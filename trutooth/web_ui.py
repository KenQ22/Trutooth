"""Flask host for the TruTooth React UI and API proxy."""

from __future__ import annotations

import json
import logging
import os
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests
from flask import Flask, jsonify, redirect, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from requests import RequestException
from sqlalchemy.exc import SQLAlchemyError


APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent
FRONTEND_DIST = REPO_ROOT / "ui" / "dist"
INSTANCE_DIR = APP_DIR / "instance"
DATABASE_PATH = INSTANCE_DIR / "ui.sqlite3"

INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_API_BASE = os.getenv("TRUTOOTH_DEFAULT_API_BASE", "http://127.0.0.1:8000")
DEFAULT_SCAN_TIMEOUT = float(os.getenv("TRUTOOTH_DEFAULT_SCAN_TIMEOUT", "6.0"))
MAX_HISTORY_RECORDS = int(os.getenv("TRUTOOTH_UI_HISTORY_LIMIT", "500"))


app = Flask(
    __name__,
    static_folder=str(FRONTEND_DIST / "assets"),
    static_url_path="/assets",
)
app.config.update(
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{DATABASE_PATH}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)

db = SQLAlchemy(app)
logger = logging.getLogger("trutooth.web_ui")


def _utc_now() -> datetime:
    return datetime.utcnow()


class DeviceSnapshot(db.Model):  # type: ignore[misc]
    __tablename__ = "ui_device_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(255))
    rssi = db.Column(db.Integer)
    connectable = db.Column(db.Boolean, default=True)
    last_seen = db.Column(db.DateTime, default=_utc_now, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "address": self.address,
            "name": self.name or "",
            "rssi": self.rssi,
            "connectable": bool(self.connectable),
            "lastSeen": self.last_seen.isoformat() + "Z" if self.last_seen else None,
        }


class HistoryRecord(db.Model):  # type: ignore[misc]
    __tablename__ = "ui_history_records"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=_utc_now, nullable=False)
    address = db.Column(db.String(120))
    device = db.Column(db.String(255))
    status = db.Column(db.String(120))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() + "Z" if self.timestamp else None,
            "address": self.address,
            "device": self.device,
            "status": self.status,
        }


def _frontend_ready() -> bool:
    return (FRONTEND_DIST / "index.html").exists()


def _missing_frontend_response():
    message = {
        "ok": False,
        "error": "React build not found",
        "hint": "Run npm install && npm run build inside ui/.",
    }
    return jsonify(message), 503


def _normalize_base_url(base_url: Optional[str]) -> str:
    candidate = (base_url or "").strip()
    if not candidate:
        return DEFAULT_API_BASE.rstrip("/")
    return candidate.rstrip("/")


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _proxy_request(
    method: str,
    base_url: str,
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    timeout: float = 15.0,
) -> Any:
    url = f"{base_url}{path}"
    response = requests.request(method, url, params=params, timeout=timeout)
    response.raise_for_status()
    try:
        return response.json()
    except ValueError:
        if response.text:
            return json.loads(response.text)
        return None


def _store_devices(devices: Iterable[Dict[str, Any]]) -> None:
    updated = 0
    for payload in devices:
        address = (payload.get("address") or "").strip()
        if not address:
            continue
        record = DeviceSnapshot.query.filter_by(address=address).one_or_none()
        if record is None:
            record = DeviceSnapshot()
            record.address = address
            db.session.add(record)
        record.name = (payload.get("name") or "").strip() or None
        rssi_value = payload.get("rssi")
        try:
            record.rssi = int(rssi_value) if rssi_value is not None else None
        except (TypeError, ValueError):
            record.rssi = None
        connectable = payload.get("connectable")
        if connectable is not None:
            record.connectable = bool(connectable)
        record.last_seen = _utc_now()
        updated += 1
    if updated:
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            logger.exception("Failed to persist device snapshots")


def _snapshot_devices(limit: int = 200) -> List[Dict[str, Any]]:
    rows = (
        DeviceSnapshot.query.order_by(DeviceSnapshot.last_seen.desc())
        .limit(limit)
        .all()
    )
    return [row.to_dict() for row in rows]


def _append_history(address: Optional[str], device: Optional[str], status: str) -> None:
    entry = HistoryRecord()
    entry.address = (address or "").strip() or None
    entry.device = (device or "").strip() or None
    entry.status = status
    db.session.add(entry)
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        logger.exception("Failed to persist history entry")
        return
    _prune_history()


