export type Health = {
  status: string;
  db_ok: boolean;
  db_ping_ms?: number | null;
  scheduler_running: boolean;
  uptime_seconds?: number;
};

export type ReportRun = {
  id: string;
  report_id: string;
  report_date: string | null;
  state: string;
  attempt: number;
  run_started_at: string;
  run_finished_at: string | null;
  error_type?: string | null;
  error_message?: string | null;
  payload_hash?: string | null;
};

export type ReportVersion = {
  id: string;
  report_id: string;
  report_date: string;
  payload_hash: string;
  created_at: string;
};

export type ReportSummary = {
  report_id: string;
  name: string;
  latest_run: ReportRun | null;
  latest_version: ReportVersion | null;
};

export type ReportLatest = {
  report_id: string;
  report_date: string;
  payload_hash: string;
  parsed_fields: Record<string, unknown>;
  source_urls: string[];
  created_at: string;
};

export type ReportConfig = Record<string, unknown>;

export type HistoricalRow = {
  report_id: string;
  report_date: string;
  payload_hash: string;
  parsed_fields: Record<string, unknown>;
  created_at: string;
};

export type AlertState = {
  report_id: string;
  consecutive_failures: number;
  last_failure_at: string | null;
  updated_at: string;
};

export type LogEvent = {
  run_id: string;
  report_id: string;
  event_type: string;
  message: string | null;
  data: Record<string, unknown> | null;
  created_at: string;
};

export type MarketQuote = {
  symbol?: string;
  price?: number;
  last_update?: string;
};

export type MarketHistoryRow = {
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
  open_interest: number | null;
};

export type MarketHistoryMeta = {
  symbol: string;
  min_date: string;
  max_date: string;
};

export type Recipient = {
  id: string;
  email: string;
  name: string | null;
  is_active: boolean;
  report_ids: string[];
};
