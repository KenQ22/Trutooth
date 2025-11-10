from __future__ import annotations
from typing import List
from datetime import datetime
import logging

from .connection_record import ConnectionRecord

logger = logging.getLogger(__name__)


class ConnectionHistory:
    """Keeps a history of connection events."""

    def __init__(self) -> None:
        self.history: List[ConnectionRecord] = []

    def log_connection(self, device_address: str) -> ConnectionRecord:
        record = ConnectionRecord(device_address, datetime.utcnow(), "connected")
        self.history.append(record)
        logger.debug("log_connection: %s", record)
        return record

    def log_disconnection(self, device_address: str) -> ConnectionRecord:
        record = ConnectionRecord(device_address, datetime.utcnow(), "disconnected")
        self.history.append(record)
        logger.debug("log_disconnection: %s", record)
        return record

    def last(self) -> ConnectionRecord | None:
        return self.history[-1] if self.history else None
