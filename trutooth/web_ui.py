"""Flask-based Web UI for TruTooth.

Integrated from fork: Provides a human-friendly web interface for viewing
connected devices and connection history. Complements the FastAPI REST API
by offering a browser-based monitoring dashboard.

Usage:
    python -m trutooth.web_ui
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
import webbrowser
from typing import Optional

from flask import Flask, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy

from trutooth.models.db_models import init_db_models
from trutooth.models.notification_system import NotificationSystem

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------
# FLASK APP SETUP
# ---------------------------------------------------------------
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///trutooth_web.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Initialize database models
BluetoothDeviceDB, ConnectionRecordDB = init_db_models(db)


# ---------------------------------------------------------------
# BLUETOOTH MONITOR INTEGRATION
# ---------------------------------------------------------------
class BluetoothWebMonitor:
    """Monitor that integrates scanning with database updates."""
    
    def __init__(self, app: Flask, scan_interval: float = 10.0):
        self.app = app
        self.scan_interval = scan_interval
        self.is_monitoring = False
        self.thread: Optional[threading.Thread] = None
        self.notifications = NotificationSystem()
    
    def start_monitoring(self) -> None:
        """Start background monitoring thread."""
        if self.is_monitoring:
            logger.warning("Monitor already running")
            return
        self.is_monitoring = True
        self.thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.thread.start()
        logger.info("BluetoothWebMonitor started scanning...")
    
    def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self.is_monitoring = False
        logger.info("BluetoothWebMonitor stopped")
    
    def monitor_loop(self) -> None:
        """Main monitoring loop - scans and updates database."""
        while self.is_monitoring:
            try:
                asyncio.run(self.scan_and_update())
            except Exception as exc:
                logger.exception("Error during scan: %s", exc)
            time.sleep(self.scan_interval)
    
    async def scan_and_update(self) -> None:
        """Scan for devices and update database.
        
        Integrates with trutooth.scanner or falls back to direct bleak scanning.
        """
        try:
            from bleak import BleakScanner
            devices = await BleakScanner.discover(timeout=5.0)
        except Exception as exc:
            logger.error("Scan failed: %s", exc)
            return
        
        found_addresses = {d.address for d in devices}
        
        with self.app.app_context():
            # Add/update found devices
            for device in devices:
                name = device.name or "Unknown"
                address = device.address
                
                existing = BluetoothDeviceDB.query.filter_by(
                    device_address=address
                ).first()
                
                if not existing:
                    # New device
                    new_dev = BluetoothDeviceDB(
                        device_name=name,
                        device_address=address,
                        connection_status=True
                    )
                    db.session.add(new_dev)
                    db.session.commit()
                    
                    # Record connection
                    record = ConnectionRecordDB(
                        device_id=new_dev.id,
                        status="Connected"
                    )
                    db.session.add(record)
                    db.session.commit()
                    
                    # Notify
                    class DeviceStub:
                        def __init__(self, name, addr):
                            self.device_name = name
                            self.device_address = addr
                    self.notifications.notify_presence(DeviceStub(name, address))
                
                elif not existing.connection_status:
                    # Reconnected device
                    existing.connect()
                    db.session.commit()
                    
                    record = ConnectionRecordDB(
                        device_id=existing.id,
                        status="Connected"
                    )
                    db.session.add(record)
                    db.session.commit()
                    
                    class DeviceStub:
                        def __init__(self, name, addr):
                            self.device_name = name
                            self.device_address = addr
                    self.notifications.notify_presence(DeviceStub(existing.device_name, address))
            
            # Mark disconnected devices
            all_devices = BluetoothDeviceDB.query.all()
            for dev in all_devices:
                if dev.device_address not in found_addresses and dev.connection_status:
                    dev.disconnect()
                    db.session.commit()
                    
                    record = ConnectionRecordDB(
                        device_id=dev.id,
                        status="Disconnected"
                    )
                    db.session.add(record)
                    db.session.commit()
                    
                    class DeviceStub:
                        def __init__(self, name, addr):
                            self.device_name = name
                            self.device_address = addr
                    self.notifications.notify_disconnection(
                        DeviceStub(dev.device_name, dev.device_address)
                    )


# Global monitor instance
monitor = BluetoothWebMonitor(app, scan_interval=10)


# ---------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------
@app.route("/")
def index():
    """Main device listing page."""
    devices = BluetoothDeviceDB.query.all()
    return render_template_string(TEMPLATE_INDEX, devices=devices)


@app.route("/history")
def history():
    """Connection history page."""
    records = (
        ConnectionRecordDB.query
        .order_by(ConnectionRecordDB.timestamp.desc())
        .limit(100)
        .all()
    )
    return render_template_string(TEMPLATE_HISTORY, records=records)


@app.route("/api/devices")
def api_devices():
    """JSON API endpoint for devices."""
    devices = BluetoothDeviceDB.query.all()
    return jsonify([d.to_dict() for d in devices])


@app.route("/api/history")
def api_history():
    """JSON API endpoint for connection history."""
    records = (
        ConnectionRecordDB.query
        .order_by(ConnectionRecordDB.timestamp.desc())
        .limit(100)
        .all()
    )
    return jsonify([r.to_dict() for r in records])


@app.route("/monitor/start", methods=["POST"])
def start_monitor():
    """Start monitoring."""
    monitor.start_monitoring()
    return jsonify({"status": "started"})


@app.route("/monitor/stop", methods=["POST"])
def stop_monitor():
    """Stop monitoring."""
    monitor.stop_monitoring()
    return jsonify({"status": "stopped"})


# ---------------------------------------------------------------
# HTML TEMPLATES (from fork)
# ---------------------------------------------------------------
TEMPLATE_INDEX = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TruTooth - Bluetooth Monitor</title>
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      min-height: 100vh;
      padding: 20px;
    }
    .container {
      max-width: 1200px;
      margin: 0 auto;
      background: white;
      border-radius: 12px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.3);
      padding: 30px;
    }
    h1 {
      color: #333;
      margin-bottom: 10px;
      font-size: 2rem;
    }
    .subtitle {
      color: #666;
      margin-bottom: 20px;
      font-size: 1rem;
    }
    nav {
      margin-bottom: 20px;
    }
    nav a {
      color: #667eea;
      text-decoration: none;
      font-weight: 500;
      padding: 8px 16px;
      border-radius: 6px;
      background: #f0f0f0;
      transition: background 0.3s;
    }
    nav a:hover {
      background: #e0e0e0;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 20px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    th, td {
      padding: 14px;
      text-align: left;
      border-bottom: 1px solid #e0e0e0;
    }
    th {
      background: #667eea;
      color: white;
      font-weight: 600;
      text-transform: uppercase;
      font-size: 0.85rem;
      letter-spacing: 0.5px;
    }
    tr:hover {
      background: #f9f9f9;
    }
    .status {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 0.85rem;
      font-weight: 600;
    }
    .status-connected {
      background: #10b981;
      color: white;
    }
    .status-disconnected {
      background: #ef4444;
      color: white;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>🦷 TruTooth Monitor</h1>
    <p class="subtitle">Real-time Bluetooth device monitoring dashboard</p>
    <nav>
      <a href="/history">📊 View Connection History</a>
    </nav>
    <table>
      <thead>
        <tr>
          <th>Device Name</th>
          <th>MAC Address</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
      {% for d in devices %}
        <tr>
          <td><strong>{{ d.device_name }}</strong></td>
          <td><code>{{ d.device_address }}</code></td>
          <td>
            <span class="status {% if d.connection_status %}status-connected{% else %}status-disconnected{% endif %}">
              {{ "Connected" if d.connection_status else "Disconnected" }}
            </span>
          </td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</body>
</html>
"""

