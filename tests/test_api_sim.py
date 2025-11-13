"""Integration-style tests for the FastAPI layer using fakes."""
from __future__ import annotations

import asyncio
import json
import unittest
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import patch

from fastapi.testclient import TestClient

import trutooth.api as api_module


class _FakeMetricsLogger:
    def __init__(self, path: str, static_extra: Optional[Dict[str, Any]] = None) -> None:
        self.path = path
        self.static_extra = static_extra or {}
        self.records: List[Dict[str, Any]] = []

    def log(self, event: str, **payload: Any) -> None:
        record = {"event": event, **payload}
        self.records.append(record)

    async def log_async(self, event: str, **payload: Any) -> None:
        await asyncio.sleep(0)
        self.log(event, **payload)


class _FakeReconnector:
    instances: List["_FakeReconnector"] = []

    def __init__(self, address: str, **kwargs: Any) -> None:
        self.address = address
        self.kwargs = kwargs
        self.stop_event = asyncio.Event()
        self.force_disconnect_event = asyncio.Event()
        self.run_calls: List[Optional[float]] = []
        _FakeReconnector.instances.append(self)

    async def run(self, runtime: Optional[float] = None) -> None:
        self.run_calls.append(runtime)
        try:
            await asyncio.wait_for(self.stop_event.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            # Ensure the fake does not hang tests even if stop is not called.
            pass

    def request_stop(self) -> None:
        self.stop_event.set()

    def request_force_disconnect(self) -> None:
        self.force_disconnect_event.set()


class ApiSimulationTest(unittest.TestCase):
    def setUp(self) -> None:
        api_module._rec_task = None
        api_module._rec = None
        api_module._log_path = None
        self.client = TestClient(api_module.app)

    def tearDown(self) -> None:
        # Best effort cleanup for lingering background work.
        if api_module._rec_task and not api_module._rec_task.done():
            api_module._rec_task.cancel()
        self.client.close()
        api_module._rec_task = None
        api_module._rec = None
        api_module._log_path = None
        _FakeReconnector.instances.clear()

    def test_scan_endpoint_returns_minimal_device_payload(self) -> None:
        async def fake_bleak_discover(timeout: float = 6.0, return_adv: bool = False):
            assert timeout == 0.25
            dev1 = SimpleNamespace(address="AA:BB", name="Sensor", rssi=-55)
            adv1 = SimpleNamespace(rssi=-55)
            dev2 = SimpleNamespace(address="CC:DD", name=None, rssi=None)
            adv2 = SimpleNamespace(rssi=None)
            return {"AA:BB": (dev1, adv1), "CC:DD": (dev2, adv2)}

        with patch("bleak.BleakScanner") as mock_scanner:
            mock_scanner.discover = fake_bleak_discover
            response = self.client.get("/scan", params={"timeout": 0.25})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 2)
        self.assertEqual(payload[0], {"address": "AA:BB", "name": "Sensor", "rssi": -55})
        self.assertIn("rssi", payload[1])

    def test_monitor_start_and_stop_flow_uses_reconnector(self) -> None:
        import time
        metadata = {"role": "demo"}
        with patch("trutooth.api.MetricsLogger", _FakeMetricsLogger), patch(
            "trutooth.api.Reconnector", _FakeReconnector
        ):
            response = self.client.post(
                "/monitor/start",
                params={
                    "device": "AA:BB:CC:DD:EE:FF",
                    "log": "test_metrics.csv",
                    "connect_timeout": 10.0,
                    "poll_interval": 0.5,
                    "base_backoff": 0.5,
                    "max_backoff": 1.0,
                    "runtime": 0.2,
                    "metadata": json.dumps(metadata),
                },
            )

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "started")
            self.assertEqual(data["log"], "test_metrics.csv")

            self.assertTrue(_FakeReconnector.instances)
            reconstructor = _FakeReconnector.instances[-1]
            self.assertEqual(reconstructor.address, "AA:BB:CC:DD:EE:FF")
            self.assertEqual(reconstructor.kwargs["metadata"], metadata)
            self.assertEqual(reconstructor.kwargs["poll_interval"], 0.5)
            self.assertIsInstance(reconstructor.kwargs["log"], _FakeMetricsLogger)
            # Give the async task time to start
            time.sleep(0.1)
            self.assertEqual(reconstructor.run_calls, [0.2])

            stop_response = self.client.post("/monitor/stop")

        self.assertEqual(stop_response.status_code, 200)
        self.assertEqual(stop_response.json(), {"status": "stopped"})

    def test_monitor_start_rejects_invalid_metadata(self) -> None:
        response = self.client.post(
            "/monitor/start",
            params={"device": "AA:BB:CC:DD:EE:FF", "metadata": "{not json"},
        )
        self.assertEqual(response.status_code, 400)
        detail = response.json()["detail"]
        self.assertIn("Invalid metadata JSON", detail)

    def test_monitor_status_returns_idle_when_not_running(self) -> None:
        response = self.client.get("/monitor/status")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "idle")

    def test_monitor_status_endpoint_structure(self) -> None:
        # Test the status endpoint returns correct structure
        response = self.client.get("/monitor/status")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("status", payload)
        self.assertEqual(payload["status"], "idle")

    def test_health_endpoint_returns_ok(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("time", payload)

    def test_scan_debug_endpoint_provides_detailed_info(self) -> None:
        async def fake_discover(timeout: float = 6.0):
            return [SimpleNamespace(address="AA:BB", name="Test", rssi=-60)]

        with patch("trutooth.api.discover", fake_discover):
            response = self.client.get("/scan/debug", params={"timeout": 0.5})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("mode", payload)
        self.assertIn("count", payload)
        self.assertIn("devices", payload)


if __name__ == "__main__":
    unittest.main()
