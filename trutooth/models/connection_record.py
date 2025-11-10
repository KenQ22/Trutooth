from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ConnectionRecord:
    """Represents a single connection or disconnection event."""
    device_address: str
    timestamp: datetime
    status: str  # e.g. 'connected' | 'disconnected' | 'failed'
