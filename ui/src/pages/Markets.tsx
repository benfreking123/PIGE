import { useEffect, useState } from "react";
import { api } from "../services/api";
import { MarketQuote } from "../types";

export default function Markets() {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [quotes, setQuotes] = useState<MarketQuote[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<number | null>(null);
  const monthOrder: Record<string, number> = {
    F: 1,
    G: 2,
    H: 3,
    J: 4,
    K: 5,
    M: 6,
    N: 7,
    Q: 8,
    U: 9,
    V: 10,
    X: 11,
    Z: 12,
  };

  const parseSymbol = (symbol?: string | null) => {
    if (!symbol || symbol.length < 4) {
      return null;
    }
    const month = symbol[symbol.length - 3];
    const yearStr = symbol.slice(symbol.length - 2);
    const year = Number.parseInt(yearStr, 10);
    if (!Number.isFinite(year)) {
      return null;
    }
    return { year, monthOrder: monthOrder[month] ?? 99 };
  };

  const formatTimestamp = (label: string, timestampMs?: number | null) => {
    if (!timestampMs) {
      return `${label}: -`;
    }
    const date = new Date(timestampMs);
    const formatted = new Intl.DateTimeFormat("en-US", {
      timeZone: "America/Chicago",
      month: "2-digit",
      day: "2-digit",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    }).format(date);
    return `${label}: ${formatted}`;
  };

  const load = async () => {
    setError(null);
    setStatus(null);
    setLoading(true);
    try {
      const data = await api.getMarketQuoteSymbols();
      setSymbols(data.symbols);
      const quoteData = await api.getMarketQuotes(data.symbols);
      setQuotes(quoteData);
      setLastRefreshedAt(Date.now());
      if (!quoteData.length) {
        setStatus("No cached quotes yet. Click Refresh Quotes.");
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const displayQuotes = quotes
    .filter((quote) => !(quote.price == null && !quote.last_update))
    .slice()
    .sort((a, b) => {
      const left = parseSymbol(a.symbol);
      const right = parseSymbol(b.symbol);
      if (!left && !right) return 0;
      if (!left) return 1;
      if (!right) return -1;
      if (left.year !== right.year) return left.year - right.year;
      return left.monthOrder - right.monthOrder;
    });

  const lastUpdatedSeconds = displayQuotes.reduce<number | null>((latest, quote) => {
    const raw = quote.last_update;
    const parsed =
      typeof raw === "number"
        ? raw
        : typeof raw === "string"
        ? Number.parseInt(raw, 10)
        : NaN;
    if (!Number.isFinite(parsed)) {
      return latest;
    }
    if (latest == null || parsed > latest) {
      return parsed;
    }
    return latest;
  }, null);
  const lastUpdatedMs = lastUpdatedSeconds ? lastUpdatedSeconds * 1000 : null;

  const refreshQuotes = async () => {
    setError(null);
    setStatus(null);
    setLoading(true);
    try {
      const result = await api.refreshMarketQuotes(symbols);
      const quoteData = await api.getMarketQuotes(symbols);
      setQuotes(quoteData);
      setLastRefreshedAt(Date.now());
      if (!quoteData.length) {
        const failedList =
          result.failed && result.failed.length
            ? ` Failed symbols (first 5): ${result.failed.slice(0, 5).join(", ")}`
            : "";
        setStatus(`Refresh ran but returned no quotes.${failedList} Check API Ninja key/limits.`);
      } else {
        const failed = result.failed && result.failed.length ? ` (failed: ${result.failed.length})` : "";
        setStatus(`Quotes updated: ${result.updated}${failed}`);
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1>Markets</h1>
      {error && <div className="card">Error: {error}</div>}
      {status && <div className="card">{status}</div>}
      <div style={{ marginBottom: "1rem", display: "flex", gap: "0.5rem", alignItems: "center" }}>
        <button className="button" onClick={refreshQuotes} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh Quotes"}
        </button>
        <div>Total symbols: {symbols.length}</div>
      </div>
      <div style={{ marginBottom: "0.75rem", display: "flex", gap: "1rem", flexWrap: "wrap" }}>
        <div>{formatTimestamp("Last Refreshed", lastRefreshedAt)}</div>
        <div>{formatTimestamp("Last Update (API)", lastUpdatedMs)}</div>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Last Price</th>
          </tr>
        </thead>
        <tbody>
          {displayQuotes.map((quote, idx) => (
            <tr key={`${quote.symbol || "unknown"}-${idx}`}>
              <td>{quote.symbol || "-"}</td>
              <td>{quote.price ?? "-"}</td>
            </tr>
          ))}
          {displayQuotes.length === 0 && (
            <tr>
              <td colSpan={2}>No quotes available.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
