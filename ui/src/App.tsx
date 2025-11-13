import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import "./App.css";
import { AlertBanner } from "./components/AlertBanner";
import { ControlToolbar } from "./components/ControlToolbar";
import { DevicesTable } from "./components/DevicesTable";
import { MonitorPanel } from "./components/MonitorPanel";
import { HistoryPanel } from "./components/HistoryPanel";
import { EventLog } from "./components/EventLog";
import { usePersistedState } from "./hooks/usePersistedState";
import {
  AlertState,
  Device,
  HistoryRecord,
  MonitorFormState,
  MonitorResultResponse,
  MonitorStatusState,
  ScanResponse
} from "./types";

const MAX_EVENTS = 400;

const DEFAULT_API_BASE = (import.meta.env.VITE_DEFAULT_API_BASE as string | undefined)?.trim() || "http://127.0.0.1:8000";
const DEFAULT_SCAN_TIMEOUT = Number(import.meta.env.VITE_DEFAULT_SCAN_TIMEOUT ?? 6) || 6;

const DEFAULT_MONITOR_FORM: MonitorFormState = {
  device: "",
  log: "metrics.csv",
  adapter: "",
  mtu: "",
  connectTimeout: "10",
  pollInterval: "5",
  baseBackoff: "2",
  maxBackoff: "60",
  runtime: "",
  metadata: ""
};

