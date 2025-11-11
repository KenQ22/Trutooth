from __future__ import annotations
import asyncio, json, logging, os, time
from typing import Optional, TYPE_CHECKING
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.responses import JSONResponse
if TYPE_CHECKING:  # pragma: no cover - typing only
    from trutooth.scanner import discover
    from trutooth.reconnect import Reconnector
    from trutooth.metrics import MetricsLogger
else:
    try:
        from trutooth.scanner import discover
        from trutooth.reconnect import Reconnector
        from trutooth.metrics import MetricsLogger
    except Exception:
        # fallback minimal stubs if running without full package in this environment
        async def discover(timeout: float = 6.0):
            await asyncio.sleep(0.1)
            return []
        class MetricsLogger:  # type: ignore
            def __init__(self, path, *_, **__):
                self.path = path
            def log(self, *_, **__):
                pass
            async def log_async(self, *_, **__):
                pass
        class Reconnector:  # type: ignore
            def __init__(self, address, *_, log=None, **__):
                self.address = address
                self._log = log
                self._stop = asyncio.Event()
            async def run(self, runtime=None):
                await asyncio.sleep(runtime or 1.0)
            def request_stop(self):
                self._stop.set()

app = FastAPI(title="TruTooth API", version="0.1.0")

_rec_task: Optional[asyncio.Task] = None
_rec: Optional[Reconnector] = None
_log_path: Optional[str] = None

@app.get("/health")
async def health():
    return {"status": "ok", "time": time.time()}


@app.get("/scan")
async def scan(timeout: float = 6.0):
    """Primary scan endpoint.

    Prefer direct Bleak discovery (fast/reliable on Windows) and fall back to
    the package scanner if Bleak is unavailable or errors.
    """
    # Try direct bleak path first
    try:
        from bleak import BleakScanner  # type: ignore
        results = await BleakScanner.discover(timeout=timeout, return_adv=True)
        devices = []
        for dev, adv in results.values():
            devices.append({
                "address": getattr(dev, "address", None),
                "name": getattr(dev, "name", None),
                "rssi": getattr(adv, "rssi", getattr(dev, "rssi", None)),
            })
        return JSONResponse(devices)
    except Exception:
        # Fall back to the library scanner implementation
        devs = await discover(timeout)
        def item(d):
            return {
                "address": getattr(d, "address", None),
                "name": getattr(d, "name", None),
                "rssi": getattr(d, "rssi", None),
            }
        return JSONResponse([item(d) for d in devs])

@app.get("/scan/debug")
async def scan_debug(timeout: float = 6.0):
    """Attempt a direct bleak scan bypassing import fallback.

    Returns:
        JSON with keys:
        - mode: 'bleak' if BleakScanner used, 'fallback' otherwise
        - count: number of devices
        - devices: list of device dicts (address, name, rssi)
        - error: optional error string if failure occurred
    """
    try:
        from bleak import BleakScanner  # type: ignore
        if BleakScanner is None:
            raise RuntimeError("BleakScanner unavailable (None)")
        # Use return_adv to capture RSSI reliably across platforms.
        results = await BleakScanner.discover(timeout=timeout, return_adv=True)
        devices = []
        for dev, adv in results.values():
            devices.append({
                "address": getattr(dev, "address", None),
                "name": getattr(dev, "name", None),
                "rssi": getattr(adv, "rssi", getattr(dev, "rssi", None)),
            })
        return {
            "mode": "bleak",
            "count": len(devices),
            "devices": devices,
        }
    except Exception as exc:
        # Fallback path: attempt existing discover (may be stub)
        try:
            devs = await discover(timeout)
            devices = [{
                "address": getattr(d, "address", None),
                "name": getattr(d, "name", None),
                "rssi": getattr(d, "rssi", None),
            } for d in devs]
            return {
                "mode": "fallback",
                "count": len(devices),
                "devices": devices,
                "error": str(exc),
            }
        except Exception as inner:
            return {
                "mode": "error",
                "count": 0,
                "devices": [],
                "error": f"{exc}; secondary discover failed: {inner}",
            }

@app.post("/monitor/start")
async def start(
    device: str = Query(..., description="MAC/UUID of target device"),
    log: str = Query("metrics.csv"),
    adapter: Optional[str] = Query(None, description="BLE adapter identifier"),
    mtu: Optional[int] = Query(None, ge=23, le=247, description="Preferred MTU size"),
    connect_timeout: float = Query(10.0, ge=1.0, description="Connection timeout seconds"),
    poll_interval: float = Query(5.0, ge=0.1, description="RSSI polling interval seconds"),
    base_backoff: float = Query(2.0, ge=0.5, description="Initial reconnect backoff"),
    max_backoff: float = Query(60.0, ge=0.5, description="Maximum reconnect backoff"),
    runtime: Optional[float] = Query(None, ge=0.1, description="Optional monitor duration"),
    metadata: Optional[str] = Query(
        None,
        description="Optional JSON metadata to include with metrics",
    ),
):
    global _rec_task, _rec, _log_path
    if _rec_task and not _rec_task.done():
        return {"status": "already-running", "device": getattr(_rec, "address", None)}
    try:
        extra = json.loads(metadata) if metadata else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid metadata JSON: {exc}")

    _log_path = log
    metrics_logger = MetricsLogger(log)
    _rec = Reconnector(
        device,
        log=metrics_logger,
        adapter=adapter,
        mtu=mtu,
        connect_timeout=connect_timeout,
        poll_interval=poll_interval,
        base_backoff=base_backoff,
        max_backoff=max_backoff,
        metadata=extra,
    )
    _rec_task = asyncio.create_task(_rec.run(runtime=runtime))
    return {
        "status": "started",
        "device": device,
        "log": log,
        "adapter": adapter,
        "runtime": runtime,
    }

@app.post("/monitor/stop")
async def stop():
    global _rec_task
    if _rec_task:
        if _rec:
            _rec.request_stop()
        _rec_task.cancel()
        try:
            await _rec_task
        except asyncio.CancelledError:
            pass
        except Exception:
            logger = logging.getLogger("trutooth.api")
            logger.exception("monitor stop encountered error")
        _rec_task = None
        return {"status": "stopped"}
    return {"status": "idle"}

@app.websocket("/events")
async def events(ws: WebSocket):
    await ws.accept()
    pos = 0
    try:
        while True:
            await asyncio.sleep(0.5)
            if not _log_path or not os.path.exists(_log_path):
                continue
            with open(_log_path, "r", encoding="utf-8") as f:
                f.seek(pos)
                for line in f:
                    await ws.send_text(json.dumps({"csv": line.strip()}))
                pos = f.tell()
    except WebSocketDisconnect:
        return
