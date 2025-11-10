"""Connection helpers built on top of bleak."""
from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional, TYPE_CHECKING, TypeAlias, Union

from trutooth.metrics import MetricsLogger

logger = logging.getLogger(__name__)

try:  # pragma: no cover - bleak optional at runtime
	from bleak import BleakClient
except Exception:  # pragma: no cover
	BleakClient = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover - typing hints
	from bleak.backends.device import BLEDevice as _BLEDevice
	from bleak import BleakClient as _BleakClientType
else:  # pragma: no cover - runtime fallback
	_BLEDevice = Any
	_BleakClientType = Any

BLEDevice: TypeAlias = _BLEDevice
BleakClientType: TypeAlias = _BleakClientType
NotificationCallback = Callable[[str, bytes], Union[None, Awaitable[None]]]


@dataclass(slots=True)
class SessionConfig:
	"""Configuration bundle for :class:`DeviceSession`."""

	address: str
	adapter: Optional[str] = None
	timeout: float = 10.0
	mtu: Optional[int] = None
	metrics: Optional[MetricsLogger] = None
	metadata: Optional[Dict[str, Any]] = None


class DeviceSession:
	"""Thin wrapper around :class:`bleak.BleakClient` with metrics hooks."""

	def __init__(self, config: SessionConfig) -> None:
		self.config = config
		self._client: Optional[BleakClientType] = None
		self._notifications: Dict[str, NotificationCallback] = {}
		self._lock = asyncio.Lock()
		self._metrics_scope: Optional[contextlib.ExitStack] = None

	# ---------------------------------------------------------------------
	# Lifecycle helpers
	# ---------------------------------------------------------------------
	async def connect(self) -> bool:
		if BleakClient is None:
			raise RuntimeError("bleak is required to create a DeviceSession")

		async with self._lock:
			self._ensure_metrics_scope()
			if self._client and await self._is_connected(self._client):
				return True

			self._client = BleakClient(
				self.config.address,
				adapter=self.config.adapter,
				timeout=self.config.timeout,
			)

			client = self._client
			if client is None:  # pragma: no cover - defensive for static checkers
				raise RuntimeError("BleakClient failed to initialize")

			try:
				connected = await client.connect()
			except Exception as exc:
				self._metrics_log("connect", status="error", message=str(exc))
				logger.exception("Connection attempt failed for %s", self.config.address)
				self._clear_metrics_scope()
				raise

			if not connected:
				self._metrics_log("connect", status="failed")
				self._clear_metrics_scope()
				return False

			self._metrics_log("connect", status="ok")

			if self.config.mtu and hasattr(client, "mtu_size"):
				with contextlib.suppress(Exception):
					await client.request_mtu(self.config.mtu)  # type: ignore[attr-defined]

			return True

	async def disconnect(self) -> None:
		async with self._lock:
			if not self._client:
				self._clear_metrics_scope()
				return
			try:
				await self._client.disconnect()
				self._metrics_log("disconnect", status="ok")
			except Exception as exc:
				self._metrics_log("disconnect", status="error", message=str(exc))
				logger.warning("Disconnect encountered error for %s: %s", self.config.address, exc)
			finally:
				self._client = None
				self._notifications.clear()
				self._clear_metrics_scope()

	async def __aenter__(self) -> "DeviceSession":
		await self.connect()
		return self

	async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
		await self.disconnect()

	# ------------------------------------------------------------------
	# Notification management
	# ------------------------------------------------------------------
	async def start_notify(self, characteristic: str, callback: NotificationCallback) -> None:
		client = await self._require_client()

		def _wrapped(_: Any, data: bytearray) -> None:
			try:
				outcome = callback(characteristic, bytes(data))
				if asyncio.iscoroutine(outcome):
					asyncio.create_task(outcome)
			except Exception as exc:  # pragma: no cover - user callback failure
				logger.exception("Notification callback raised for %s: %s", characteristic, exc)

		await client.start_notify(characteristic, _wrapped)
		self._notifications[characteristic] = callback
		self._metrics_log("notify_start", status="ok", extra={"characteristic": characteristic})

	async def stop_notify(self, characteristic: str) -> None:
		client = await self._require_client()
		if characteristic not in self._notifications:
			return
		with contextlib.suppress(Exception):
			await client.stop_notify(characteristic)
		self._notifications.pop(characteristic, None)
		self._metrics_log("notify_stop", status="ok", extra={"characteristic": characteristic})

	async def clear_notifications(self) -> None:
		client = await self._require_client()
		for char in list(self._notifications):
			with contextlib.suppress(Exception):
				await client.stop_notify(char)
		self._notifications.clear()

	# ------------------------------------------------------------------
	# Utility operations
	# ------------------------------------------------------------------
	async def read_rssi(self) -> Optional[int]:
		client = await self._require_client()
		rssi: Optional[int] = None

		if hasattr(client, "get_rssi"):
			try:
				rssi = await client.get_rssi()  # type: ignore[attr-defined]
			except Exception:
				rssi = None
		elif hasattr(client, "rssi"):
			rssi = getattr(client, "rssi")

		if rssi is not None:
			self._metrics_log("rssi", status="ok", value=float(rssi))
		return rssi

	async def read_gatt(self, characteristic: str) -> bytes:
		client = await self._require_client()
		data = await client.read_gatt_char(characteristic)
		self._metrics_log("read_gatt", status="ok", extra={"characteristic": characteristic, "len": len(data)})
		return bytes(data)

	async def write_gatt(self, characteristic: str, data: bytes, *, response: bool = False) -> None:
		client = await self._require_client()
		await client.write_gatt_char(characteristic, data, response=response)
		self._metrics_log(
			"write_gatt",
			status="ok",
			extra={"characteristic": characteristic, "len": len(data), "response": response},
		)

	async def _require_client(self) -> BleakClientType:
		if self._client is None:
			raise RuntimeError("DeviceSession is not connected")
		if not await self._is_connected(self._client):
			raise RuntimeError("DeviceSession connection has dropped")
		return self._client

	async def _is_connected(self, client: BleakClientType) -> bool:
		state = getattr(client, "is_connected", None)
		if callable(state):
			with contextlib.suppress(Exception):
				result = state()
				if asyncio.iscoroutine(result):
					return bool(await result)
				return bool(result)
			return False
		return bool(state)

	# ------------------------------------------------------------------
	# Metrics helper
	# ------------------------------------------------------------------
	def _metrics_log(
		self,
		event: str,
		*,
		status: Optional[str] = None,
		value: Optional[float] = None,
		message: Optional[str] = None,
		extra: Optional[Dict[str, Any]] = None,
	) -> None:
		if not self.config.metrics:
			return
		payload = dict(extra or {})
		try:
			self.config.metrics.log(
				event,
				status=status,
				value=value,
				message=message,
				extra=payload,
			)
		except Exception:  # pragma: no cover - logging must not break session
			logger.debug("Metrics logging failed for %s", event, exc_info=True)

	def _ensure_metrics_scope(self) -> None:
		if not self.config.metrics:
			return
		if self._metrics_scope is not None:
			return
		payload = {"address": self.config.address}
		if self.config.metadata:
			payload.update(self.config.metadata)
		stack = contextlib.ExitStack()
		stack.enter_context(self.config.metrics.scope(payload))
		self._metrics_scope = stack

	def _clear_metrics_scope(self) -> None:
		if self._metrics_scope is None:
			return
		with contextlib.suppress(Exception):
			self._metrics_scope.close()
		self._metrics_scope = None


__all__ = [
	"DeviceSession",
	"SessionConfig",
	"BLEDevice",
	"NotificationCallback",
]
