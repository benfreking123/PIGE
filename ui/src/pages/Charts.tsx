import { useEffect, useMemo, useState } from "react";
import ReactECharts from "echarts-for-react";
import { api } from "../services/api";
import { MarketHistoryMeta, MarketHistoryRow } from "../types";

type Job = {
  job_id: string;
  status: string;
  start_date: string;
  end_date: string;
  updated_at: string;
  last_error?: string | null;
};

export default function Charts() {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [history, setHistory] = useState<MarketHistoryRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [chartRange, setChartRange] = useState<MarketHistoryMeta | null>(null);
  const [cost, setCost] = useState<number | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);

  useEffect(() => {
    api
      .getMarketContracts()
      .then((data) => {
        setSymbols(data.symbols);
        setSelected(data.symbols[0] || "");
      })
      .catch((err) => setError(String(err)));
  }, []);

  useEffect(() => {
    if (!selected) return;
    api
      .getMarketHistoryMeta(selected)
      .then((meta) => {
        setChartRange(meta);
        return api.getMarketHistory(selected, meta.min_date, meta.max_date);
      })
      .then(setHistory)
      .catch((err) => setError(String(err)));
  }, [selected]);

  useEffect(() => {
    api.getBackfillJobs().then(setJobs).catch(() => null);
  }, []);

  const loadCost = async () => {
    if (!startDate || !endDate) {
      setError("Provide start and end dates to estimate cost.");
      return;
    }
    setError(null);
    const res = await api.getBackfillCost(startDate, endDate);
    setCost(res.estimated_cost);
  };

  const runBackfill = async () => {
    if (!startDate || !endDate) {
      setError("Provide start and end dates before running backfill.");
      return;
    }
    setError(null);
    await api.runBackfill(startDate, endDate);
    const latest = await api.getBackfillJobs();
    setJobs(latest);
  };

  const runTestBackfill = async () => {
    if (!startDate || !endDate) {
      setError("Provide start and end dates before running test.");
      return;
    }
    setError(null);
    await api.runTestBackfill(startDate, endDate);
    const latest = await api.getBackfillJobs();
    setJobs(latest);
  };

  const chartOption = useMemo(() => {
    const categories = history.map((row) => row.date);
    const ohlc = history.map((row) => [row.open, row.close, row.low, row.high]);
    const volume = history.map((row) => row.volume || 0);
    const oi = history.map((row) => row.open_interest || 0);

    return {
      tooltip: { trigger: "axis" },
      legend: { data: ["OHLC", "Volume", "Open Interest"] },
      grid: [
        { left: "8%", right: "4%", height: "55%" },
        { left: "8%", right: "4%", top: "68%", height: "20%" },
      ],
      xAxis: [
        { type: "category", data: categories, scale: true, boundaryGap: false },
        { type: "category", gridIndex: 1, data: categories, scale: true, boundaryGap: false },
      ],
      yAxis: [{ scale: true }, { gridIndex: 1, scale: true }],
      series: [
        { type: "candlestick", name: "OHLC", data: ohlc },
        { type: "bar", name: "Volume", xAxisIndex: 1, yAxisIndex: 1, data: volume },
        { type: "line", name: "Open Interest", data: oi, smooth: true },
      ],
    };
  }, [history]);

  const groupedSymbols = useMemo(() => {
    const groups: Record<string, string[]> = {};
    symbols.forEach((symbol) => {
      const year = `20${symbol.slice(-2)}`;
      groups[year] = groups[year] || [];
      groups[year].push(symbol);
    });
    return groups;
  }, [symbols]);

  return (
    <div>
      <h1>Charts</h1>
      {error && <div className="card">Error: {error}</div>}
      <div className="card">
        <label>
          Contract
          <select value={selected} onChange={(e) => setSelected(e.target.value)} style={{ marginLeft: "8px" }}>
            {Object.entries(groupedSymbols).map(([year, list]) => (
              <optgroup key={year} label={year}>
                {list.map((symbol) => (
                  <option key={symbol} value={symbol}>
                    {symbol}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </label>
        {chartRange && (
          <div style={{ marginTop: "8px" }}>
            Range: {chartRange.min_date} → {chartRange.max_date}
          </div>
        )}
      </div>
      <div className="card">
        <ReactECharts option={chartOption} style={{ height: 420 }} />
      </div>
      <div className="card">
        <h3>Backfill (manual)</h3>
        <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
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
          <button className="button" onClick={loadCost}>
            Estimate Cost
          </button>
          <button className="button" onClick={runBackfill}>
            Run Backfill
          </button>
          <button className="button secondary" onClick={runTestBackfill}>
            Test Batch (2 symbols)
          </button>
          {cost !== null && <div>Estimated cost: ${cost.toFixed(2)}</div>}
        </div>
      </div>
      <div className="card">
        <h3>Backfill Jobs</h3>
        <table className="table">
          <thead>
            <tr>
              <th>Job</th>
              <th>Status</th>
              <th>Start</th>
              <th>End</th>
              <th>Updated</th>
              <th>Error</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.job_id}>
                <td>{job.job_id}</td>
                <td>{job.status}</td>
                <td>{job.start_date}</td>
                <td>{job.end_date}</td>
                <td>{job.updated_at}</td>
                <td>{job.last_error || "-"}</td>
              </tr>
            ))}
            {jobs.length === 0 && (
              <tr>
                <td colSpan={6}>No jobs yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
