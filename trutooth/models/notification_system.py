from __future__ import annotations
import logging
from .bluetooth_device import BluetoothDevice

logger = logging.getLogger(__name__)


class NotificationSystem:
    """Handles notifications (skeleton).

    The real system could push GUI updates, logs, or external alerts.
    """

    def notify_success(self, device: BluetoothDevice, message: str | None = None) -> None:
        logger.info("NOTIFY SUCCESS: %s %s", device.address, message or "")

    def notify_failure(self, device: BluetoothDevice, message: str | None = None) -> None:
        logger.warning("NOTIFY FAILURE: %s %s", device.address, message or "")
