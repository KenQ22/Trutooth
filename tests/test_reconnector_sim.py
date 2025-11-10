"""Simulation tests for the reconnection supervisor."""
from __future__ import annotations

import asyncio
import csv
import json
import tempfile
import unittest
from pathlib import Path
from typing import Iterable, Optional

from trutooth.metrics import MetricsLogger
from trutooth.reconnect import Reconnector


class _FakeSession:
    def __init__(self, config, rssi_script: Iterable[Optional[int]]) -> None:
        self.config = config
        self._iter = iter(rssi_script)
        self.connected = False

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):  # pragma: no cover - trivial
        await self.disconnect()
        return False

    async def connect(self) -> bool:
        self.connected = True
        await asyncio.sleep(0)
        return True

    async def disconnect(self) -> None:
        self.connected = False
        await asyncio.sleep(0)

    async def read_rssi(self) -> Optional[int]:
        await asyncio.sleep(0)
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise RuntimeError("signal lost") from exc


class _FakeSessionFactory:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, config) -> _FakeSession:
        self.calls += 1
        script = [-65, -64, -63, None, -62]
        return _FakeSession(config, script)


class ReconnectorSimulationTest(unittest.IsolatedAsyncioTestCase):
    async def test_reconnector_logs_metrics_with_fake_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp, "metrics.csv")
            metrics = MetricsLogger(log_path)
            factory = _FakeSessionFactory()

            reconnector = Reconnector(
                address="AA:BB:CC:DD:EE:FF",
                log=metrics,
                poll_interval=0.01,
                base_backoff=0.01,
                max_backoff=0.02,
                metadata={"role": "test"},
                session_factory=factory,
            )

            await reconnector.run(runtime=0.05)

            self.assertGreaterEqual(factory.calls, 1)

            with log_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertTrue(any(row["event"] == "monitor_start" for row in rows))
            self.assertTrue(any(row["event"] == "rssi_sample" for row in rows))

            monitor_row = next(row for row in rows if row["event"] == "monitor_start")
            extra_payload = json.loads(monitor_row["extra"]) if monitor_row["extra"] else {}
            self.assertEqual(extra_payload.get("address"), "AA:BB:CC:DD:EE:FF")
            self.assertEqual(extra_payload.get("role"), "test")


if __name__ == "__main__":
    unittest.main()
