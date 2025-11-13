import React from "react";
import { MonitorStatusState } from "../types";
import { PulseIcon, RadarIcon, RefreshIcon } from "../icons";

interface ControlToolbarProps {
  apiBase: string;
  scanTimeout: number;
  isScanning: boolean;
  monitorStatus: MonitorStatusState;
  onApiBaseChange(value: string): void;
  onScanTimeoutChange(value: number): void;
  onScan(): void;
  onCheckStatus(): void;
}

export function ControlToolbar({
  apiBase,
  scanTimeout,
  isScanning,
  monitorStatus,
  onApiBaseChange,
  onScanTimeoutChange,
  onScan,
  onCheckStatus
}: ControlToolbarProps) {
  const statusLabel = monitorStatus.running
    ? `Monitoring ${monitorStatus.deviceName ?? "device"}`
    : "Monitor Idle";

  return (
    <div className="toolbar">
      <div className="field" style={{ flex: "2 1 320px" }}>
        <label htmlFor="apiBase">API Base URL</label>
        <input
          id="apiBase"
          className="prime"
          value={apiBase}
          onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
            onApiBaseChange(event.target.value)
          }
          placeholder="http://127.0.0.1:8000"
        />
      </div>
      <div className="field" style={{ maxWidth: 160 }}>
        <label htmlFor="scanTimeout">Scan Timeout (s)</label>
        <input
          id="scanTimeout"
          className="prime"
          type="number"
          min={1}
          step={1}
          value={scanTimeout}
          onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
            onScanTimeoutChange(Number(event.target.value))
          }
        />
      </div>
      <div className="field" style={{ flex: "0 0 auto", alignSelf: "stretch" }}>
        <label>&nbsp;</label>
        <button className="primary" type="button" onClick={onScan} disabled={isScanning}>
          <span style={{ display: "inline-flex", gap: 8, alignItems: "center" }}>
            <RadarIcon width={18} height={18} />
            {isScanning ? "Scanning…" : "Scan"}
          </span>
        </button>
      </div>
      <div className="field" style={{ flex: "0 0 auto", alignSelf: "stretch" }}>
        <label>&nbsp;</label>
        <button className="secondary" type="button" onClick={onCheckStatus}>
          <span style={{ display: "inline-flex", gap: 8, alignItems: "center" }}>
            <RefreshIcon width={18} height={18} />
            Refresh Status
          </span>
        </button>
      </div>
      <div className="field" style={{ marginLeft: "auto", flex: "0 0 auto" }}>
        <label>Status</label>
        <span
          className={`status-pill ${monitorStatus.running ? "running" : "idle"}`}
          title={monitorStatus.raw ? JSON.stringify(monitorStatus.raw) : undefined}
        >
          <PulseIcon width={16} height={16} />
          {statusLabel}
        </span>
      </div>
    </div>
  );
}
