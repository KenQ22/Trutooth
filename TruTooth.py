from flask import Flask, render_template_string, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import asyncio
import threading
import time
import webbrowser
from bleak import BleakScanner

# ---------------------------------------------------------------
# SETTING UP THE TABLE IN MYSQL FORMAT 
# ---------------------------------------------------------------
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///bluetooth.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ---------------------------------------------------------------
# MODELS
# ---------------------------------------------------------------
class BluetoothDevice(db.Model):
    __tablename__ = "bluetooth_devices"
    id = db.Column(db.Integer, primary_key=True)
    device_name = db.Column(db.String, nullable=False)
    device_address = db.Column(db.String, nullable=False, unique=True)
    connection_status = db.Column(db.Boolean, default=False, nullable=False)

    def connect(self):
        self.connection_status = True

    def disconnect(self):
        self.connection_status = False

    def to_dict(self):
        return {
            "id": self.id,
            "device_name": self.device_name,
            "device_address": self.device_address,
            "connection_status": self.connection_status,
        }

# ---------------------------------------------------------------
# IM GOING TO PULL OUT MY HAIR
# ---------------------------------------------------------------

class ConnectionRecord(db.Model):
    __tablename__ = "connection_records"
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey("bluetooth_devices.id"), nullable=False)
    timestamp = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(__import__("zoneinfo").ZoneInfo("America/New_York")),
        nullable=False,
    )
    status = db.Column(db.String, nullable=False)# tHOUGH IN THE THE ERROR SAYING ITS NOT DEFINED, WHICH IS BULL
    device = db.relationship("BluetoothDevice", backref="connection_history")

    def to_dict(self):
        return {
            "id": self.id,
            "device_name": self.device.device_name if self.device else None,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
        }

# ---------------------------------------------------------------
# NOTIFICATION SYSTEM
# ---------------------------------------------------------------
class NotificationSystem:
    def notify_presence(self, device):
        print(f"[+] Device Connected: {device.device_name} ({device.device_address})")

    def notify_failure(self, device):
        print(f"[-] Device Disconnected: {device.device_name} ({device.device_address})")

# ---------------------------------------------------------------
# BLUETOOTH MONITOR TOOL, GOES BACK TO CLASS DIAGRAM
# ---------------------------------------------------------------
class BluetoothMonitorTool:
    def __init__(self, app=None, scan_interval=10):
        self.app = app
        self.scan_interval = scan_interval
        self.is_monitoring = False
        self.thread = None
        self.notifications = NotificationSystem()

    def start_monitoring(self):
        if self.is_monitoring:
            return
        self.is_monitoring = True
        self.thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.thread.start()
        print("BluetoothMonitorTool started scanning...")

    def stop_monitoring(self):
        self.is_monitoring = False
        print("BluetoothMonitorTool stopped...")

    def monitor_loop(self):
        while self.is_monitoring:
            try:
                asyncio.run(self.scan_and_update())
            except Exception as e:
                print("Error scanning:", e)
            time.sleep(self.scan_interval)

    async def scan_and_update(self):
        devices = await BleakScanner.discover(timeout=5.0)
        found_addresses = {d.address for d in devices}

        with self.app.app_context():
            for d in devices:
                name = d.name or "Unknown" #IF DEVICE IS KNOWN OIF COURSE
                existing = BluetoothDevice.query.filter_by(device_address=d.address).first()

                # New device
                if not existing:
                    new_dev = BluetoothDevice(device_name=name, device_address=d.address, connection_status=True)
                    db.session.add(new_dev)
                    db.session.commit()
                    rec = ConnectionRecord(device_id=new_dev.id, status="Connected")
                    db.session.add(rec)
                    db.session.commit()
                    self.notifications.notify_presence(new_dev)

                # Reconnected device
                elif not existing.connection_status:
                    existing.connect()
                    db.session.commit()
                    rec = ConnectionRecord(device_id=existing.id, status="Connected")
                    db.session.add(rec)
                    db.session.commit()
                    self.notifications.notify_presence(existing)

            # Handle disconnected devices
            known = BluetoothDevice.query.all()
            for dev in known:
                if dev.device_address not in found_addresses and dev.connection_status:
                    dev.disconnect()
                    db.session.commit()
                    rec = ConnectionRecord(device_id=dev.id, status="Disconnected")
                    db.session.add(rec)
                    db.session.commit()
                    self.notifications.notify_failure(dev)

