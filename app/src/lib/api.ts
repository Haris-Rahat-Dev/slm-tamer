export const API = "http://127.0.0.1:8765";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { "content-type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `${res.status} ${res.statusText}`);
  }
  return res.json();
}

export function jobWs(jobId: string): WebSocket {
  return new WebSocket(`ws://127.0.0.1:8765/ws/jobs/${jobId}`);
}

export interface SearchHit {
  repo_id: string;
  downloads: number;
  likes: number;
  params: number | null;
}

export interface LocalModel {
  repo_id: string;
  path: string;
  size_bytes: number;
}

export interface JobRow {
  id: string;
  kind: string;
  status: string;
  params: Record<string, unknown>;
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface EngineInfo {
  name: string;
  available: boolean;
  device: string | null;
}

export function formatBytes(n: number): string {
  if (!n) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  let v = n;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(1)} ${units[i]}`;
}

export function formatParams(n: number | null): string {
  if (!n) return "—";
  return `${(n / 1e9).toFixed(1)}B`;
}
