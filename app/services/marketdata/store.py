from __future__ import annotations

from datetime import date
from typing import Iterable, List

import pandas as pd
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import MarketOhlcv1d, MarketQuote


def upsert_ohlcv_rows(db: Session, rows: List[dict]) -> int:
    if not rows:
        return 0
    stmt = insert(MarketOhlcv1d).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol", "trade_date"],
        set_={
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
            "volume": stmt.excluded.volume,
            "open_interest": stmt.excluded.open_interest,
        },
    )
    result = db.execute(stmt)
    return result.rowcount or 0


def df_to_ohlcv_rows(df: pd.DataFrame) -> List[dict]:
    if df.empty:
        return []

    def col(name: str) -> str | None:
        for candidate in [name, name.upper(), name.lower()]:
            if candidate in df.columns:
                return candidate
        return None

    ts_col = col("ts_event") or col("ts_recv") or col("ts_end") or col("ts")
    symbol_col = col("symbol") or col("raw_symbol")
    if not ts_col or not symbol_col:
        return []

    rows: List[dict] = []
    for _, row in df.iterrows():
        ts_val = row[ts_col]
        if pd.isna(ts_val):
            continue
        trade_date: date = pd.to_datetime(ts_val).date()
        rows.append(
            {
                "symbol": str(row[symbol_col]),
                "trade_date": trade_date,
                "open": _to_float(row.get(col("open"))),
                "high": _to_float(row.get(col("high"))),
                "low": _to_float(row.get(col("low"))),
                "close": _to_float(row.get(col("close"))),
                "volume": _to_float(row.get(col("volume"))),
                "open_interest": _to_float(row.get(col("open_interest"))),
            }
        )
    return rows


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def upsert_quotes(db: Session, quotes: List[dict]) -> int:
    if not quotes:
        return 0
    stmt = insert(MarketQuote).values(quotes)
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol"],
        set_={
            "price": stmt.excluded.price,
            "last_update": stmt.excluded.last_update,
            "raw_payload": stmt.excluded.raw_payload,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    result = db.execute(stmt)
    return result.rowcount or 0