# ---------------------------------------------------------------
# INITIALIZATION
# ---------------------------------------------------------------
monitor = BluetoothMonitorTool(app, scan_interval=10)

def init_db():
    """Initialize database and start monitoring"""
    with app.app_context():
        db.create_all()
        if not monitor.is_monitoring:
            monitor.start_monitoring()

# ---------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------
@app.route("/")
def index():
    devices = BluetoothDevice.query.all()
    return render_template_string(TEMPLATE_INDEX, devices=devices)

@app.route("/history")
def history():
    records = ConnectionRecord.query.order_by(ConnectionRecord.timestamp.desc()).limit(100).all()
    return render_template_string(TEMPLATE_HISTORY, records=records)

@app.route("/api/devices")
def api_devices():
    devices = BluetoothDevice.query.all()
    return jsonify([d.to_dict() for d in devices])

@app.route("/api/history")
def api_history():
    records = ConnectionRecord.query.order_by(ConnectionRecord.timestamp.desc()).limit(100).all()
    return jsonify([r.to_dict() for r in records])

@app.route("/monitor/start", methods=["POST"])
def start_monitor():
    monitor.start_monitoring()
    return jsonify({"status": "started"})

@app.route("/monitor/stop", methods=["POST"])
def stop_monitor():
    monitor.stop_monitoring()
    return jsonify({"status": "stopped"})

# ---------------------------------------------------------------
# WEBPAGE GET MADE HERE
# ---------------------------------------------------------------
TEMPLATE_INDEX = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Bluetooth Monitor</title>
  <style>
    body { font-family: Arial; margin: 30px; }
    table { border-collapse: collapse; width: 100%; margin-top: 10px; }
    th, td { border: 1px solid #ccc; padding: 8px; }
    th { background: #f0f0f0; }
  </style>
</head>
<body>
  <h1>Bluetooth Monitor Tool</h1>
  <p><a href="/history">View Connection History</a></p>
  <table>
    <thead>
      <tr><th>Name</th><th>Address</th><th>Status</th></tr>
    </thead>
    <tbody>
    {% for d in devices %}
      <tr>
        <td>{{ d.device_name }}</td>
        <td>{{ d.device_address }}</td>
        <td>{{ "Connected" if d.connection_status else "Disconnected" }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
</body>
</html>
"""

TEMPLATE_HISTORY = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Connection History</title>
  <style>
    body { font-family: Arial; margin: 30px; }
    table { border-collapse: collapse; width: 100%; margin-top: 10px; }
    th, td { border: 1px solid #ccc; padding: 8px; }
    th { background: #f0f0f0; }
  </style>
</head>
<body>
  <h1>Connection History</h1>
  <p><a href="/">Back to Devices</a></p>
  <table>
    <thead><tr><th>Timestamp (EST)</th><th>Device</th><th>Status</th></tr></thead>
    <tbody>
    {% for r in records %}
      <tr>
        <td>{{ r.timestamp }}</td>
        <td>{{ r.device.device_name if r.device else "Unknown" }}</td>
        <td>{{ r.status }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
</body>
</html>
"""
# ---------------------------------------------------------------
# BARE BONES HTML DO NOT RECOMMEND 
# ---------------------------------------------------------------


# ---------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------
if __name__ == "__main__":
    # Initialize DB and start scanning BEFORE Flask starts
    init_db()

    # Open web browser automatically
    url = "http://127.0.0.1:5000"
    webbrowser.open(url)

    # Start Flask server
    app.run(debug=True, host="127.0.0.1", port=5000) #WHAT LETS THE WEBPAGE TO RUN 