TEMPLATE_HISTORY = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TruTooth - Connection History</title>
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      min-height: 100vh;
      padding: 20px;
    }
    .container {
      max-width: 1200px;
      margin: 0 auto;
      background: white;
      border-radius: 12px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.3);
      padding: 30px;
    }
    h1 {
      color: #333;
      margin-bottom: 10px;
      font-size: 2rem;
    }
    .subtitle {
      color: #666;
      margin-bottom: 20px;
      font-size: 1rem;
    }
    nav {
      margin-bottom: 20px;
    }
    nav a {
      color: #667eea;
      text-decoration: none;
      font-weight: 500;
      padding: 8px 16px;
      border-radius: 6px;
      background: #f0f0f0;
      transition: background 0.3s;
    }
    nav a:hover {
      background: #e0e0e0;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 20px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    th, td {
      padding: 14px;
      text-align: left;
      border-bottom: 1px solid #e0e0e0;
    }
    th {
      background: #764ba2;
      color: white;
      font-weight: 600;
      text-transform: uppercase;
      font-size: 0.85rem;
      letter-spacing: 0.5px;
    }
    tr:hover {
      background: #f9f9f9;
    }
    .status-badge {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 0.85rem;
      font-weight: 600;
    }
    .status-connected {
      background: #10b981;
      color: white;
    }
    .status-disconnected {
      background: #ef4444;
      color: white;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>📊 Connection History</h1>
    <p class="subtitle">Historical record of device connections</p>
    <nav>
      <a href="/">← Back to Devices</a>
    </nav>
    <table>
      <thead>
        <tr>
          <th>Timestamp</th>
          <th>Device</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
      {% for r in records %}
        <tr>
          <td>{{ r.timestamp }}</td>
          <td><strong>{{ r.device.device_name if r.device else "Unknown" }}</strong></td>
          <td>
            <span class="status-badge {% if r.status == 'Connected' %}status-connected{% else %}status-disconnected{% endif %}">
              {{ r.status }}
            </span>
          </td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</body>
</html>
"""


# ---------------------------------------------------------------
# INITIALIZATION
# ---------------------------------------------------------------
def init_db():
    """Initialize database and start monitoring."""
    with app.app_context():
        db.create_all()
        if not monitor.is_monitoring:
            monitor.start_monitoring()


# ---------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------
def main():
    """Run the Flask web UI."""
    # Initialize DB and start scanning
    init_db()
    
    # Open web browser automatically
    url = "http://127.0.0.1:5000"
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    
    # Start Flask server
    app.run(debug=False, host="127.0.0.1", port=5000, use_reloader=False)


if __name__ == "__main__":
    main()
