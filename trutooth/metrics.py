"""Utility helpers for recording connection and scanner metrics."""
from __future__ import annotations

import asyncio
import contextlib
import csv
import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Dict, Iterable, Iterator, Mapping, Optional, Sequence


DEFAULT_FIELDS: Sequence[str] = (
    "timestamp",
    "event",
    "status",
    "value",
    "message",
    "extra",
)

def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _normalize_extra(extra: Mapping[str, Any]) -> str:
    if not extra:
        return ""
    # Ensure ASCII-only output; fallback to repr if json fails.
    try:
        return json.dumps(extra, separators=(",", ":"), ensure_ascii=True, sort_keys=True)
    except (TypeError, ValueError):
        return repr(extra)


@dataclass(slots=True)
class MetricRecord:
    """Simple value container representing a single CSV row."""

    timestamp: str
    event: str
    status: Optional[str] = None
    value: Optional[float] = None
    message: Optional[str] = None
    extra: str = ""

    def as_row(self, fields: Sequence[str]) -> Dict[str, Any]:
        row: Dict[str, Any] = {
            "timestamp": self.timestamp,
            "event": self.event,
            "status": self.status or "",
            "value": self.value if self.value is not None else "",
            "message": self.message or "",
            "extra": self.extra,
        }
        return {key: row.get(key, "") for key in fields}


class MetricsLogger:
    """Lightweight CSV logger for connection and signal metrics.

    Records are appended synchronously to keep the log tail-friendly for the
    `/events` websocket endpoint. This module deliberately avoids buffering so
    that new entries become visible to file watchers immediately.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        fields: Sequence[str] | None = None,
        static_extra: Mapping[str, Any] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.path = Path(path)
        self.fields: Sequence[str] = tuple(fields) if fields else DEFAULT_FIELDS
        if not self.fields:
            raise ValueError("fields must contain at least one column")

        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._static_extra: Dict[str, Any] = dict(static_extra or {})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._context = threading.local()
        self._ensure_header()

    def _ensure_header(self) -> None:
        if self.path.exists() and self.path.stat().st_size > 0:
            return
        with self._lock:
            with self.path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=self.fields, extrasaction="ignore")
                writer.writeheader()
                handle.flush()

    def log(
        self,
        event: str,
        *,
        status: Optional[str] = None,
        value: Optional[float] = None,
        message: Optional[str] = None,
        extra: Optional[Mapping[str, Any]] = None,
    ) -> None:
        record = MetricRecord(
            timestamp=self._timestamp(),
            event=event,
            status=status,
            value=value,
            message=message,
            extra=_normalize_extra(self._combined_extra(extra)),
        )
        self._write_row(record)

    async def log_async(
        self,
        event: str,
        *,
        status: Optional[str] = None,
        value: Optional[float] = None,
        message: Optional[str] = None,
        extra: Optional[Mapping[str, Any]] = None,
    ) -> None:
        await asyncio.to_thread(
            self.log,
            event,
            status=status,
            value=value,
            message=message,
            extra=extra,
        )

    def log_many(self, records: Iterable[Mapping[str, Any]]) -> None:
        for payload in records:
            self.log(
                str(payload.get("event", "unknown")),
                status=str(payload.get("status")) if payload.get("status") is not None else None,
                value=float(payload["value"]) if "value" in payload and payload["value"] is not None else None,
                message=str(payload.get("message")) if payload.get("message") is not None else None,
                extra={k: v for k, v in payload.items() if k not in self.fields},
            )

    def log_status(
        self,
        event: str,
        status: str,
        *,
        value: Optional[float] = None,
        message: Optional[str] = None,
        extra: Optional[Mapping[str, Any]] = None,
        **extra_kwargs: Any,
    ) -> None:
        payload = dict(extra or {})
        if extra_kwargs:
            payload.update(extra_kwargs)
        self.log(
            event,
            status=status,
            value=value,
            message=message,
            extra=payload,
        )

    @contextlib.contextmanager
    def scope(self, extra: Mapping[str, Any] | None = None, **extra_kwargs: Any) -> Iterator[None]:
        payload: Dict[str, Any] = dict(extra or {})
        if extra_kwargs:
            payload.update(extra_kwargs)
        stack = self._context_stack()
        stack.append(payload)
        try:
            yield
        finally:
            stack.pop()

    @contextlib.contextmanager
    def timer(
        self,
        event: str,
        *,
        status: str = "ok",
        error_status: str = "error",
        extra: Optional[Mapping[str, Any]] = None,
        **extra_kwargs: Any,
    ) -> Iterator[None]:
        start = perf_counter()
        payload = dict(extra or {})
        if extra_kwargs:
            payload.update(extra_kwargs)
        try:
            with self.scope(payload):
                yield
        except Exception as exc:
            duration = perf_counter() - start
            failure_payload = dict(payload)
            failure_payload["exception"] = type(exc).__name__
            failure_payload["duration"] = duration
            self.log(
                event,
                status=error_status,
                value=duration,
                message=str(exc),
                extra=failure_payload,
            )
            raise
        else:
            duration = perf_counter() - start
            success_payload = dict(payload)
            success_payload["duration"] = duration
            self.log(
                event,
                status=status,
                value=duration,
                extra=success_payload,
            )

    def _write_row(self, record: MetricRecord) -> None:
        row = record.as_row(self.fields)
        with self._lock:
            with self.path.open("a", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=self.fields, extrasaction="ignore")
                writer.writerow(row)
                handle.flush()

    def _timestamp(self) -> str:
        try:
            dt = self._clock()
        except Exception:  # pragma: no cover - guard against faulty clock
            dt = datetime.now(timezone.utc)
        if not isinstance(dt, datetime):
            return str(dt)
        return _ensure_utc(dt).isoformat(timespec="milliseconds")

    def _combined_extra(self, extra: Optional[Mapping[str, Any]]) -> Mapping[str, Any]:
        payload: Dict[str, Any] = dict(self._static_extra)
        for layer in self._context_stack():
            payload.update(layer)
        if extra:
            payload.update(extra)
        return payload

    def _context_stack(self) -> list[Dict[str, Any]]:
        stack = getattr(self._context, "stack", None)
        if stack is None:
            stack = []
            self._context.stack = stack
        return stack


__all__ = [
    "MetricsLogger",
    "MetricRecord",
    "DEFAULT_FIELDS",
]
