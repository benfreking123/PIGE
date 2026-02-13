import {
  AlertState,
  Health,
  LogEvent,
  HistoricalRow,
  MarketHistoryRow,
  MarketHistoryMeta,
  MarketQuote,
  Recipient,
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
    if (text) {
      try {
        const parsed = JSON.parse(text) as { detail?: string };
        throw new Error(parsed.detail || text);
      } catch {
        throw new Error(text);
      }
    }
    throw new Error(res.statusText);
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
  getRecipients: () => request<Recipient[]>("/recipients"),
  createRecipient: (payload: { email: string; name?: string | null; is_active?: boolean; report_ids?: string[] }) =>
    request<{ status: string; id: string }>("/recipients", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateRecipient: (id: string, payload: { email?: string; name?: string | null; is_active?: boolean }) =>
    request<{ status: string }>(`/recipients/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  updateRecipientReports: (id: string, payload: { report_ids: string[] }) =>
    request<{ status: string; report_ids: string[] }>(`/recipients/${id}/reports`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteRecipient: (id: string) =>
    request<{ status: string }>(`/recipients/${id}`, {
      method: "DELETE",
    }),
  getLogs: () => request<LogEvent[]>("/logs"),
  clearReportData: () =>
    request<{ deleted_events: number; deleted_runs: number; deleted_versions: number }>("/logs/clear", {
      method: "POST",
    }),
  sendTestAlert: () =>
    request<{ status: string; recipient: string }>("/logs/test-alert", { method: "POST" }),
  getMarketContracts: () => request<{ symbols: string[] }>("/markets/contracts"),
  getMarketQuoteSymbols: () => request<{ symbols: string[] }>("/markets/quote-symbols"),
  getMarketQuotes: (symbols?: string[]) => {
    const params = symbols && symbols.length ? `?symbols=${symbols.join(",")}` : "";
    return request<MarketQuote[]>(`/markets/quotes${params}`);
  },
  refreshMarketQuotes: (symbols?: string[]) =>
    request<{ status: string; updated: number; failed?: string[] }>("/markets/quotes/refresh", {
      method: "POST",
      body: JSON.stringify({ symbols }),
    }),
  getMarketHistory: (symbol: string, start?: string, end?: string) => {
    const params = new URLSearchParams({ symbol });
    if (start) params.set("start_date", start);
    if (end) params.set("end_date", end);
    return request<MarketHistoryRow[]>(`/markets/history?${params.toString()}`);
  },
  getMarketHistoryMeta: (symbol: string) => {
    const params = new URLSearchParams({ symbol });
    return request<MarketHistoryMeta>(`/markets/history/meta?${params.toString()}`);
  },
  getBackfillCost: (start: string, end: string) =>
    request<{ estimated_cost: number; symbol_count: number }>("/markets/backfill/cost", {
      method: "POST",
      body: JSON.stringify({ start_date: start, end_date: end }),
    }),
  runBackfill: (start: string, end: string) =>
    request<{ job_id: string; status: string }>("/markets/backfill/run", {
      method: "POST",
      body: JSON.stringify({ start_date: start, end_date: end }),
    }),
  runTestBackfill: (start: string, end: string) =>
    request<{ job_id: string; status: string; symbols: string[] }>("/markets/backfill/test", {
      method: "POST",
      body: JSON.stringify({ start_date: start, end_date: end }),
    }),
  getBackfillJobs: () =>
    request<
      {
        job_id: string;
        status: string;
        start_date: string;
        end_date: string;
        updated_at: string;
        last_error?: string | null;
      }[]
    >("/markets/backfill/jobs"),
};
