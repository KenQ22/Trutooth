from __future__ import annotations
from typing import List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CommunicationHistory:
    """Records communication messages exchanged with devices."""

    def __init__(self) -> None:
        # Each entry is a tuple (device_address, timestamp, direction, payload)
        self.messages: List[tuple[str, datetime, str, object]] = []

    def log_message(self, device_address: str, direction: str, payload: object) -> None:
        self.messages.append((device_address, datetime.utcnow(), direction, payload))
        logger.debug("log_message: %s %s", device_address, direction)

    def get_for_device(self, device_address: str) -> List[tuple[str, datetime, str, object]]:
        return [m for m in self.messages if m[0] == device_address]
