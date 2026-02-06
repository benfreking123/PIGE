import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../services/api";
import { ReportConfig } from "../types";

export default function ReportSettings() {
  const { id } = useParams();
  const [config, setConfig] = useState<ReportConfig | null>(null);
  const [text, setText] = useState<string>("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api
      .getReportConfig(id)
      .then((data) => {
        setConfig(data);
        setText(JSON.stringify(data, null, 2));
      })
      .catch((err) => setError(String(err)));
  }, [id]);

  const save = async () => {
    if (!id) return;
    setStatus(null);
    setError(null);
    try {
      const parsed = JSON.parse(text);
      await api.updateReportConfig(id, parsed);
      setConfig(parsed);
      setStatus("Saved.");
    } catch (err) {
      setError(String(err));
    }
  };

  if (!id) {
    return <div className="card">Missing report id.</div>;
  }

  return (
    <div>
      <h1>Report Settings</h1>
      {error && <div className="card">Error: {error}</div>}
      {status && <div className="card">{status}</div>}
      <div className="card">
        <p>Editing raw config JSON for {id}.</p>
        <textarea
          style={{ width: "100%", minHeight: "420px", fontFamily: "monospace" }}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div style={{ marginTop: "12px" }}>
          <button className="button" onClick={save}>
            Save Settings
          </button>
        </div>
      </div>
      {config && (
        <div className="card">
          <h3>Current Settings Snapshot</h3>
          <pre>{JSON.stringify(config, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