export default function App() {
  const [apiBase, setApiBase] = usePersistedState<string>("trutooth-api-base", DEFAULT_API_BASE);
  const [scanTimeout, setScanTimeout] = usePersistedState<number>("trutooth-scan-timeout", DEFAULT_SCAN_TIMEOUT);
  const [devices, setDevices] = useState<Device[]>([]);
  const [history, setHistory] = useState<HistoryRecord[]>([]);
  const [selectedAddress, setSelectedAddress] = useState<string>("");
  const [monitorStatus, setMonitorStatus] = useState<MonitorStatusState>({ running: false });
  const [monitorForm, setMonitorForm] = useState<MonitorFormState>(DEFAULT_MONITOR_FORM);
  const [isScanning, setIsScanning] = useState(false);
  const [isStartingMonitor, setIsStartingMonitor] = useState(false);
  const [isStoppingMonitor, setIsStoppingMonitor] = useState(false);
  const [alert, setAlert] = useState<AlertState | null>(null);
  const [events, setEvents] = useState<string[]>([]);

  const websocketRef = useRef<WebSocket | null>(null);
  const pollIntervalRef = useRef<number | null>(null);

  const monitorDeviceName = useMemo(
    () => monitorStatus.deviceName ?? (monitorForm.device || selectedAddress),
    [monitorStatus.deviceName, monitorForm.device, selectedAddress]
  );

  const appendEvent = useCallback((message: string) => {
    const entry = `[${new Date().toLocaleTimeString()}] ${message}`;
    setEvents((prev: string[]) => {
      const next = [...prev, entry];
      if (next.length > MAX_EVENTS) {
        return next.slice(next.length - MAX_EVENTS);
      }
      return next;
    });
  }, []);

  const setPositiveAlert = useCallback((message: string) => setAlert({ tone: "positive", message }), []);
  const setDangerAlert = useCallback((message: string) => setAlert({ tone: "danger", message }), []);

  const refreshDevices = useCallback(async () => {
    try {
      const response = await fetch("/api/devices");
      if (!response.ok) {
        throw new Error(`Device snapshot failed (${response.status})`);
      }
      const payload: Device[] = await response.json();
      setDevices(payload);
    } catch (error) {
      console.warn("Failed to refresh devices", error);
    }
  }, []);

  const refreshHistory = useCallback(async () => {
    try {
      const response = await fetch("/ui/history");
      if (!response.ok) {
        throw new Error(`History snapshot failed (${response.status})`);
      }
      const payload = (await response.json()) as { ok: boolean; records: HistoryRecord[] };
      if (payload.ok) {
        setHistory(payload.records);
      }
    } catch (error) {
      console.warn("Failed to refresh history", error);
    }
  }, []);

  const stopStatusPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      window.clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  const disconnectEventStream = useCallback(() => {
    if (websocketRef.current) {
      websocketRef.current.close();
      websocketRef.current = null;
    }
  }, []);

  const fetchStatus = useCallback(
    async (showErrors = false) => {
      try {
        const response = await fetch(`/ui/monitor/status?baseUrl=${encodeURIComponent(apiBase)}`);
        const payload = (await response.json()) as MonitorResultResponse;
        if (!payload.ok) {
          throw new Error(payload.error || "Unable to fetch monitor status");
        }
        const statusRaw = payload.result as { status?: string; device?: string };
        const running = statusRaw.status === "running";
        setMonitorStatus({ running, deviceName: statusRaw.device, raw: payload.result });
        if (!running) {
          stopStatusPolling();
        }
        return running;
      } catch (error) {
        if (showErrors) {
          setDangerAlert(error instanceof Error ? error.message : String(error));
        }
        setMonitorStatus({ running: false });
        stopStatusPolling();
        return false;
      }
    },
    [apiBase, setDangerAlert, stopStatusPolling]
  );

  const startStatusPolling = useCallback(() => {
    stopStatusPolling();
    pollIntervalRef.current = window.setInterval(() => {
      void fetchStatus(false);
    }, 5000);
  }, [fetchStatus, stopStatusPolling]);

  const connectEventStream = useCallback(() => {
    disconnectEventStream();
    try {
      const wsUrl = apiBase.replace(/^http/i, "ws") + "/events";
      const socket = new WebSocket(wsUrl);
      websocketRef.current = socket;
      socket.onopen = () => appendEvent("Event stream connected.");
      socket.onerror = () => setDangerAlert("Event stream encountered an error.");
      socket.onclose = () => appendEvent("Event stream closed.");
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data as string);
          if (payload?.csv) {
            appendEvent(payload.csv);
          } else {
            appendEvent(event.data);
          }
        } catch (error) {
          appendEvent(event.data);
        }
      };
    } catch (error) {
      setDangerAlert(`Failed to open event stream: ${error instanceof Error ? error.message : error}`);
    }
  }, [apiBase, appendEvent, disconnectEventStream, setDangerAlert]);

  const handleScan = useCallback(async () => {
    setAlert(null);
    setIsScanning(true);
    try {
      const response = await fetch("/ui/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ baseUrl: apiBase, timeout: scanTimeout })
      });
      const payload = (await response.json()) as ScanResponse;
      if (!payload.ok) {
        throw new Error(payload.error || "Scan failed");
      }
      setDevices(payload.devices || []);
      setHistory(payload.history || []);
      setPositiveAlert(`Scan completed: ${payload.devices?.length ?? 0} devices found.`);
    } catch (error) {
      setDangerAlert(error instanceof Error ? error.message : String(error));
    } finally {
      setIsScanning(false);
    }
  }, [apiBase, scanTimeout, setDangerAlert, setPositiveAlert]);

  const handleStartMonitor = useCallback(async () => {
    if (!monitorForm.device.trim()) {
      setDangerAlert("Device address is required.");
      return;
    }
    setAlert(null);
    setIsStartingMonitor(true);
    try {
      const response = await fetch("/ui/monitor/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          baseUrl: apiBase,
          device: monitorForm.device.trim(),
          log: monitorForm.log.trim() || undefined,
          adapter: monitorForm.adapter.trim() || undefined,
          mtu: monitorForm.mtu.trim() || undefined,
          connect_timeout: monitorForm.connectTimeout.trim() || undefined,
          poll_interval: monitorForm.pollInterval.trim() || undefined,
          base_backoff: monitorForm.baseBackoff.trim() || undefined,
          max_backoff: monitorForm.maxBackoff.trim() || undefined,
          runtime: monitorForm.runtime.trim() || undefined,
          metadata: monitorForm.metadata.trim() || undefined
        })
      });
      const payload = (await response.json()) as MonitorResultResponse;
      if (!payload.ok) {
        throw new Error(payload.error || "Monitor start failed");
      }
      setPositiveAlert("Monitor started successfully.");
      appendEvent("Monitor start requested.");
      connectEventStream();
      startStatusPolling();
      await refreshHistory();
    } catch (error) {
      setDangerAlert(error instanceof Error ? error.message : String(error));
    } finally {
      setIsStartingMonitor(false);
    }
  }, [apiBase, appendEvent, connectEventStream, monitorForm, refreshHistory, setDangerAlert, setPositiveAlert, startStatusPolling]);

  const handleStopMonitor = useCallback(async () => {
    setAlert(null);
    setIsStoppingMonitor(true);
    try {
      const response = await fetch("/ui/monitor/stop", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ baseUrl: apiBase })
      });
      const payload = (await response.json()) as MonitorResultResponse;
      if (!payload.ok) {
        throw new Error(payload.error || "Monitor stop failed");
      }
      setPositiveAlert("Monitor stopped.");
      appendEvent("Monitor stop requested.");
    } catch (error) {
      setDangerAlert(error instanceof Error ? error.message : String(error));
    } finally {
      setIsStoppingMonitor(false);
      disconnectEventStream();
      stopStatusPolling();
      setMonitorStatus({ running: false });
      void refreshHistory();
    }
  }, [apiBase, appendEvent, disconnectEventStream, refreshHistory, setDangerAlert, setPositiveAlert, stopStatusPolling]);

  const handleDeviceSelection = useCallback((address: string) => {
    setSelectedAddress(address);
    setMonitorForm((prev: MonitorFormState) => ({ ...prev, device: address }));
  }, []);

  const handleFormChange = useCallback((field: keyof MonitorFormState, value: string) => {
    setMonitorForm((prev: MonitorFormState) => ({ ...prev, [field]: value }));
  }, []);

  useEffect(() => {
    void refreshDevices();
    void refreshHistory();
    void fetchStatus(false);
  }, [fetchStatus, refreshDevices, refreshHistory]);

  useEffect(() => {
    return () => {
      disconnectEventStream();
      stopStatusPolling();
    };
  }, [disconnectEventStream, stopStatusPolling]);

  useEffect(() => {
    if (monitorForm.device !== selectedAddress) {
      setSelectedAddress(monitorForm.device);
    }
  }, [monitorForm.device, selectedAddress]);

  return (
    <div className="app-shell">
      <h1>TruTooth Control Center</h1>

      <AlertBanner alert={alert} onClose={() => setAlert(null)} />

      <ControlToolbar
        apiBase={apiBase}
        scanTimeout={scanTimeout}
        isScanning={isScanning}
        monitorStatus={{ ...monitorStatus, deviceName: monitorDeviceName }}
        onApiBaseChange={setApiBase}
        onScanTimeoutChange={setScanTimeout}
        onScan={handleScan}
        onCheckStatus={() => void fetchStatus(true)}
      />

      <div className="layout-grid">
        <DevicesTable devices={devices} selectedAddress={selectedAddress} onSelect={handleDeviceSelection} />
        <MonitorPanel
          form={monitorForm}
          onChange={handleFormChange}
          onStart={() => void handleStartMonitor()}
          onStop={() => void handleStopMonitor()}
          isStarting={isStartingMonitor}
          isStopping={isStoppingMonitor}
        />
      </div>

      <div className="card-spacer" />

      <div className="layout-grid">
        <HistoryPanel history={history} />
        <EventLog events={events} onClear={() => setEvents([])} />
      </div>
    </div>
  );
}
