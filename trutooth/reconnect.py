"""Automatic reconnection supervisor for BLE sessions."""
from __future__ import annotations

import asyncio
import contextlib
import logging
from pathlib import Path
from time import monotonic
from typing import Any, Callable, Dict, Mapping, Optional, Union

from trutooth.connector import DeviceSession, SessionConfig
from trutooth.metrics import MetricsLogger

logger = logging.getLogger(__name__)


class Reconnector:
    """Manage continual BLE monitoring with exponential backoff."""

    def __init__(
        self,
        address: str,
        *,
        log: Union[MetricsLogger, str, Path, None] = None,
        adapter: Optional[str] = None,
        mtu: Optional[int] = None,
        connect_timeout: float = 10.0,
        poll_interval: float = 5.0,
        base_backoff: float = 2.0,
        max_backoff: float = 60.0,
        metadata: Optional[Mapping[str, Any]] = None,
        session_factory: Optional[Callable[[SessionConfig], Any]] = None,
    ) -> None:
        self.address = address
        self.adapter = adapter
        self.mtu = mtu
        self.connect_timeout = max(1.0, connect_timeout)
        self.poll_interval = max(0.1, poll_interval)
        self.base_backoff = max(0.5, base_backoff)
        self.max_backoff = max(self.base_backoff, max_backoff)
        self.metadata = dict(metadata or {})

        scope_payload = {"address": self.address, **self.metadata}

        if isinstance(log, MetricsLogger):
            self.metrics = log
        elif log is None:
            self.metrics = None
        else:
            self.metrics = MetricsLogger(log, static_extra=scope_payload)

        self._scope_payload = scope_payload
        self._session_factory: Callable[[SessionConfig], Any] = session_factory or DeviceSession

        self._stop_event: Optional[asyncio.Event] = None
        self._session: Optional[DeviceSession] = None

    async def run(self, runtime: Optional[float] = None) -> None:
        """Continuously attempt to maintain a session until stopped."""
        stop_event = asyncio.Event()
        self._stop_event = stop_event
        deadline = monotonic() + runtime if runtime else None
        backoff = self.base_backoff
        attempt = 0

        metrics_scope = contextlib.nullcontext()
        if self.metrics:
            metrics_scope = self.metrics.scope(self._scope_payload)

        await self._log("monitor_start", status="pending")

        try:
            with metrics_scope:
                while not stop_event.is_set():
                    if deadline and monotonic() >= deadline:
                        break

                    attempt += 1
                    try:
                        await self._log("connect_attempt", status="pending", extra={"attempt": attempt})
                        session = self._session_factory(
                            SessionConfig(
                                address=self.address,
                                adapter=self.adapter,
                                timeout=self.connect_timeout,
                                mtu=self.mtu,
                                metrics=self.metrics,
                                metadata=self.metadata,
                            )
                        )
                        async with session as active_session:
                            self._session = active_session
                            await self._log(
                                "connect_attempt",
                                status="ok",
                                extra={"attempt": attempt, "backoff": backoff},
                            )
                            backoff = self.base_backoff
                            await self._connected_loop(active_session, deadline, stop_event)
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:  # pragma: no cover - network/hardware dependent
                        await self._log("session_error", status="error", message=str(exc))
                        logger.warning("Reconnector session error for %s: %s", self.address, exc)
                    finally:
                        if self._session is not None:
                            with contextlib.suppress(Exception):
                                await self._session.disconnect()
                        self._session = None

                    if stop_event.is_set():
                        break
                    if deadline and monotonic() >= deadline:
                        break

                    await self._sleep_with_stop(backoff, stop_event, deadline)
                    backoff = min(backoff * 2, self.max_backoff)
        except asyncio.CancelledError:
            await self._log("monitor_stop", status="cancelled")
            raise
        finally:
            stop_event.set()
            await self._log("monitor_stop", status="ok")

    def request_stop(self) -> None:
        if self._stop_event:
            self._stop_event.set()

    async def _connected_loop(
        self,
        session: DeviceSession,
        deadline: Optional[float],
        stop_event: asyncio.Event,
    ) -> None:
        await self._log("session_active", status="ok")
        try:
            while not stop_event.is_set():
                if deadline and monotonic() >= deadline:
                    break
                try:
                    rssi = await session.read_rssi()
                    status = "ok" if rssi is not None else "unknown"
                    await self._log("rssi_sample", status=status, value=float(rssi) if rssi is not None else None)
                except RuntimeError as exc:
                    # DeviceSession reports dropped connections via RuntimeError
                    await self._log("session_lost", status="error", message=str(exc))
                    break
                except Exception as exc:  # pragma: no cover - hardware dependent
                    await self._log("rssi_sample", status="error", message=str(exc))

                await self._sleep_with_stop(self.poll_interval, stop_event, deadline)
        finally:
            await self._log("session_active", status="ended")

    async def _sleep_with_stop(
        self,
        duration: float,
        stop_event: asyncio.Event,
        deadline: Optional[float],
    ) -> None:
        if duration <= 0:
            return
        wait_time = duration
        if deadline:
            wait_time = min(wait_time, max(0.0, deadline - monotonic()))
            if wait_time <= 0:
                return
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=wait_time)
        except asyncio.TimeoutError:
            pass

    async def _log(
        self,
        event: str,
        *,
        status: Optional[str] = None,
        value: Optional[float] = None,
        message: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.metrics:
            return
        payload: Dict[str, Any] = dict(self._scope_payload)
        if extra:
            payload.update(extra)
        try:
            await self.metrics.log_async(
                event,
                status=status,
                value=value,
                message=message,
                extra=payload,
            )
        except Exception:  # pragma: no cover - I/O failure safeguard
            logger.debug("Metrics logging failed for %s", event, exc_info=True)


__all__ = ["Reconnector"]
