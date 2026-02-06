import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../services/api";
import { HistoricalRow } from "../types";

export default function Historicals() {
  const { id } = useParams();
  const [rows, setRows] = useState<HistoricalRow[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api
      .getHistoricals(id)
      .then((data) => {
        setRows(data);
        const keys = new Set<string>();
        data.forEach((row) => Object.keys(row.parsed_fields || {}).forEach((k) => keys.add(k)));
        const list = Array.from(keys);
        setColumns(list);
        setSelectedColumns(list.slice(0, 8));
      })
      .catch((err) => setError(String(err)));
  }, [id]);

  const displayedRows = useMemo(() => rows, [rows]);

  const toggleColumn = (col: string) => {
    setSelectedColumns((prev) =>
      prev.includes(col) ? prev.filter((c) => c !== col) : [...prev, col]
    );
  };

  const gather = async () => {
    if (!id || !startDate || !endDate) {
      setError("Please provide start and end dates.");
      return;
    }
    setStatus(null);
    setError(null);
    try {
      const res = await api.gatherHistoricals(id, startDate, endDate);
      setStatus(`Gather complete: ${res.inserted} inserted, ${res.skipped} skipped.`);
      const data = await api.getHistoricals(id, startDate, endDate);
      setRows(data);
    } catch (err) {
      setError(String(err));
    }
  };

  if (!id) {
    return <div className="card">Missing report id.</div>;
  }

  return (
    <div>
      <h1>Historicals</h1>
      {error && <div className="card">Error: {error}</div>}
      {status && <div className="card">{status}</div>}
      <div className="card">
        <h3>Gather</h3>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          <button className="button" onClick={gather}>
            Gather
          </button>
        </div>
      </div>
      <div className="card">
        <h3>Columns</h3>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
          {columns.map((col) => (
            <label key={col} style={{ display: "flex", gap: "4px", alignItems: "center" }}>
              <input
                type="checkbox"
                checked={selectedColumns.includes(col)}
                onChange={() => toggleColumn(col)}
              />
              {col}
            </label>
          ))}
        </div>
      </div>
      <div className="card">
        <h3>Historical Data</h3>
        <table className="table">
          <thead>
            <tr>
              <th>Report Date</th>
              {selectedColumns.map((col) => (
                <th key={col}>{col}</th>
              ))}
              <th>Created At</th>
            </tr>
          </thead>
          <tbody>
            {displayedRows.map((row) => (
              <tr key={`${row.report_date}-${row.payload_hash}`}>
                <td>{row.report_date}</td>
                {selectedColumns.map((col) => (
                  <td key={col}>{String(row.parsed_fields?.[col] ?? "")}</td>
                ))}
                <td>{row.created_at}</td>
              </tr>
            ))}
            {displayedRows.length === 0 && (
              <tr>
                <td colSpan={selectedColumns.length + 2}>No data.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
