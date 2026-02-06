import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import { ReportSummary } from "../types";

export default function Reports() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState<string | null>(null);

  const load = () => {
    api.getReports().then(setReports).catch((err) => setError(String(err)));
  };

  useEffect(() => {
    load();
  }, []);

  const runReport = async (id: string) => {
    setRunning(id);
    try {
      await api.runReport(id);
      setTimeout(load, 800);
    } catch (err) {
      setError(String(err));
    } finally {
      setRunning(null);
    }
  };

  return (
    <div>
      <h1>Reports</h1>
      {error && <div className="card">Error: {error}</div>}
      <table className="table">
        <thead>
          <tr>
            <th>Report</th>
            <th>Latest State</th>
            <th>Last Run</th>
            <th>Last Published</th>
            <th>Action</th>
            <th>Settings</th>
            <th>Historicals</th>
          </tr>
        </thead>
        <tbody>
          {reports.map((report) => (
            <tr key={report.report_id}>
              <td>
                <Link to={`/reports/${report.report_id}`}>{report.name}</Link>
              </td>
              <td>
                <span className="pill">{report.latest_run?.state || "unknown"}</span>
              </td>
              <td>{report.latest_run?.run_started_at || "-"}</td>
              <td>{report.latest_version?.created_at || "-"}</td>
              <td>
                <button
                  className="button"
                  onClick={() => runReport(report.report_id)}
                  disabled={running === report.report_id}
                >
                  {running === report.report_id ? "Running..." : "Run"}
                </button>
              </td>
              <td>
                <Link to={`/reports/${report.report_id}/settings`}>Settings</Link>
              </td>
              <td>
                <Link to={`/reports/${report.report_id}/historicals`}>Historicals</Link>
              </td>
            </tr>
          ))}
          {reports.length === 0 && (
            <tr>
              <td colSpan={7}>No reports found.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
