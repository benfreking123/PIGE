from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional
from datetime import date, datetime, timedelta

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.db.models import AlertState, Recipient, RecipientReport, Report, ReportRun, ReportRunEvent, ReportVersion
from app.db.session import SessionLocal
from app.registry import RECIPIENTS, get_reports, report_config_from_dict, set_report_overrides
from app.scheduler import SchedulerService
from app.services.email import EmailService
from app.services.logging import configure_logging
from app.services.gather import fetch_range_payloads, fetch_range_rows, group_rows_by_date
from app.workers.hg201_cme_index import HG201CmeIndexWorker
from app.workers.registry import get_worker, init_workers, reload_workers


app = FastAPI(title=settings.app_name)
_START_TIME = datetime.utcnow()
scheduler = SchedulerService()
cors_kwargs = {
    "allow_origins": settings.cors_origin_list(),
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if settings.cors_origin_regex:
    cors_kwargs["allow_origin_regex"] = settings.cors_origin_regex
app.add_middleware(CORSMiddleware, **cors_kwargs)


@app.on_event("startup")
def startup() -> None:
    configure_logging()
    _seed_registry()
    _load_report_overrides()
    init_workers()
    scheduler.start()


@app.on_event("shutdown")
def shutdown() -> None:
    scheduler.shutdown()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/health")
def api_health() -> dict:
    db_ok = True
    db_ping_ms: Optional[float] = None
    try:
        with SessionLocal() as db:
            start = time.perf_counter()
            db.execute(text("select 1"))
            db_ping_ms = (time.perf_counter() - start) * 1000
    except Exception:
        db_ok = False
    uptime_seconds = (datetime.utcnow() - _START_TIME).total_seconds()
    return {
        "status": "ok",
        "db_ok": db_ok,
        "db_ping_ms": db_ping_ms,
        "scheduler_running": scheduler.scheduler.running,
        "uptime_seconds": uptime_seconds,
    }


@app.get("/api/reports")
def api_reports() -> List[dict]:
    with SessionLocal() as db:
        latest_runs = {}
        latest_versions = {}
        runs = db.query(ReportRun).order_by(ReportRun.run_started_at.desc()).all()
        versions = db.query(ReportVersion).order_by(ReportVersion.created_at.desc()).all()
        for run in runs:
            latest_runs.setdefault(run.report_id, run)
        for version in versions:
            latest_versions.setdefault(version.report_id, version)
    return [
        {
            "report_id": r.report_id,
            "name": r.name,
            "latest_run": _run_to_dict(latest_runs.get(r.report_id)),
            "latest_version": _version_to_dict(latest_versions.get(r.report_id)),
        }
        for r in get_reports()
    ]


@app.get("/api/reports/{report_id}/runs")
def api_report_runs(report_id: str, limit: int = 50) -> List[dict]:
    with SessionLocal() as db:
        runs = (
            db.query(ReportRun)
            .filter(ReportRun.report_id == report_id)
            .order_by(ReportRun.run_started_at.desc())
            .limit(limit)
            .all()
        )
    return [_run_to_dict(run) for run in runs]


@app.get("/api/reports/{report_id}/latest")
def api_report_latest(report_id: str) -> dict:
    with SessionLocal() as db:
        version = (
            db.query(ReportVersion)
            .filter(ReportVersion.report_id == report_id)
            .order_by(ReportVersion.created_at.desc())
            .first()
        )
    if not version:
        raise HTTPException(status_code=404, detail="No version found")
    raw_payload = version.raw_payload or {}
    return {
        "report_id": report_id,
        "report_date": version.report_date.isoformat(),
        "payload_hash": version.payload_hash,
        "parsed_fields": version.parsed_fields,
        "source_urls": raw_payload.get("urls", []),
        "created_at": version.created_at.isoformat(),
    }


@app.get("/api/reports/{report_id}/historicals")
def api_report_historicals(
    report_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 500,
) -> List[dict]:
    with SessionLocal() as db:
        query = db.query(ReportVersion).filter(ReportVersion.report_id == report_id)
        if start_date:
            query = query.filter(ReportVersion.report_date >= _parse_date(start_date))
        if end_date:
            query = query.filter(ReportVersion.report_date <= _parse_date(end_date))
        versions = query.order_by(ReportVersion.report_date.desc()).limit(limit).all()
    return [
        {
            "report_id": v.report_id,
            "report_date": v.report_date.isoformat(),
            "payload_hash": v.payload_hash,
            "parsed_fields": v.parsed_fields,
            "created_at": v.created_at.isoformat(),
        }
        for v in versions
    ]


@app.get("/api/reports/{report_id}/config")
def api_report_config(report_id: str) -> Dict[str, Any]:
    with SessionLocal() as db:
        report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report.config


@app.put("/api/reports/{report_id}/config")
def api_report_config_update(report_id: str, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    try:
        parsed = report_config_from_dict(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if parsed.report_id != report_id:
        raise HTTPException(status_code=400, detail="report_id mismatch")
    with SessionLocal() as db:
        report = db.get(Report, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        report.config = payload
        report.name = parsed.name
        db.commit()
    _load_report_overrides()
    reload_workers()
    return {"status": "updated"}


@app.post("/api/reports/{report_id}/gather")
def api_report_gather(report_id: str, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    start = _parse_date(payload.get("start_date"))
    end = _parse_date(payload.get("end_date"))
    if start > end:
        raise HTTPException(status_code=400, detail="start_date must be <= end_date")
    report = next((r for r in get_reports() if r.report_id == report_id), None)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.endpoints and report.endpoints[0].absolute_url:
        raise HTTPException(status_code=400, detail="Gather is not supported for PDF reports")

    worker = get_worker(report_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    if report_id == "HG201_CME_INDEX":
        rows = fetch_range_rows(report, start, end)
        if not rows:
            return {"status": "ok", "inserted": 0, "skipped": 0}
        grouped = group_rows_by_date(rows)
        payloads_by_date = {day: [rows] for day in grouped.keys()}
    else:
        payloads_by_date = fetch_range_payloads(report, start, end)
    inserted = 0
    skipped = 0
    with SessionLocal() as db:
        for report_date, payloads in payloads_by_date.items():
            if report_id == "HG201_CME_INDEX":
                parsed_fields = _compute_hg201_day(rows, report_date)
                payload_hash = worker.compute_hash_from_payloads([rows])
            else:
                parsed_fields = worker._parse(payloads, report_date)
                payload_hash = worker.compute_hash_from_payloads(payloads)
            existing = (
                db.query(ReportVersion)
                .filter(
                    ReportVersion.report_id == report_id,
                    ReportVersion.report_date == report_date,
                    ReportVersion.payload_hash == payload_hash,
                )
                .first()
            )
            if existing:
                existing.parsed_fields = worker._merge_parsed_fields(
                    existing.parsed_fields or {}, parsed_fields
                )
                db.add(existing)
                skipped += 1
                continue
            version = ReportVersion(
                report_id=report_id,
                report_date=report_date,
                payload_hash=payload_hash,
                parsed_fields=parsed_fields,
                raw_payload={"payloads": payloads},
            )
            db.add(version)
            inserted += 1
        db.commit()
    return {"status": "ok", "inserted": inserted, "skipped": skipped}


@app.post("/api/reports/{report_id}/run")
async def api_run_report(report_id: str) -> dict:
    return await run_report(report_id)


@app.get("/api/alerts")
def api_alerts() -> List[dict]:
    with SessionLocal() as db:
        alerts = db.query(AlertState).all()
    return [
        {
            "report_id": alert.report_id,
            "consecutive_failures": alert.consecutive_failures,
            "last_failure_at": alert.last_failure_at.isoformat() if alert.last_failure_at else None,
            "updated_at": alert.updated_at.isoformat(),
        }
        for alert in alerts
    ]


@app.get("/api/logs")
def api_logs(limit: int = 200) -> List[dict]:
    with SessionLocal() as db:
        events = (
            db.query(ReportRunEvent, ReportRun)
            .join(ReportRun, ReportRun.id == ReportRunEvent.report_run_id)
            .order_by(ReportRunEvent.created_at.desc())
            .limit(limit)
            .all()
        )
    return [
        {
            "run_id": event.report_run_id,
            "report_id": run.report_id,
            "event_type": event.event_type,
            "message": event.message,
            "data": event.data,
            "created_at": event.created_at.isoformat(),
        }
        for event, run in events
    ]


@app.post("/api/logs/test-alert")
def api_logs_test_alert() -> dict:
    """Send a test alert email to the configured master alert address to verify email/SES."""
    try:
        email_service = EmailService()
        if not email_service.enabled:
            raise HTTPException(status_code=400, detail="Email is disabled (EMAIL_ENABLED=false)")
        payload = email_service.render(
            "alert",
            {
                "subject": "USDA Monitor – Test Alert",
                "report_id": "test",
                "run_id": "test",
                "error_type": "test_alert",
                "last_attempt_at": datetime.utcnow().isoformat() + "Z",
            },
        )
        email_service.send([settings.master_alert_email], payload)
        return {"status": "sent", "recipient": settings.master_alert_email}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to send test alert: {type(e).__name__}: {e!s}",
        )


@app.post("/api/logs/clear")
def api_logs_clear() -> dict:
    """Delete all report runs, run events, and report versions (historical data)."""
    with SessionLocal() as db:
        deleted_events = db.query(ReportRunEvent).delete()
        deleted_runs = db.query(ReportRun).delete()
        deleted_versions = db.query(ReportVersion).delete()
        db.commit()
    return {
        "deleted_events": deleted_events,
        "deleted_runs": deleted_runs,
        "deleted_versions": deleted_versions,
    }


@app.get("/reports")
def list_reports() -> List[dict]:
    with SessionLocal() as db:
        versions = db.query(ReportVersion).all()
        latest = {}
        for v in versions:
            latest.setdefault(v.report_id, v)
            if latest[v.report_id].created_at < v.created_at:
                latest[v.report_id] = v
    return [
        {
            "report_id": r.report_id,
            "name": r.name,
            "latest_version": latest.get(r.report_id).created_at.isoformat() if latest.get(r.report_id) else None,
        }
        for r in get_reports()
    ]


@app.get("/reports/{report_id}")
def get_report(report_id: str) -> dict:
    report = next((r for r in get_reports() if r.report_id == report_id), None)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    with SessionLocal() as db:
        latest = (
            db.query(ReportVersion)
            .filter(ReportVersion.report_id == report_id)
            .order_by(ReportVersion.created_at.desc())
            .first()
        )
    return {
        "report_id": report.report_id,
        "name": report.name,
        "latest_version": latest.created_at.isoformat() if latest else None,
        "schema": report.schema.required_fields,
    }


@app.post("/run/{report_id}")
async def run_report(report_id: str) -> dict:
    worker = get_worker(report_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Report not found")
    asyncio.create_task(worker.run())
    return {"status": "started", "report_id": report_id}


def _seed_registry() -> None:
    with SessionLocal() as db:
        for report in get_reports():
            existing = db.get(Report, report.report_id)
            if not existing:
                db.add(Report(id=report.report_id, name=report.name, config=report.to_db_config()))
            else:
                merged = _merge_missing(existing.config or {}, report.to_db_config())
                merged = _upgrade_report_config(report.report_id, merged, report.to_db_config())
                if merged != existing.config:
                    existing.config = merged
                    existing.name = report.name
        for recipient in RECIPIENTS:
            existing = db.query(Recipient).filter(Recipient.email == recipient["email"]).first()
            if not existing:
                existing = Recipient(email=recipient["email"], name=recipient.get("name"))
                db.add(existing)
                db.flush()
            for report_id in recipient["reports"]:
                link = (
                    db.query(RecipientReport)
                    .filter(
                        RecipientReport.recipient_id == existing.id,
                        RecipientReport.report_id == report_id,
                    )
                    .first()
                )
                if not link:
                    db.add(RecipientReport(recipient_id=existing.id, report_id=report_id))
        db.commit()


def _load_report_overrides() -> None:
    try:
        with SessionLocal() as db:
            rows = db.query(Report).all()
    except Exception:
        return
    overrides = []
    for row in rows:
        try:
            overrides.append(report_config_from_dict(row.config))
        except Exception:
            continue
    if overrides:
        set_report_overrides(overrides)


def _merge_missing(current: Dict[str, Any], default: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(current)
    for key, value in default.items():
        if key not in merged:
            merged[key] = value
        elif isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_missing(merged[key], value)
        elif isinstance(value, list) and not merged.get(key):
            merged[key] = value
    return merged


def _upgrade_report_config(report_id: str, current: Dict[str, Any], default: Dict[str, Any]) -> Dict[str, Any]:
    updated = dict(current)
    if report_id == "PK600_AFTERNOON_CUTOUT":
        schema = updated.get("schema", {})
        required = schema.get("required_fields")
        if required == ["cutout_value", "primal_value"]:
            schema["required_fields"] = default.get("schema", {}).get("required_fields", required)
            updated["schema"] = schema
    if report_id == "HG201_CME_INDEX":
        schema = updated.get("schema", {})
        required = schema.get("required_fields")
        if required == ["avg_net_price", "head_count"]:
            schema["required_fields"] = default.get("schema", {}).get("required_fields", required)
            updated["schema"] = schema
    return updated


def _parse_date(value: Optional[str]) -> date:
    if not value:
        raise HTTPException(status_code=400, detail="Missing date")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date format (expected YYYY-MM-DD)") from exc


def _compute_hg201_day(rows: List[Dict[str, Any]], report_date: date) -> Dict[str, Any]:
    worker = HG201CmeIndexWorker.__new__(HG201CmeIndexWorker)
    return worker.compute_index_for_date(rows, report_date)


def _run_to_dict(run: ReportRun | None) -> dict | None:
    if not run:
        return None
    return {
        "id": run.id,
        "report_id": run.report_id,
        "report_date": run.report_date.isoformat() if run.report_date else None,
        "state": run.state,
        "attempt": run.attempt,
        "run_started_at": run.run_started_at.isoformat(),
        "run_finished_at": run.run_finished_at.isoformat() if run.run_finished_at else None,
        "error_type": run.error_type,
        "error_message": run.error_message,
        "payload_hash": run.payload_hash,
    }


def _version_to_dict(version: ReportVersion | None) -> dict | None:
    if not version:
        return None
    return {
        "id": version.id,
        "report_id": version.report_id,
        "report_date": version.report_date.isoformat(),
        "payload_hash": version.payload_hash,
        "created_at": version.created_at.isoformat(),
    }
