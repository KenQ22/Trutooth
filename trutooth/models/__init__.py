"""Model package for TruTooth class-diagram skeletons.

This package contains lightweight class stubs generated from the provided
class diagram. These are minimal implementations intended as a starting
point to build behavior on.
"""
from .bluetooth_device import BluetoothDevice
from .bluetooth_monitor import BluetoothMonitorTool
from .notification_system import NotificationSystem
from .connection_record import ConnectionRecord
from .connection_history import ConnectionHistory
from .communication_history import CommunicationHistory
from .opus_messages import OpusMessages

__all__ = [
    "BluetoothDevice",
    "BluetoothMonitorTool",
    "NotificationSystem",
    "ConnectionRecord",
    "ConnectionHistory",
    "CommunicationHistory",
    "OpusMessages",
]
