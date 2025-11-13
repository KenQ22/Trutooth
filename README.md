# TruTooth

TruTooth is a comprehensive Bluetooth monitoring toolkit with multiple interface options:

- **FastAPI REST API** - Programmatic access for automation and integration
- **Flask Web UI** - Browser-based monitoring dashboard (NEW)
- **Java Swing GUI** - Rich desktop control center

The backend handles device scanning, reconnection logic, and metrics collection. Choose the interface that best fits your needs: browser-based monitoring, desktop GUI, or REST API integration.

## Prerequisites

- Python 3.10+
- Java 17+
- Maven 3.8+

## Quick Start

### Option 1: Automated Launch with PowerShell (Windows)

```powershell
.\start-trutooth.ps1
```

Launches both the FastAPI backend and Java GUI in separate windows.

### Option 2: Flask Web UI (NEW - Browser-Based)

```powershell
python launch_trutooth.py --mode web
```

Opens a browser-based monitoring dashboard at `http://127.0.0.1:5000`. No Java required!

### Option 3: Unified Launcher (Most Flexible)

```powershell
# Launch only the web interface
python launch_trutooth.py --mode web

# Launch only the REST API
python launch_trutooth.py --mode api

# Launch both web and API simultaneously
python launch_trutooth.py --mode both
```

## Manual Setup

### Backend API

1. Create and activate a Python virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Launch the API (defaults to `http://127.0.0.1:8000`):
   ```bash
   uvicorn trutooth.api:app --reload
   ```

### Desktop Control Center

The Java application lives under `java/` and consumes the API.

````powershell
cd java
mvn compile
mvn exec:java
```The GUI opens with the API base URL pre-filled (`http://127.0.0.1:8000`). Use the **Scan** button to list nearby devices, select one, adjust monitor settings, and start the session. Monitor events stream in real time in the lower panel while metrics append to the configured CSV log.

**Using the Script:**
- Two PowerShell windows open automatically: one for the backend, one for the GUI.
- Close both windows when finished to stop all services.

## Tests

Backend simulations and utilities include a small pytest suite:

```bash
pytest
```

Run tests from the repository root after installing backend dependencies.

## Interface Comparison

| Feature | FastAPI REST API | Flask Web UI | Java GUI |
|---------|-----------------|--------------|----------|
| Access Method | HTTP/WebSocket | Browser | Desktop App |
| Use Case | Automation/Integration | Quick Monitoring | Advanced Control |
| Requirements | Python only | Python only | Python + Java + Maven |
| Port | 8000 | 5000 | Uses API (8000) |
| Storage | CSV Metrics | SQLite + CSV | CSV Metrics |

## Flask Web UI Features

The new browser-based interface includes:
- **Real-time device listing** with connection status
- **Connection history viewer** with timestamps
- **Modern responsive design** with gradient styling
- **Automatic background scanning** using bleak
- **SQLite database storage** for historical analysis

Access at `http://127.0.0.1:5000` after launching with `python launch_trutooth.py --mode web`

## Integration Notes

See [INTEGRATION_SUMMARY.md](INTEGRATION_SUMMARY.md) for details about the recent fork integration that added the Flask Web UI and database support.
````
