from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import ReportRun, ReportRunEvent, ReportVersion
from app.db.session import SessionLocal
from app.registry import ReportConfig
from app.services.alerts import AlertService
from app.services.email import EmailService
from app.services.http import get_client


logger = logging.getLogger(__name__)


class FetchError(Exception):
    pass


class ParseError(Exception):
    pass


@dataclass
class FetchResult:
    payloads: List[List[Dict[str, Any]]]
    urls: List[str]


class BaseWorker:
    def __init__(self, config: ReportConfig, email_service: EmailService, alert_service: AlertService) -> None:
        self.config = config
        self.email_service = email_service
        self.alert_service = alert_service
        self.tz = ZoneInfo(settings.app_timezone)
        self.forced_report_date: Optional[date] = None

    async def run(self) -> bool:
        async with get_client() as client:
            with SessionLocal() as db:
                if not self._acquire_lock(db):
                    return True
                run = ReportRun(report_id=self.config.report_id, state="waiting_for_publication")
                db.add(run)
                db.commit()

                try:
                    report_date, fetch_result, is_holiday = await self._fetch_for_date_window(client)
                    if not fetch_result:
                        state = "holiday_or_no_report" if is_holiday else "waiting_for_publication"
                        self._finalize_run(db, run, report_date, state)
                        return True

                    parsed_fields = self._parse(fetch_result.payloads, report_date)
                    payload_hash = self._compute_hash(fetch_result.payloads)
                    run.payload_hash = payload_hash
                    run.report_date = report_date

                    existing = (
                        db.query(ReportVersion)
                        .filter(
                            ReportVersion.report_id == self.config.report_id,
                            ReportVersion.report_date == report_date,
                        )
                        .all()
                    )
                    if any(v.payload_hash == payload_hash for v in existing):
                        self._finalize_run(db, run, report_date, "published_no_change")
                        self.alert_service.clear_failure(db, self.config.report_id)
                        return True

                    version = ReportVersion(
                        report_id=self.config.report_id,
                        report_date=report_date,
                        payload_hash=payload_hash,
                        parsed_fields=parsed_fields,
                        raw_payload={"payloads": fetch_result.payloads, "urls": fetch_result.urls},
                    )
                    db.add(version)
                    self._finalize_run(db, run, report_date, "published_new")
                    self.alert_service.clear_failure(db, self.config.report_id)
                    db.commit()

                    self._send_email(parsed_fields, report_date, fetch_result.urls)
                    return True
                except Exception as exc:
                    db.rollback()
                    run.state = "error_parse" if isinstance(exc, ParseError) else "error_fetch"
                    run.error_type = type(exc).__name__
                    run.error_message = str(exc)
                    run.run_finished_at = datetime.utcnow()
                    db.add(ReportRunEvent(report_run_id=run.id, event_type="error", message=str(exc)))
                    db.commit()
                    self.alert_service.record_failure(db, self.config.report_id, run.id, run.error_type or "error")
                    logger.exception(
                        "worker run failed",
                        extra={"report_id": self.config.report_id, "run_id": run.id},
                    )
                    return False
                finally:
                    self._release_lock(db)
        return True

    async def _fetch_for_date_window(self, client) -> tuple[Optional[date], Optional[FetchResult], bool]:
        today = self.forced_report_date or datetime.now(tz=self.tz).date()
        search_days = 1 if self.forced_report_date else self.config.date_search_window_days
        for offset in range(search_days):
            target = today - timedelta(days=offset)
            report_date_str = target.strftime("%m/%d/%Y")
            payloads: List[List[Dict[str, Any]]] = []
            urls: List[str] = []
            for endpoint in self.config.endpoints:
                url = endpoint.build_url(report_date_str)
                urls.append(url)
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    data = resp.json()
                    if isinstance(data, list):
                        payloads.append(data)
                    elif isinstance(data, dict) and isinstance(data.get("results"), list):
                        payloads.append(data["results"])
                    else:
                        payloads.append([])
                except Exception as exc:
                    raise FetchError(str(exc)) from exc
            if any(len(p) > 0 for p in payloads):
                return target, FetchResult(payloads=payloads, urls=urls), False

        if self._should_mark_holiday(today):
            return today, None, True
        return today, None, False

    def _parse(self, payloads: List[List[Dict[str, Any]]], report_date: date) -> Dict[str, Any]:
        row = self._select_row(payloads[0], report_date)
        if not row:
            raise ParseError("No matching row for report date")
        parsed: Dict[str, Any] = {}
        for field in self.config.schema.required_fields:
            parsed[field] = row.get(field)
        parsed["report_date"] = report_date.isoformat()
        return parsed

    def _select_row(self, rows: List[Dict[str, Any]], report_date: date) -> Optional[Dict[str, Any]]:
        rule = self.config.schema.select_rule
        if rule.get("type") == "row_index":
            idx = int(rule.get("index", 0))
            return rows[idx] if 0 <= idx < len(rows) else None
        if rule.get("type") == "date_match":
            target = report_date.strftime("%m/%d/%Y")
            for row in rows:
                for key in ["report_date", "report date", "reportdate", "Report Date"]:
                    val = row.get(key)
                    if val and str(val).strip() == target:
                        return row
        if rule.get("type") == "field_equals":
            field = rule.get("field")
            value = rule.get("value")
            for row in rows:
                if field in row and str(row.get(field)) == str(value):
                    return row
        return rows[0] if rows else None

    def _compute_hash(self, payloads: List[List[Dict[str, Any]]]) -> str:
        normalized = json.dumps(payloads, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_hash_from_payloads(payloads: List[List[Dict[str, Any]]]) -> str:
        normalized = json.dumps(payloads, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _send_email(self, parsed_fields: Dict[str, Any], report_date: date, urls: List[str]) -> None:
        recipients = self._get_recipients()
        payload = self.email_service.render(
            "report",
            {
                "subject": f"{self.config.name} - {report_date.isoformat()}",
                "report_id": self.config.report_id,
                "report_name": self.config.name,
                "report_date": report_date.isoformat(),
                "fields": parsed_fields,
                "urls": urls,
            },
        )
        self.email_service.send(recipients, payload)

    def _get_recipients(self) -> List[str]:
        with SessionLocal() as db:
            rows = db.execute(
                text(
                    "select r.email from recipients r "
                    "join recipient_reports rr on rr.recipient_id = r.id "
                    "where rr.report_id = :rid and r.is_active = true"
                ),
                {"rid": self.config.report_id},
            ).fetchall()
        return [r[0] for r in rows]

    def _finalize_run(self, db: Session, run: ReportRun, report_date: Optional[date], state: str) -> None:
        run.state = state
        run.report_date = report_date
        run.run_finished_at = datetime.utcnow()
        db.add(ReportRunEvent(report_run_id=run.id, event_type=state, message=state))
        db.commit()

    def _acquire_lock(self, db: Session) -> bool:
        result = db.execute(text("select pg_try_advisory_lock(hashtext(:rid))"), {"rid": self.config.report_id})
        locked = result.scalar()
        return bool(locked)

    def _release_lock(self, db: Session) -> None:
        db.execute(text("select pg_advisory_unlock(hashtext(:rid))"), {"rid": self.config.report_id})
        db.commit()

    def _should_mark_holiday(self, report_date: date) -> bool:
        return report_date.weekday() >= 5
