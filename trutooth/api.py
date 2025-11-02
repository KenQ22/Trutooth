from __future__ import annotations
import asyncio, json, os, time
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse
try:
    from trutooth.scanner import discover
    from trutooth.reconnect import Reconnector
    from trutooth.metrics import MetricsLogger
except Exception:
    # fallback minimal stubs if running without full package in this environment
    async def discover(timeout: float = 6.0):
        await asyncio.sleep(0.1)
        return []
    class MetricsLogger:
        def __init__(self, path): pass
    class Reconnector:
        def __init__(self, address, log=None): self.address = address
        async def run(self, runtime=None): await asyncio.sleep(runtime or 1.0)

app = FastAPI(title="TruTooth API", version="0.1.0")

_rec_task: Optional[asyncio.Task] = None
_rec: Optional[Reconnector] = None
_log_path: Optional[str] = None

@app.get("/health")
async def health():
    return {"status": "ok", "time": time.time()}

@app.get("/scan")
async def scan(timeout: float = 6.0):
    devs = await discover(timeout)
    def item(d):
        return {"address": getattr(d, "address", None), "name": getattr(d, "name", None), "rssi": getattr(d, "rssi", None)}
    return JSONResponse([item(d) for d in devs])

@app.post("/monitor/start")
async def start(device: str = Query(..., description="MAC/UUID of target device"),
                log: str = Query("metrics.csv")):
    global _rec_task, _rec, _log_path
    if _rec_task and not _rec_task.done():
        return {"status": "already-running", "device": getattr(_rec, "address", None)}
    _log_path = log
    _rec = Reconnector(device, log=MetricsLogger(log))
    _rec_task = asyncio.create_task(_rec.run())
    return {"status": "started", "device": device, "log": log}

@app.post("/monitor/stop")
async def stop():
    global _rec_task
    if _rec_task:
        _rec_task.cancel()
        try:
            await _rec_task
        except Exception:
            pass
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
