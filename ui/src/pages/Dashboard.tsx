import { useEffect, useMemo, useState } from "react";
import { api } from "../services/api";
import { Health, ReportSummary } from "../types";

export default function Dashboard() {
  const [health, setHealth] = useState<Health | null>(null);
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.getHealth(), api.getReports()])
      .then(([h, r]) => {
        setHealth(h);
        setReports(r);
      })
      .catch((err) => setError(String(err)));
  }, []);

  const counts = useMemo(() => {
    const result: Record<string, number> = {};
    for (const report of reports) {
      const state = report.latest_run?.state || "unknown";
      result[state] = (result[state] || 0) + 1;
    }
    return result;
  }, [reports]);

  const today = new Date().toISOString().slice(0, 10);
  const statusForToday = (report: ReportSummary) => {
    if (report.latest_run?.report_date === today) {
      return report.latest_run.state;
    }
    return "not_run_today";
  };

  return (
    <div>
      <h1>Dashboard</h1>
      {error && <div className="card">Error: {error}</div>}
      <div className="grid">
        <div className="card">
          <div>Health</div>
          <div>Status: {health?.status || "unknown"}</div>
          <div>DB: {health?.db_ok ? "ok" : "down"}</div>
          <div>DB Ping: {health?.db_ping_ms ? `${health.db_ping_ms.toFixed(1)} ms` : "n/a"}</div>
          <div>Scheduler: {health?.scheduler_running ? "running" : "stopped"}</div>
          <div>
            Uptime:{" "}
            {health?.uptime_seconds ? `${Math.floor(health.uptime_seconds / 60)} min` : "n/a"}
          </div>
        </div>
        <div className="card">
          <div>Report States</div>
          {Object.keys(counts).length === 0 && <div>No data yet.</div>}
          {Object.entries(counts).map(([key, value]) => (
            <div key={key}>
              {key}: {value}
            </div>
          ))}
        </div>
      </div>
      <div className="card">
        <h3>Today Status</h3>
        <table className="table">
          <thead>
            <tr>
              <th>Report</th>
              <th>Today Status</th>
              <th>Last Run</th>
              <th>Report Date</th>
            </tr>
          </thead>
          <tbody>
            {reports.map((report) => (
              <tr key={report.report_id}>
                <td>{report.name}</td>
                <td>
                  <span className="pill">{statusForToday(report)}</span>
                </td>
                <td>{report.latest_run?.run_started_at || "-"}</td>
                <td>{report.latest_run?.report_date || "-"}</td>
              </tr>
            ))}
            {reports.length === 0 && (
              <tr>
                <td colSpan={4}>No reports found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
