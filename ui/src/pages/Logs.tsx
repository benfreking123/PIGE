import { useEffect, useState } from "react";
import { api } from "../services/api";
import { LogEvent } from "../types";

export default function Logs() {
  const [events, setEvents] = useState<LogEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const load = () => {
    api.getLogs().then(setEvents).catch((err) => setError(String(err)));
  };

  useEffect(() => {
    load();
  }, []);

  const clearData = async () => {
    setStatus(null);
    setError(null);
    const confirm = window.confirm(
      "This will delete all report runs, versions, events, and alert data. Continue?"
    );
    if (!confirm) return;
    try {
      await api.clearData();
      setStatus("Data cleared.");
      load();
    } catch (err) {
      setError(String(err));
    }
  };

  return (
    <div>
      <h1>Logs</h1>
      {error && <div className="card">Error: {error}</div>}
      {status && <div className="card">{status}</div>}
      <div className="card">
        <button className="button" onClick={clearData}>
          Clear Database Data
        </button>
      </div>
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
