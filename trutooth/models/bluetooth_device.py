from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class BluetoothDevice:
    """Represents a BLE device (skeleton).

    Fields are chosen from the class diagram. Methods are minimal stubs
    that callers can extend later.
    """
    address: str
    name: Optional[str] = None
    connected: bool = False
    metadata: dict = field(default_factory=dict)

    def connect(self) -> bool:
        """Attempt to connect to the device. Stub: mark connected and return True.
        Replace with real connection logic in `connector.py`.
        """
        logger.debug("Connecting to %s", self.address)
        self.connected = True
        return True

    def disconnect(self) -> None:
        logger.debug("Disconnecting %s", self.address)
        self.connected = False

    def auto_reconnect(self, attempts: int = 3) -> bool:
        """Simple auto-reconnect stub."""
        logger.debug("Auto-reconnect %s (attempts=%d)", self.address, attempts)
        for _ in range(attempts):
            if self.connect():
                return True
        return False
