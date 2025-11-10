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
        async def fake_discover(timeout: float = 6.0):
            assert timeout == 0.25
            return [
                SimpleNamespace(address="AA:BB", name="Sensor", rssi=-55),
                SimpleNamespace(address="CC:DD", name=None, rssi=None),
            ]

        with patch("trutooth.api.discover", fake_discover):
            response = self.client.get("/scan", params={"timeout": 0.25})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 2)
        self.assertEqual(payload[0], {"address": "AA:BB", "name": "Sensor", "rssi": -55})
        self.assertIn("rssi", payload[1])

    def test_monitor_start_and_stop_flow_uses_reconnector(self) -> None:
        metadata = {"role": "demo"}
        with patch("trutooth.api.MetricsLogger", _FakeMetricsLogger), patch(
            "trutooth.api.Reconnector", _FakeReconnector
        ):
            response = self.client.post(
                "/monitor/start",
                params={
                    "device": "AA:BB:CC:DD:EE:FF",
                    "log": "test_metrics.csv",
                    "poll_interval": 0.1,
                    "base_backoff": 0.1,
                    "max_backoff": 0.1,
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
            self.assertEqual(reconstructor.kwargs["poll_interval"], 0.1)
            self.assertIsInstance(reconstructor.kwargs["log"], _FakeMetricsLogger)
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


if __name__ == "__main__":
    unittest.main()
