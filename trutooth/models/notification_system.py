from __future__ import annotations
import logging
from typing import Optional
from .bluetooth_device import BluetoothDevice

logger = logging.getLogger(__name__)


class NotificationSystem:
    """Handles notifications for device connection/disconnection events.

    Provides consistent logging and notification patterns for device presence
    and failure events. Can be extended to support GUI updates, external alerts,
    or other notification mechanisms.
    """

    def notify_success(self, device: BluetoothDevice, message: str | None = None) -> None:
        """Notify successful operation (connection, reconnection, etc.)."""
        logger.info("NOTIFY SUCCESS: %s %s", device.address, message or "")

    def notify_failure(self, device: BluetoothDevice, message: str | None = None) -> None:
        """Notify failure event (disconnection, error, etc.)."""
        logger.warning("NOTIFY FAILURE: %s %s", device.address, message or "")

    def notify_presence(self, device: BluetoothDevice) -> None:
        """Notify that a device is present/connected.
        
        Integrated from fork: provides dedicated presence notification.
        """
        device_name = getattr(device, 'name', None) or getattr(device, 'device_name', 'Unknown')
        device_addr = getattr(device, 'address', None) or getattr(device, 'device_address', 'Unknown')
        logger.info("[+] Device Connected: %s (%s)", device_name, device_addr)
        print(f"[+] Device Connected: {device_name} ({device_addr})")

    def notify_disconnection(self, device: BluetoothDevice) -> None:
        """Notify that a device has disconnected.
        
        Integrated from fork: provides dedicated disconnection notification.
        """
        device_name = getattr(device, 'name', None) or getattr(device, 'device_name', 'Unknown')
        device_addr = getattr(device, 'address', None) or getattr(device, 'device_address', 'Unknown')
        logger.info("[-] Device Disconnected: %s (%s)", device_name, device_addr)
        print(f"[-] Device Disconnected: {device_name} ({device_addr})")
