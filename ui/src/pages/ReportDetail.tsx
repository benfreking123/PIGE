import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../services/api";
import { ReportLatest, ReportRun } from "../types";

export default function ReportDetail() {
  const { id } = useParams();
  const [latest, setLatest] = useState<ReportLatest | null>(null);
  const [runs, setRuns] = useState<ReportRun[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api
      .getReportLatest(id)
      .then(setLatest)
      .catch(() => setLatest(null));
    api
      .getReportRuns(id)
      .then(setRuns)
      .catch((err) => setError(String(err)));
  }, [id]);

  if (!id) {
    return <div className="card">Missing report id.</div>;
  }

  return (
    <div>
      <h1>Report Detail</h1>
      {error && <div className="card">Error: {error}</div>}
      <div className="card">
        <h3>Latest Parsed Fields</h3>
        {latest ? (
          <pre>{JSON.stringify(latest.parsed_fields, null, 2)}</pre>
        ) : (
          <div>No parsed fields yet.</div>
        )}
      </div>
      <div className="card">
        <h3>Source URLs</h3>
        {latest?.source_urls?.length ? (
          <ul>
            {latest.source_urls.map((url) => (
              <li key={url}>
                <a href={url} target="_blank" rel="noreferrer">
                  {url}
                </a>
              </li>
            ))}
          </ul>
        ) : (
          <div>No sources.</div>
        )}
      </div>
      <div className="card">
        <h3>Run History</h3>
        <table className="table">
          <thead>
            <tr>
              <th>State</th>
              <th>Report Date</th>
              <th>Started</th>
              <th>Finished</th>
              <th>Error</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id}>
                <td>{run.state}</td>
                <td>{run.report_date || "-"}</td>
                <td>{run.run_started_at}</td>
                <td>{run.run_finished_at || "-"}</td>
                <td>{run.error_message || "-"}</td>
              </tr>
            ))}
            {runs.length === 0 && (
              <tr>
                <td colSpan={5}>No runs yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
