export interface Device {
  id?: number;
  address?: string;
  name?: string;
  rssi?: number;
  connectable?: boolean;
}

export interface HistoryRecord {
  id: number;
  device: string;
  address?: string | null;
  status: string;
  timestamp?: string | null;
}

export interface MonitorStatusState {
  running: boolean;
  deviceName?: string;
  raw?: unknown;
}

export interface ScanResponse {
  ok: boolean;
  devices: Device[];
  history: HistoryRecord[];
  error?: string;
}

export interface HistoryResponse {
  ok: boolean;
  records: HistoryRecord[];
}

export interface MonitorResultResponse {
  ok: boolean;
  result: Record<string, unknown>;
  error?: string;
}

export interface AlertState {
  tone: "positive" | "neutral" | "warning" | "danger";
  message: string;
}

export interface MonitorFormState {
  device: string;
  log: string;
  adapter: string;
  mtu: string;
  connectTimeout: string;
  pollInterval: string;
  baseBackoff: string;
  maxBackoff: string;
  runtime: string;
  metadata: string;
}
