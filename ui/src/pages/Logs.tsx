import { useEffect, useState } from "react";
import { api } from "../services/api";
import { LogEvent } from "../types";

export default function Logs() {
  const [events, setEvents] = useState<LogEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getLogs().then(setEvents).catch((err) => setError(String(err)));
  }, []);

  return (
    <div>
      <h1>Logs</h1>
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
