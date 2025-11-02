# trutooth/scanner.py
from __future__ import annotations
import asyncio
from typing import Optional, List, Dict, Any
from bleak import BleakScanner

async def discover(timeout: float = 6.0,
                   name_prefix: Optional[str] = None,
                   min_rssi: Optional[int] = None) -> List[Dict[str, Any]]:
    devs = await BleakScanner.discover(timeout=timeout)
    out = []
    for d in devs:
        rec = {
            "address": getattr(d, "address", None) or getattr(d, "uuid", None),
            "name": getattr(d, "name", None),
            "rssi": getattr(d, "rssi", None),
            "metadata": getattr(d, "metadata", {}) or {}
        }
        if name_prefix and (not (rec["name"] or "").startswith(name_prefix)):
            continue
        if min_rssi is not None and rec["rssi"] is not None and rec["rssi"] < min_rssi:
            continue
        out.append(rec)
    return out

async def _main():
    for d in await discover(6):
        print(f'{d["address"]:>20}  {str(d["rssi"]):>4}  {d["name"]}')

if __name__ == "__main__":
    asyncio.run(_main())
