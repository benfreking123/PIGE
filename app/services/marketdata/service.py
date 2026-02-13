from __future__ import annotations

import pathlib
import tempfile
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import MarketBatchJob, MarketOhlcv1d, MarketQuote
from app.services.marketdata.api_ninja import ApiNinjaClient
from app.services.marketdata.databento_client import DatabentoClient, df_from_dbn_files
from app.services.marketdata.store import df_to_ohlcv_rows, upsert_ohlcv_rows, upsert_quotes
from app.services.marketdata.symbols import (
    add_months,
    filter_future_symbols,
    generate_he_symbols,
    generate_he_symbols_future,
)


class MarketDataService:
    def __init__(self) -> None:
        self.databento = DatabentoClient(settings.databento_apikey) if settings.databento_apikey else None
        self.api_ninja = ApiNinjaClient(settings.api_ninja_apikey) if settings.api_ninja_apikey else None
        self.tz = ZoneInfo(settings.app_timezone)

    def symbol_range_history(self) -> List[str]:
        today = datetime.now(tz=self.tz).date()
        start = date(today.year - 3, 1, 1)
        end = add_months(today, 18)
        return generate_he_symbols(start, end)

    def symbol_range_quotes(self) -> List[str]:
        today = datetime.now(tz=self.tz).date()
        try:
            symbols = self._require_api_ninja().contract_symbols()
            he_symbols = [symbol for symbol in symbols if symbol.startswith("HE")]
            filtered = filter_future_symbols(he_symbols, today)
            if filtered:
                return filtered
        except Exception:
            pass
        end = add_months(today, 18)
        return generate_he_symbols_future(today, end)

    def estimate_backfill_cost(self, start: date, end: date) -> float:
        client = self._require_databento()
        return client.estimate_cost(self.symbol_range_history(), start, end)

    def submit_backfill_job(self, db: Session, start: date, end: date) -> MarketBatchJob:
        symbols = self.symbol_range_history()
        job_id = self._require_databento().submit_batch_job(symbols, start, end)
        job = MarketBatchJob(
            job_id=job_id,
            symbols=symbols,
            start_date=start,
            end_date=end,
            status="submitted",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(job)
        db.commit()
        return job

    def submit_test_batch_job(self, db: Session, start: date, end: date) -> MarketBatchJob:
        symbols = self.symbol_range_history()[:2]
        job_id = self._require_databento().submit_batch_job(symbols, start, end)
        job = MarketBatchJob(
            job_id=job_id,
            symbols=symbols,
            start_date=start,
            end_date=end,
            status="submitted",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(job)
        db.commit()
        return job

    def poll_jobs(self, db: Session) -> int:
        pending = db.query(MarketBatchJob).filter(MarketBatchJob.status == "submitted").all()
        if not pending:
            return 0
        client = self._require_databento()
        done_ids = set(client.list_jobs("done"))
        updated = 0
        for job in pending:
            if job.job_id not in done_ids:
                continue
            try:
                rows_inserted = self._download_and_ingest(job)
                job.status = "done"
                job.updated_at = datetime.utcnow()
                job.last_error = None
                db.add(job)
                db.commit()
                updated += rows_inserted
            except Exception as exc:
                job.status = "failed"
                job.last_error = str(exc)
                job.updated_at = datetime.utcnow()
                db.add(job)
                db.commit()
        return updated

    def run_daily_update(self, db: Session) -> int:
        today = datetime.now(tz=self.tz).date()
        symbols = self.symbol_range_history()
        existing = (
            db.query(MarketOhlcv1d)
            .filter(MarketOhlcv1d.trade_date == today)
            .with_entities(MarketOhlcv1d.symbol)
            .all()
        )
        existing_symbols = {row[0] for row in existing}
        missing = [symbol for symbol in symbols if symbol not in existing_symbols]
        if not missing:
            return 0
        end = today + timedelta(days=1)
        df = self._require_databento().get_range(missing, today, end)
        rows = df_to_ohlcv_rows(df)
        return upsert_ohlcv_rows(db, rows)

    def market_contracts(self) -> List[Dict[str, object]]:
        return self._require_api_ninja().contract_list()

    def market_quotes(self, symbols: List[str]) -> List[Dict[str, object]]:
        quotes = []
        for symbol in symbols:
            try:
                data = self._require_api_ninja().contract_quote(symbol)
                if isinstance(data, list) and data:
                    quotes.append(data[0])
                elif isinstance(data, dict):
                    quotes.append(data)
            except Exception:
                continue
        return quotes

    def refresh_quotes(self, db: Session, symbols: Optional[List[str]] = None) -> Tuple[int, List[str]]:
        symbols = symbols or self.symbol_range_quotes()
        quotes = []
        failed: List[str] = []
        for symbol in symbols:
            try:
                data = self._require_api_ninja().contract_quote(symbol)
                if isinstance(data, list) and data:
                    quotes.append(data[0])
                elif isinstance(data, dict):
                    quotes.append(data)
                else:
                    failed.append(symbol)
            except Exception:
                failed.append(symbol)
        rows: List[dict] = []
        now = datetime.utcnow()
        for quote in quotes:
            symbol, price, last_update = _extract_quote_fields(quote)
            if not symbol:
                continue
            rows.append(
                {
                    "symbol": symbol,
                    "price": price,
                    "last_update": last_update,
                    "raw_payload": quote,
                    "updated_at": now,
                }
            )
        updated = upsert_quotes(db, rows)
        return updated, failed

    def cached_quotes(self, db: Session, symbols: Optional[List[str]] = None) -> List[Dict[str, object]]:
        query = db.query(MarketQuote)
        if symbols:
            query = query.filter(MarketQuote.symbol.in_(symbols))
        rows = query.order_by(MarketQuote.symbol.asc()).all()
        return [
            {
                "symbol": row.symbol,
                "price": row.price,
                "last_update": row.last_update,
                "updated_at": row.updated_at.isoformat(),
            }
            for row in rows
        ]

    def get_history(self, db: Session, symbol: str, start: Optional[date], end: Optional[date]) -> List[Dict[str, object]]:
        query = db.query(MarketOhlcv1d).filter(MarketOhlcv1d.symbol == symbol)
        if start:
            query = query.filter(MarketOhlcv1d.trade_date >= start)
        if end:
            query = query.filter(MarketOhlcv1d.trade_date <= end)
        rows = query.order_by(MarketOhlcv1d.trade_date.asc()).all()
        return [
            {
                "date": row.trade_date.isoformat(),
                "open": row.open,
                "high": row.high,
                "low": row.low,
                "close": row.close,
                "volume": row.volume,
                "open_interest": row.open_interest,
            }
            for row in rows
        ]

    def _download_and_ingest(self, job: MarketBatchJob) -> int:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = pathlib.Path(tmp_dir)
            files = self._require_databento().download_job(job.job_id, output_dir)
            df = df_from_dbn_files(files)
            rows = df_to_ohlcv_rows(df)
            return self._write_rows(rows)

    def _write_rows(self, rows: List[dict]) -> int:
        from app.db.session import SessionLocal

        with SessionLocal() as db:
            count = upsert_ohlcv_rows(db, rows)
            db.commit()
            return count

    def _require_databento(self) -> DatabentoClient:
        if not self.databento:
            raise ValueError("DATABENTO_APIKEY is required")
        return self.databento

    def _require_api_ninja(self) -> ApiNinjaClient:
        if not self.api_ninja:
            raise ValueError("API_NINJA_APIKEY is required")
        return self.api_ninja


def _extract_quote_fields(quote: Dict[str, object]) -> Tuple[Optional[str], Optional[float], Optional[str]]:
    symbol = quote.get("symbol") or quote.get("ticker")
    price = _to_float(
        quote.get("price")
        or quote.get("last_price")
        or quote.get("last")
        or quote.get("value")
    )
    last_update = (
        quote.get("last_update")
        or quote.get("last_updated")
        or quote.get("timestamp")
        or quote.get("time")
        or quote.get("updated")
    )
    last_update_str = str(last_update) if last_update is not None else None
    return (str(symbol) if symbol else None, price, last_update_str)


def _to_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None
