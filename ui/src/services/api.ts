import {
  AlertState,
  Health,
  LogEvent,
  HistoricalRow,
  ReportConfig,
  ReportLatest,
  ReportRun,
  ReportSummary,
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getHealth: () => request<Health>("/health"),
  getReports: () => request<ReportSummary[]>("/reports"),
  getReportRuns: (id: string) => request<ReportRun[]>(`/reports/${id}/runs`),
  getReportLatest: (id: string) => request<ReportLatest>(`/reports/${id}/latest`),
  getReportConfig: (id: string) => request<ReportConfig>(`/reports/${id}/config`),
  updateReportConfig: (id: string, payload: ReportConfig) =>
    request(`/reports/${id}/config`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  getHistoricals: (id: string, start?: string, end?: string) => {
    const params = new URLSearchParams();
    if (start) params.set("start_date", start);
    if (end) params.set("end_date", end);
    const suffix = params.toString() ? `?${params.toString()}` : "";
    return request<HistoricalRow[]>(`/reports/${id}/historicals${suffix}`);
  },
  gatherHistoricals: (id: string, start: string, end: string) =>
    request(`/reports/${id}/gather`, {
      method: "POST",
      body: JSON.stringify({ start_date: start, end_date: end }),
    }),
  runReport: (id: string) => request(`/reports/${id}/run`, { method: "POST" }),
  getAlerts: () => request<AlertState[]>("/alerts"),
  getLogs: () => request<LogEvent[]>("/logs"),
  clearReportData: () =>
    request<{ deleted_events: number; deleted_runs: number; deleted_versions: number }>("/logs/clear", {
      method: "POST",
    }),
};