def _prune_history() -> None:
    total = HistoryRecord.query.count()
    if total <= MAX_HISTORY_RECORDS:
        return
    excess = total - MAX_HISTORY_RECORDS
    rows = (
        HistoryRecord.query.order_by(HistoryRecord.timestamp.asc())
        .limit(excess)
        .all()
    )
    for row in rows:
        db.session.delete(row)
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        logger.exception("Failed to prune history entries")


def _snapshot_history(limit: int = 200) -> List[Dict[str, Any]]:
    rows = (
        HistoryRecord.query.order_by(HistoryRecord.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [row.to_dict() for row in rows]


@app.get("/api/health")
def api_health():
    return jsonify({"status": "ok", "time": _utc_now().isoformat() + "Z"})


@app.get("/api/devices")
def api_devices():
    return jsonify(_snapshot_devices())


@app.post("/ui/scan")
def ui_scan():
    payload = request.get_json(silent=True) or {}
    base_url = _normalize_base_url(payload.get("baseUrl"))
    timeout = _safe_float(payload.get("timeout"), DEFAULT_SCAN_TIMEOUT)
    params = {"timeout": timeout}
    try:
        result = _proxy_request(
            "GET",
            base_url,
            "/scan",
            params=params,
            timeout=max(timeout + 5.0, 10.0),
        )
    except RequestException as exc:
        logger.warning("Scan proxy failed: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 502
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Scan proxy failed unexpectedly")
        return jsonify({"ok": False, "error": str(exc)}), 502

    devices: List[Dict[str, Any]] = []
    if isinstance(result, list):
        for item in result:
            if not isinstance(item, dict):
                continue
            devices.append(
                {
                    "address": item.get("address"),
                    "name": item.get("name"),
                    "rssi": item.get("rssi"),
                    "connectable": item.get("connectable", True),
                }
            )

    _store_devices(devices)
    return jsonify({"ok": True, "devices": devices, "history": _snapshot_history()})


@app.post("/ui/monitor/start")
def ui_monitor_start():
    payload = request.get_json(silent=True) or {}
    base_url = _normalize_base_url(payload.pop("baseUrl", None))
    params = {k: v for k, v in payload.items() if v not in (None, "", [])}
    try:
        result = _proxy_request(
            "POST",
            base_url,
            "/monitor/start",
            params=params,
            timeout=30.0,
        )
    except RequestException as exc:
        logger.warning("Monitor start failed: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 502
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Monitor start failed unexpectedly")
        return jsonify({"ok": False, "error": str(exc)}), 502

    address = params.get("device")
    device_name = address
    if isinstance(result, dict):
        device_name = result.get("device") or device_name
    if address or device_name:
        _append_history(address=address, device=device_name, status="monitor-started")
    return jsonify({"ok": True, "result": result})


@app.post("/ui/monitor/stop")
def ui_monitor_stop():
    payload = request.get_json(silent=True) or {}
    base_url = _normalize_base_url(payload.get("baseUrl"))
    try:
        result = _proxy_request(
            "POST",
            base_url,
            "/monitor/stop",
            timeout=15.0,
        )
    except RequestException as exc:
        logger.warning("Monitor stop failed: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 502
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Monitor stop failed unexpectedly")
        return jsonify({"ok": False, "error": str(exc)}), 502

    _append_history(address=None, device=None, status="monitor-stopped")
    return jsonify({"ok": True, "result": result})


@app.get("/ui/monitor/status")
def ui_monitor_status():
    base_url = _normalize_base_url(request.args.get("baseUrl"))
    try:
        result = _proxy_request(
            "GET",
            base_url,
            "/monitor/status",
            timeout=15.0,
        )
    except RequestException as exc:
        logger.warning("Monitor status failed: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 502
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Monitor status failed unexpectedly")
        return jsonify({"ok": False, "error": str(exc)}), 502
    return jsonify({"ok": True, "result": result})


@app.get("/ui/history")
def ui_history():
    return jsonify({"ok": True, "records": _snapshot_history()})


@app.route("/", methods=["GET"])
def root_redirect():
    return redirect("/ui", code=307)


@app.route("/ui", defaults={"path": ""})
@app.route("/ui/<path:path>")
def ui_app(path: str):
    if not _frontend_ready():
        return _missing_frontend_response()
    target = FRONTEND_DIST / path
    if path and target.is_file():
        return send_from_directory(FRONTEND_DIST, path)
    return send_from_directory(FRONTEND_DIST, "index.html")


def init_db() -> None:
    with app.app_context():
        db.create_all()


try:
    init_db()
except Exception:  # pragma: no cover - defensive bootstrap
    logger.exception("Database bootstrap failed during module import")


def main() -> None:
    init_db()
    url = "http://127.0.0.1:5000"
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(debug=False, host="127.0.0.1", port=5000, use_reloader=False)


if __name__ == "__main__":
    main()
