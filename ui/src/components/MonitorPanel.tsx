import React from "react";
import { MonitorFormState } from "../types";
import { PowerIcon } from "../icons";

interface MonitorPanelProps {
  form: MonitorFormState;
  onChange(field: keyof MonitorFormState, value: string): void;
  onStart(): void;
  onStop(): void;
  isStarting: boolean;
  isStopping: boolean;
}

export function MonitorPanel({ form, onChange, onStart, onStop, isStarting, isStopping }: MonitorPanelProps) {
  const update = (field: keyof MonitorFormState) => (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    onChange(field, event.target.value);
  };

  return (
    <div className="panel">
      <h2>
        <PowerIcon width={20} height={20} /> Monitor Configuration
      </h2>
      <div className="form-grid">
        <div className="field" style={{ gridColumn: "1 / -1" }}>
          <label htmlFor="device">Device Address *</label>
          <input
            id="device"
            className="prime"
            value={form.device}
            onChange={update("device")}
            placeholder="AA:BB:CC:DD:EE:FF"
            required
          />
        </div>
        <div className="field">
          <label htmlFor="metricsLog">Metrics Log</label>
          <input
            id="metricsLog"
            className="prime"
            value={form.log}
            onChange={update("log")}
            placeholder="metrics.csv"
          />
        </div>
        <div className="field">
          <label htmlFor="adapter">Adapter</label>
          <input id="adapter" className="prime" value={form.adapter} onChange={update("adapter")} />
        </div>
        <div className="field">
          <label htmlFor="mtu">MTU</label>
          <input id="mtu" className="prime" type="number" min={23} max={247} value={form.mtu} onChange={update("mtu")} />
        </div>
        <div className="field">
          <label htmlFor="connectTimeout">Connect Timeout (s)</label>
          <input
            id="connectTimeout"
            className="prime"
            type="number"
            min={1}
            step={0.5}
            value={form.connectTimeout}
            onChange={update("connectTimeout")}
          />
        </div>
        <div className="field">
          <label htmlFor="pollInterval">Poll Interval (s)</label>
          <input
            id="pollInterval"
            className="prime"
            type="number"
            min={0.1}
            step={0.1}
            value={form.pollInterval}
            onChange={update("pollInterval")}
          />
        </div>
        <div className="field">
          <label htmlFor="baseBackoff">Base Backoff (s)</label>
          <input
            id="baseBackoff"
            className="prime"
            type="number"
            min={0.5}
            step={0.5}
            value={form.baseBackoff}
            onChange={update("baseBackoff")}
          />
        </div>
        <div className="field">
          <label htmlFor="maxBackoff">Max Backoff (s)</label>
          <input
            id="maxBackoff"
            className="prime"
            type="number"
            min={0.5}
            step={0.5}
            value={form.maxBackoff}
            onChange={update("maxBackoff")}
          />
        </div>
        <div className="field">
          <label htmlFor="runtime">Runtime Limit (s)</label>
          <input id="runtime" className="prime" type="number" min={0.1} step={0.5} value={form.runtime} onChange={update("runtime")} />
        </div>
        <div className="field" style={{ gridColumn: "1 / -1" }}>
          <label htmlFor="metadata">Metadata (JSON)</label>
          <textarea
            id="metadata"
            className="prime log"
            rows={4}
            placeholder='{"operator": "Alice"}'
            value={form.metadata}
            onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) => onChange("metadata", event.target.value)}
          />
        </div>
      </div>
      <div className="inline-actions" style={{ marginTop: 22 }}>
        <button className="primary" type="button" onClick={onStart} disabled={isStarting}>
          {isStarting ? "Launching…" : "Start Monitor"}
        </button>
        <button className="secondary" type="button" onClick={onStop} disabled={isStopping}>
          {isStopping ? "Stopping…" : "Stop Monitor"}
        </button>
      </div>
    </div>
  );
}
