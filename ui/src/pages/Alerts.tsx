import { useEffect, useState } from "react";
import { api } from "../services/api";
import { AlertState } from "../types";

export default function Alerts() {
  const [alerts, setAlerts] = useState<AlertState[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getAlerts().then(setAlerts).catch((err) => setError(String(err)));
  }, []);

  return (
    <div>
      <h1>Alerts</h1>
      {error && <div className="card">Error: {error}</div>}
      <table className="table">
        <thead>
          <tr>
            <th>Report</th>
            <th>Consecutive Failures</th>
            <th>Last Failure</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((alert) => (
            <tr key={alert.report_id}>
              <td>{alert.report_id}</td>
              <td>{alert.consecutive_failures}</td>
              <td>{alert.last_failure_at || "-"}</td>
              <td>{alert.updated_at}</td>
            </tr>
          ))}
          {alerts.length === 0 && (
            <tr>
              <td colSpan={4}>No alerts.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
