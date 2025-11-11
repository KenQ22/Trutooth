# TruTooth

TruTooth is a Bluetooth monitoring toolkit that exposes a FastAPI backend along with a desktop control center written in Java Swing. The API handles device scanning, reconnection logic, and metrics collection, while the GUI provides an operator-friendly way to observe nearby devices, configure monitor sessions, and stream live events.

## Prerequisites

- Python 3.10+
- Java 17+
- Maven 3.8+

## Quick Start

**Automated Launch (Recommended for Windows):**

```powershell
.\start-trutooth.ps1
```

This script checks for Python, Java, and Maven, then launches both the backend API and GUI in separate windows.

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
````

Run tests from the repository root after installing backend dependencies.
