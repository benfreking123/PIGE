import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../services/api";
import { LogEvent } from "../types";

function loadLogs(setEvents: (e: LogEvent[]) => void, setError: (e: string | null) => void) {
  setError(null);
  api.getLogs().then(setEvents).catch((err) => setError(String(err)));
}

export default function Logs() {
  const [events, setEvents] = useState<LogEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [clearing, setClearing] = useState(false);
  const [sendingTestAlert, setSendingTestAlert] = useState(false);
  const [eventTypeFilter, setEventTypeFilter] = useState<string>("all");
  const [reportFilter, setReportFilter] = useState<string>("");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [autoRefresh, setAutoRefresh] = useState<boolean>(false);

  const refresh = useCallback(() => loadLogs(setEvents, setError), []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = window.setInterval(() => refresh(), 15000);
    return () => window.clearInterval(id);
  }, [autoRefresh, refresh]);

  const eventTypes = useMemo(() => {
    const values = new Set<string>();
    events.forEach((event) => values.add(event.event_type));
    return Array.from(values);
  }, [events]);

  const filtered = useMemo(() => {
    return events.filter((event) => {
      if (eventTypeFilter !== "all" && event.event_type !== eventTypeFilter) {
        return false;
      }
      if (reportFilter && !event.report_id.toLowerCase().includes(reportFilter.toLowerCase())) {
        return false;
      }
      if (startDate) {
        const eventDate = event.created_at.slice(0, 10);
        if (eventDate < startDate) return false;
      }
      if (endDate) {
        const eventDate = event.created_at.slice(0, 10);
        if (eventDate > endDate) return false;
      }
      return true;
    });
  }, [events, eventTypeFilter, reportFilter, startDate, endDate]);

  const exportCsv = () => {
    const headers = ["created_at", "event_type", "report_id", "run_id", "message"];
    const rows = filtered.map((event) => [
      event.created_at,
      event.event_type,
      event.report_id,
      event.run_id,
      (event.message || "").replaceAll('"', '""'),
    ]);
    const csv = [headers.join(","), ...rows.map((r) => r.map((v) => `"${v}"`).join(","))].join(
      "\n"
    );
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "logs.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const badgeClass = (type: string) => {
    if (type.startsWith("published")) return "pill success";
    if (type.startsWith("error")) return "pill error";
    if (type.includes("waiting")) return "pill warning";
    return "pill info";
  };

  const handleClearData = () => {
    if (!window.confirm("Delete all report runs, events, and historical data? This cannot be undone.")) return;
    setClearing(true);
    setError(null);
    api
      .clearReportData()
      .then((result) => {
        setEvents([]);
        refresh();
        alert(
          `Cleared: ${result.deleted_events} events, ${result.deleted_runs} runs, ${result.deleted_versions} versions.`
        );
      })
      .catch((err) => setError(String(err)))
      .finally(() => setClearing(false));
  };

  const handleSendTestAlert = () => {
    setSendingTestAlert(true);
    setError(null);
    api
      .sendTestAlert()
      .then((result) => {
        alert(`Test alert sent to ${result.recipient}. Check that inbox to verify email is working.`);
      })
      .catch((err) => setError(String(err)))
      .finally(() => setSendingTestAlert(false));
  };

  return (
    <div>
      <h1>Logs</h1>
      <div style={{ marginBottom: "1rem", display: "flex", gap: "0.5rem", alignItems: "center" }}>
        <button type="button" className="button" onClick={handleSendTestAlert} disabled={sendingTestAlert}>
          {sendingTestAlert ? "Sending…" : "Send test alert"}
        </button>
        <button type="button" className="button" onClick={handleClearData} disabled={clearing}>
          {clearing ? "Clearing…" : "Clear all report data"}
        </button>
        <button type="button" className="button secondary" onClick={exportCsv}>
          Export CSV
        </button>
      </div>
      <div className="card">
        <h3>Filters</h3>
        <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
          <label>
            Event Type
            <select
              value={eventTypeFilter}
              onChange={(e) => setEventTypeFilter(e.target.value)}
              style={{ marginLeft: "8px" }}
            >
              <option value="all">All</option>
              {eventTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>
          <label>
            Report Id
            <input
              value={reportFilter}
              onChange={(e) => setReportFilter(e.target.value)}
              placeholder="e.g. PK600"
              style={{ marginLeft: "8px" }}
            />
          </label>
          <label>
            Start
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              style={{ marginLeft: "8px" }}
            />
          </label>
          <label>
            End
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              style={{ marginLeft: "8px" }}
            />
          </label>
          <label style={{ display: "flex", gap: "6px", alignItems: "center" }}>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh (15s)
          </label>
        </div>
      </div>
      {error && <div className="card">Error: {error}</div>}
      <table className="table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Type</th>
            <th>Report</th>
            <th>Run</th>
            <th>Message</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((event) => (
            <tr key={`${event.run_id}-${event.created_at}`}>
              <td>{event.created_at}</td>
              <td>
                <span className={badgeClass(event.event_type)}>{event.event_type}</span>
              </td>
              <td>{event.report_id}</td>
              <td>{event.run_id}</td>
              <td>{event.message || "-"}</td>
            </tr>
          ))}
          {filtered.length === 0 && (
            <tr>
              <td colSpan={5}>No events found.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
