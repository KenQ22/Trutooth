"""Simulation tests for the BLE scanner logic."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Iterable, List, Optional, Tuple
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from trutooth.scanner import ScanResult, Scanner, ScannerConfig, discover


class FakeBleakScanner:
    """Minimal async context manager that replays predetermined events."""

    events: List[Tuple[Any, Any]] = []

    def __init__(self, **_: Any) -> None:
        self._callback = None
        self._task: Optional[asyncio.Task[None]] = None

    def register_detection_callback(self, callback):
        self._callback = callback

    async def __aenter__(self):
        self._task = asyncio.create_task(self._emit())
        return self

    async def __aexit__(self, exc_type, exc, tb):  # pragma: no cover - cleanup
        if self._task:
            await self._task
        return False

    async def _emit(self) -> None:
        await asyncio.sleep(0)
        if not self._callback:
            return
        for device, advertisement in list(self.events):
            self._callback(device, advertisement)
        await asyncio.sleep(0)


class ScannerSimulationTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        FakeBleakScanner.events = []

    async def test_discover_collects_scan_results(self) -> None:
        device1 = SimpleNamespace(
            address="AA:BB:CC:DD:EE:01",
            name="SensorOne",
            metadata={"uuids": ["1234"]},
            details={"os": "win"},
            rssi=-52,
        )
        adv1 = SimpleNamespace(
            service_uuids=["1234"],
            manufacturer_data={42: b"\x01\x02"},
            service_data={"abcd": b"\x10"},
            is_connectable=True,
            tx_power=-4,
            timestamp=100.5,
            platform_data=[("win", 1)],
            rssi=-50,
        )
        device2 = SimpleNamespace(address="AA:BB:CC:DD:EE:02", name="SensorTwo", metadata={}, rssi=-60)
        adv2 = SimpleNamespace(service_uuids=None, manufacturer_data=None, service_data=None, is_connectable=False, tx_power=None, timestamp=None, platform_data=None, rssi=-58)
        FakeBleakScanner.events = [(device1, adv1), (device2, adv2)]

        with patch("trutooth.scanner.BleakScanner", FakeBleakScanner):
            results = await discover(timeout=0.1, max_devices=2)

        self.assertEqual(len(results), 2)
        first = results[0]
        self.assertIsInstance(first, ScanResult)
        self.assertEqual(first.address, "AA:BB:CC:DD:EE:01")
        self.assertEqual(first.name, "SensorOne")
        self.assertIn("1234", first.uuids)
        self.assertEqual(first.manufacturer_data[42], b"\x01\x02")
        self.assertEqual(first.extra.get("details", {}).get("os"), "win")

        devices = Scanner(ScannerConfig()).as_bluetooth_devices()  # empty without results
        self.assertEqual(devices, [])

        scanner = Scanner(ScannerConfig())
        scanner._results = {result.address: result for result in results}  # inject results for conversion
        bt_devices = scanner.as_bluetooth_devices()
        self.assertEqual(len(bt_devices), 2)
        self.assertEqual(bt_devices[0].address, "AA:BB:CC:DD:EE:01")
        self.assertIn("uuids", bt_devices[0].metadata)

    async def test_duplicates_mode_preserves_all_events(self) -> None:
        device = SimpleNamespace(address="AA:BB:CC:DD:EE:03", name="SensorThree", metadata={}, rssi=-70)
        adv_first = SimpleNamespace(service_uuids=None, manufacturer_data=None, service_data=None, is_connectable=True, tx_power=None, timestamp=None, platform_data=None, rssi=-70)
        adv_second = SimpleNamespace(service_uuids=None, manufacturer_data=None, service_data=None, is_connectable=True, tx_power=None, timestamp=None, platform_data=None, rssi=-71)
        FakeBleakScanner.events = [(device, adv_first), (device, adv_second)]

        config = ScannerConfig(return_duplicates=True, max_devices=2)
        scanner = Scanner(config)

        with patch("trutooth.scanner.BleakScanner", FakeBleakScanner):
            results = await scanner.run(timeout=0.1)

        self.assertEqual(len(results), 2)
        self.assertNotEqual(results[0].rssi, results[1].rssi)

        config_unique = ScannerConfig(return_duplicates=False, max_devices=2)
        scanner_unique = Scanner(config_unique)
        with patch("trutooth.scanner.BleakScanner", FakeBleakScanner):
            unique_results = await scanner_unique.run(timeout=0.1)
        self.assertEqual(len(unique_results), 1)
        self.assertEqual(unique_results[0].address, "AA:BB:CC:DD:EE:03")


if __name__ == "__main__":
    import unittest

    unittest.main()
