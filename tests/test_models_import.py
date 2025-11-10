"""Simple smoke test to ensure model skeletons import correctly."""
from trutooth.models import BluetoothDevice, BluetoothMonitorTool, NotificationSystem


def test_imports():
    d = BluetoothDevice(address="00:11:22:33:44:55", name="Test")
    monitor = BluetoothMonitorTool()
    notifier = NotificationSystem()
    assert d.address == "00:11:22:33:44:55"
    assert isinstance(monitor.check_connection_state(), list)
    assert callable(notifier.notify_success)


if __name__ == "__main__":
    test_imports()
    print("models import smoke test: OK")
