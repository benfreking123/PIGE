import { useCallback, useEffect, useState } from "react";
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

  const refresh = useCallback(() => loadLogs(setEvents, setError), []);

  useEffect(() => {
    refresh();
  }, [refresh]);

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

  return (
    <div>
      <h1>Logs</h1>
      <div style={{ marginBottom: "1rem", display: "flex", gap: "0.5rem", alignItems: "center" }}>
        <button type="button" className="button" onClick={handleClearData} disabled={clearing}>
          {clearing ? "Clearing…" : "Clear all report data"}
        </button>
      </div>
      {error && <div className="card">Error: {error}</div>}
      <table className="table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Type</th>
            <th>Run</th>
            <th>Message</th>
          </tr>
        </thead>
        <tbody>
          {events.map((event) => (
            <tr key={`${event.run_id}-${event.created_at}`}>
              <td>{event.created_at}</td>
              <td>{event.event_type}</td>
              <td>{event.run_id}</td>
              <td>{event.message || "-"}</td>
            </tr>
          ))}
          {events.length === 0 && (
            <tr>
              <td colSpan={4}>No events found.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
