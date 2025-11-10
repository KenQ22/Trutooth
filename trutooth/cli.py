"""TruTooth command-line interface."""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import signal
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from trutooth.metrics import MetricsLogger
from trutooth.reconnect import Reconnector
from trutooth.scanner import discover

try:  # pragma: no cover - optional rich rendering
	from rich.console import Console
	from rich.table import Table
except Exception:  # pragma: no cover
	Console = None  # type: ignore
	Table = None  # type: ignore


def _result_to_dict(item: Any) -> Dict[str, Any]:
	if hasattr(item, "to_dict"):
		return item.to_dict()  # type: ignore[return-value]
	return {
		"address": getattr(item, "address", None),
		"name": getattr(item, "name", None),
		"rssi": getattr(item, "rssi", None),
	}


def _parse_metadata(raw: Optional[str]) -> Dict[str, Any]:
	if not raw:
		return {}
	try:
		value = json.loads(raw)
	except json.JSONDecodeError as exc:
		raise ValueError(f"invalid metadata JSON: {exc}") from exc
	if not isinstance(value, dict):
		raise ValueError("metadata must be a JSON object")
	return value


async def _cmd_scan(args: argparse.Namespace) -> int:
	results = await discover(
		timeout=args.timeout,
		service_uuids=args.service_uuid or None,
		addresses=args.address or None,
		names=args.name or None,
		max_devices=args.limit,
	)
	data = [_result_to_dict(item) for item in results]
	if args.json:
		json.dump(data, sys.stdout, indent=2)
		sys.stdout.write("\n")
		return 0
	if Console and Table:
		console = Console()
		table = Table(title="TruTooth Scan Results", show_lines=False)
		for column in ("address", "name", "rssi"):
			table.add_column(column.upper())
		for entry in data:
			table.add_row(
				str(entry.get("address", "")),
				str(entry.get("name", "")),
				str(entry.get("rssi", "")),
			)
		console.print(table)
	else:
		for entry in data:
			sys.stdout.write(f"{entry.get('address')}	{entry.get('name')}	{entry.get('rssi')}\n")
	return 0


async def _cmd_monitor(args: argparse.Namespace) -> int:
	metadata = _parse_metadata(args.metadata)
	log_path = Path(args.log)
	log_path.parent.mkdir(parents=True, exist_ok=True)
	logger = MetricsLogger(log_path)
	reconnector = Reconnector(
		address=args.device,
		log=logger,
		adapter=args.adapter,
		mtu=args.mtu,
		connect_timeout=args.connect_timeout,
		poll_interval=args.poll_interval,
		base_backoff=args.base_backoff,
		max_backoff=args.max_backoff,
		metadata=metadata,
	)

	stop_event = asyncio.Event()

	def _signal_handler(*_: Any) -> None:
		reconnector.request_stop()
		stop_event.set()

	loop = asyncio.get_event_loop()
	for sig in (signal.SIGINT, signal.SIGTERM):
		with contextlib.suppress(NotImplementedError):
			loop.add_signal_handler(sig, _signal_handler)

	try:
		await reconnector.run(runtime=args.runtime)
	except KeyboardInterrupt:
		reconnector.request_stop()
	finally:
		reconnector.request_stop()
		stop_event.set()
		with contextlib.suppress(asyncio.TimeoutError):
			await asyncio.wait_for(stop_event.wait(), timeout=1.0)
	return 0


def _build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="TruTooth BLE utilities")
	sub = parser.add_subparsers(dest="command", required=True)

	scan = sub.add_parser("scan", help="Discover nearby BLE devices")
	scan.add_argument("--timeout", type=float, default=6.0, help="Scan timeout in seconds")
	scan.add_argument("--service-uuid", action="append", help="Filter by service UUID", dest="service_uuid")
	scan.add_argument("--address", action="append", help="Filter by device address")
	scan.add_argument("--name", action="append", help="Filter by device name")
	scan.add_argument("--limit", type=int, help="Maximum devices to return")
	scan.add_argument("--json", action="store_true", help="Output JSON")
	scan.set_defaults(handler=_cmd_scan)

	monitor = sub.add_parser("monitor", help="Maintain a BLE connection and log metrics")
	monitor.add_argument("device", help="MAC/UUID of target device")
	monitor.add_argument("--log", default="metrics.csv", help="Path to metrics CSV")
	monitor.add_argument("--adapter", help="BLE adapter identifier")
	monitor.add_argument("--mtu", type=int, help="Preferred MTU size")
	monitor.add_argument("--connect-timeout", type=float, default=10.0, help="Connection timeout seconds")
	monitor.add_argument("--poll-interval", type=float, default=5.0, help="RSSI polling interval seconds")
	monitor.add_argument("--base-backoff", type=float, default=2.0, help="Initial reconnect backoff")
	monitor.add_argument("--max-backoff", type=float, default=60.0, help="Maximum reconnect backoff")
	monitor.add_argument("--runtime", type=float, help="Optional monitor duration seconds")
	monitor.add_argument("--metadata", help="JSON object to embed in metrics")
	monitor.set_defaults(handler=_cmd_monitor)

	return parser


def main(argv: Optional[List[str]] = None) -> int:
	parser = _build_parser()
	args = parser.parse_args(argv)
	try:
		return asyncio.run(args.handler(args))
	except ValueError as exc:
		parser.error(str(exc))


if __name__ == "__main__":
	sys.exit(main())
