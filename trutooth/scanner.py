"""BLE scanning utilities for TruTooth."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Sequence, TYPE_CHECKING, Union, TypeAlias

logger = logging.getLogger(__name__)

try:  # pragma: no cover - bleak is optional in some environments
	from bleak import BleakScanner
except Exception:  # pragma: no cover
	BleakScanner = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover - typing helper only
	from bleak.backends.device import BLEDevice as _BLEDevice
	from bleak.backends.scanner import AdvertisementData as _AdvertisementData
else:  # pragma: no cover - runtime fallback when bleak unavailable
	_BLEDevice = Any
	_AdvertisementData = Any

BLEDevice: TypeAlias = _BLEDevice
AdvertisementData: TypeAlias = _AdvertisementData

try:  # pragma: no cover - optional dependency at runtime
	from trutooth.models.bluetooth_device import BluetoothDevice as _BluetoothDeviceRuntime
except Exception:  # pragma: no cover
	_BluetoothDeviceRuntime = None

if TYPE_CHECKING:  # pragma: no cover
	from trutooth.models.bluetooth_device import BluetoothDevice as _BluetoothDeviceType
else:  # pragma: no cover
	_BluetoothDeviceType = Any

BluetoothDeviceType: TypeAlias = _BluetoothDeviceType

try:  # pragma: no cover - models may be absent in lightweight tests
	from trutooth.models.bluetooth_device import BluetoothDevice
except Exception:  # pragma: no cover
	BluetoothDevice = None  # type: ignore

EventCallback = Callable[["ScanResult"], Union[None, Awaitable[None]]]


@dataclass(slots=True)
class ScanResult:
	"""Represents a single BLE advertisement snapshot."""

	address: str
	name: Optional[str]
	rssi: Optional[int]
	uuids: tuple[str, ...] = ()
	manufacturer_data: Dict[int, bytes] = field(default_factory=dict)
	service_data: Dict[str, bytes] = field(default_factory=dict)
	connectable: Optional[bool] = None
	tx_power: Optional[int] = None
	advertisement_time: Optional[float] = None
	extra: Dict[str, Any] = field(default_factory=dict)

	@classmethod
	def from_bleak(
		cls,
		device: BLEDevice,
		advertisement: AdvertisementData | None = None,
	) -> "ScanResult":
		uuids: Iterable[str] = ()
		manufacturer_data: Dict[int, bytes] = {}
		service_data: Dict[str, bytes] = {}
		connectable: Optional[bool] = None
		tx_power: Optional[int] = None
		timestamp: Optional[float] = None
		extra: Dict[str, Any] = {}

		if advertisement is not None:
			uuids = advertisement.service_uuids or ()
			manufacturer_data = {
				key: bytes(value)
				for key, value in (advertisement.manufacturer_data or {}).items()
			}
			service_data = {
				key: bytes(value)
				for key, value in (advertisement.service_data or {}).items()
			}
			connectable = getattr(advertisement, "is_connectable", None)
			tx_power = advertisement.tx_power
			timestamp = getattr(advertisement, "timestamp", None)
			if advertisement.platform_data:
				extra["platform_data"] = advertisement.platform_data

		if not uuids:
			metadata = getattr(device, "metadata", None) or {}
			meta_uuids = metadata.get("uuids")
			if meta_uuids:
				uuids = meta_uuids

		name = device.name or None
		rssi = None
		if advertisement is not None and advertisement.rssi is not None:
			rssi = advertisement.rssi
		else:
			rssi = getattr(device, "rssi", None)

		details = getattr(device, "details", None)
		if details is not None:
			extra["details"] = details

		return cls(
			address=device.address,
			name=name,
			rssi=rssi,
			uuids=tuple(str(uuid) for uuid in uuids),
			manufacturer_data=manufacturer_data,
			service_data=service_data,
			connectable=connectable,
			tx_power=tx_power,
			advertisement_time=timestamp,
			extra=extra,
		)

	def to_dict(self) -> Dict[str, Any]:
		payload: Dict[str, Any] = {
			"address": self.address,
			"name": self.name,
			"rssi": self.rssi,
			"uuids": list(self.uuids),
			"connectable": self.connectable,
			"tx_power": self.tx_power,
			"advertisement_time": self.advertisement_time,
		}
		if self.manufacturer_data:
			payload["manufacturer_data"] = {
				key: value.hex() for key, value in self.manufacturer_data.items()
			}
		if self.service_data:
			payload["service_data"] = {
				key: value.hex() for key, value in self.service_data.items()
			}
		if self.extra:
			payload["extra"] = self.extra
		return payload

	def to_bluetooth_device(self) -> Optional[BluetoothDeviceType]:
		if _BluetoothDeviceRuntime is None:
			return None
		metadata = {
			"uuids": list(self.uuids),
			"manufacturer_data": self.manufacturer_data,
			"service_data": self.service_data,
			"connectable": self.connectable,
			"tx_power": self.tx_power,
			"advertisement_time": self.advertisement_time,
			**self.extra,
		}
		return _BluetoothDeviceRuntime(address=self.address, name=self.name, metadata=metadata)


@dataclass(slots=True)
class ScannerConfig:
	"""Configuration bundle used by :class:`Scanner`."""

	service_uuids: Sequence[str] | None = None
	address_allowlist: Sequence[str] | None = None
	name_allowlist: Sequence[str] | None = None
	max_devices: int | None = None
	callback: Optional[EventCallback] = None
	return_duplicates: bool = False
	scanning_mode: Optional[str] = None
	adapter: Optional[str] = None
	detection_kwargs: Dict[str, Any] = field(default_factory=dict)
	_address_index: Optional[frozenset[str]] = field(init=False, repr=False, default=None)
	_name_index: Optional[tuple[str, ...]] = field(init=False, repr=False, default=None)
	_service_index: Optional[frozenset[str]] = field(init=False, repr=False, default=None)

	def __post_init__(self) -> None:
		if self.max_devices is not None and self.max_devices <= 0:
			raise ValueError("max_devices must be positive when provided")
		if self.address_allowlist:
			self._address_index = frozenset(addr.lower() for addr in self.address_allowlist)
		if self.name_allowlist:
			self._name_index = tuple(self.name_allowlist)
		if self.service_uuids:
			self._service_index = frozenset(uuid.lower() for uuid in self.service_uuids)

	def allows(self, device: BLEDevice, advertisement: AdvertisementData | None) -> bool:
		if self._address_index and device.address.lower() not in self._address_index:
			return False

		if self._name_index:
			observed_name = device.name or None
			if advertisement is not None and getattr(advertisement, "local_name", None):
				observed_name = advertisement.local_name
			if observed_name not in self._name_index:
				return False

		if self._service_index:
			observed: set[str] = set()
			if advertisement is not None and advertisement.service_uuids:
				observed.update(uuid.lower() for uuid in advertisement.service_uuids)
			metadata = getattr(device, "metadata", None) or {}
			if metadata.get("uuids"):
				observed.update(str(uuid).lower() for uuid in metadata["uuids"])
			if not observed.issuperset(self._service_index):
				return False

		return True

	def bleak_kwargs(self) -> Dict[str, Any]:
		kwargs = dict(self.detection_kwargs)
		if self.service_uuids and "service_uuids" not in kwargs:
			kwargs["service_uuids"] = list(self.service_uuids)
		if self.adapter and "adapter" not in kwargs:
			kwargs["adapter"] = self.adapter
		if self.scanning_mode and "scanning_mode" not in kwargs:
			kwargs["scanning_mode"] = self.scanning_mode
		return kwargs


class Scanner:
	"""Stateful BLE scanner with filtering and callbacks."""

	def __init__(self, config: ScannerConfig | None = None) -> None:
		self.config = config or ScannerConfig()
		self._results: Dict[str, ScanResult] = {}
		self._duplicates: List[ScanResult] = []
		self._loop: Optional[asyncio.AbstractEventLoop] = None
		self._stop_event: Optional[asyncio.Event] = None

	def reset(self) -> None:
		self._results.clear()
		self._duplicates.clear()

	async def run(self, timeout: float) -> List[ScanResult]:
		if BleakScanner is None:
			logger.warning("bleak is not installed; returning empty scan results")
			await asyncio.sleep(min(timeout, 0.1))
			return []

		self.reset()
		self._loop = asyncio.get_running_loop()
		self._stop_event = asyncio.Event()

		scanner = BleakScanner(**self.config.bleak_kwargs())
		register_cb = getattr(scanner, "register_detection_callback", None)
		if callable(register_cb):
			register_cb(self._on_detection)

		try:
			async with scanner:
				try:
					await asyncio.wait_for(self._stop_event.wait(), timeout=timeout)
				except asyncio.TimeoutError:
					pass
		except Exception as exc:  # pragma: no cover - hardware specific
			logger.exception("BLE scan failed: %s", exc)
			raise

		return self.results()

	def results(self) -> List[ScanResult]:
		if self.config.return_duplicates:
			return list(self._duplicates)
		return list(self._results.values())

	def as_bluetooth_devices(self) -> List[BluetoothDeviceType]:
		devices: List[BluetoothDeviceType] = []
		for result in self.results():
			model = result.to_bluetooth_device()
			if model is not None:
				devices.append(model)
		return devices

	def _on_detection(self, device: BLEDevice, advertisement: AdvertisementData | None) -> None:
		if not self.config.allows(device, advertisement):
			return

		result = ScanResult.from_bleak(device, advertisement)

		if self.config.return_duplicates:
			self._duplicates.append(result)
			collection_size = len(self._duplicates)
		else:
			self._results[result.address] = result
			collection_size = len(self._results)

		if self.config.callback:
			self._dispatch_callback(result)

		if (
			self.config.max_devices is not None
			and collection_size >= self.config.max_devices
			and self._stop_event is not None
			and not self._stop_event.is_set()
		):
			self._stop_event.set()

	def _dispatch_callback(self, result: ScanResult) -> None:
		if not self.config.callback:
			return
		try:
			outcome = self.config.callback(result)
			if asyncio.iscoroutine(outcome):
				loop = self._loop or asyncio.get_event_loop()
				loop.create_task(outcome)
		except Exception:  # pragma: no cover - diagnostic path
			logger.exception("scanner callback raised an exception")


async def discover(
	timeout: float = 6.0,
	*,
	service_uuids: Sequence[str] | None = None,
	addresses: Sequence[str] | None = None,
	names: Sequence[str] | None = None,
	max_devices: int | None = None,
	return_duplicates: bool = False,
	callback: Optional[EventCallback] = None,
	scanning_mode: Optional[str] = None,
	adapter: Optional[str] = None,
	detection_kwargs: Optional[Dict[str, Any]] = None,
) -> List[ScanResult]:
	config = ScannerConfig(
		service_uuids=service_uuids,
		address_allowlist=addresses,
		name_allowlist=names,
		max_devices=max_devices,
		callback=callback,
		return_duplicates=return_duplicates,
		scanning_mode=scanning_mode,
		adapter=adapter,
		detection_kwargs=detection_kwargs or {},
	)
	scanner = Scanner(config)
	return await scanner.run(timeout)


__all__ = [
	"ScanResult",
	"ScannerConfig",
	"Scanner",
	"discover",
]
