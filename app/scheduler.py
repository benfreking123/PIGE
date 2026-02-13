from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Optional
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.registry import ReportConfig, get_reports
from app.db.session import SessionLocal
from app.services.marketdata.service import MarketDataService
from app.workers.registry import get_worker


logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()
        self.state: Dict[str, Dict[str, object]] = {}
        self.semaphore = asyncio.Semaphore(settings.max_concurrency)
        self.tz = ZoneInfo(settings.app_timezone)
        self.marketdata = (
            MarketDataService()
            if settings.databento_apikey or settings.api_ninja_apikey
            else None
        )

    def start(self) -> None:
        self.scheduler.add_job(self.tick, "interval", seconds=settings.poll_tick_seconds)
        self.scheduler.add_job(
            self.run_market_daily_update,
            "cron",
            hour=15,
            minute=0,
            timezone=self.tz,
        )
        self.scheduler.add_job(
            self.poll_market_jobs,
            "interval",
            seconds=settings.market_job_poll_seconds,
            timezone=self.tz,
        )
        self.scheduler.add_job(
            self.refresh_market_quotes,
            "interval",
            seconds=settings.market_quote_refresh_seconds,
            timezone=self.tz,
        )
        self.scheduler.start()

    def shutdown(self) -> None:
        self.scheduler.shutdown(wait=False)

    def _next_due(self, report: ReportConfig, now: datetime, error_count: int) -> datetime:
        polling = report.polling
        in_window = self._is_within_window(report, now)
        base = polling.inside_cadence_sec if in_window else polling.outside_cadence_sec
        if error_count > 0:
            exponential = polling.error_backoff_base_sec * (2 ** (error_count - 1))
            base = min(polling.error_backoff_max_sec, max(base, exponential))
        jitter = random.randint(0, polling.jitter_sec)
        return now + timedelta(seconds=base + jitter)

    def _is_within_window(self, report: ReportConfig, now: datetime) -> bool:
        local = now.astimezone(self.tz)
        for window in report.windows:
            start = local.replace(hour=window.start.hour, minute=window.start.minute, second=0, microsecond=0)
            end = local.replace(hour=window.end.hour, minute=window.end.minute, second=0, microsecond=0)
            if start <= local <= end:
                return True
        return False

    async def tick(self) -> None:
        now = datetime.now(tz=self.tz)
        for report in get_reports():
            report_state = self.state.setdefault(report.report_id, {"next_due": now, "error_count": 0})
            next_due: datetime = report_state["next_due"]  # type: ignore[assignment]
            if now < next_due:
                continue
            report_state["next_due"] = self._next_due(report, now, report_state["error_count"])  # type: ignore[index]
            asyncio.create_task(self._run_report(report))

    async def _run_report(self, report: ReportConfig) -> None:
        async with self.semaphore:
            worker = get_worker(report.report_id)
            if not worker:
                return
            success = await worker.run()
            if success:
                self.state[report.report_id]["error_count"] = 0  # type: ignore[index]
            else:
                logger.error("worker error", extra={"report_id": report.report_id})
                self.state[report.report_id]["error_count"] = self.state[report.report_id]["error_count"] + 1  # type: ignore[index]

    async def run_market_daily_update(self) -> None:
        if not self.marketdata:
            return
        with SessionLocal() as db:
            self.marketdata.run_daily_update(db)

    async def poll_market_jobs(self) -> None:
        if not self.marketdata:
            return
        with SessionLocal() as db:
            self.marketdata.poll_jobs(db)

    async def refresh_market_quotes(self) -> None:
        if not self.marketdata or not settings.api_ninja_apikey:
            return
        now = datetime.now(tz=self.tz)
        start = now.replace(hour=8, minute=20, second=0, microsecond=0)
        end = now.replace(hour=13, minute=30, second=0, microsecond=0)
        if not (start <= now <= end):
            return
        with SessionLocal() as db:
            self.marketdata.refresh_quotes(db)
