from __future__ import annotations

import argparse
import asyncio
from datetime import datetime

from app.registry import get_reports
from app.db.session import SessionLocal
from app.db.models import ReportVersion
from app.services.email import EmailPayload
from app.services.http import get_client
from app.workers.hg201_cme_index import HG201CmeIndexWorker
from app.workers.registry import get_worker, init_workers


class DummyEmailService:
    def render(self, template_name, context):
        return EmailPayload(subject="x", body_text="x", body_html="x")

    def send(self, recipients, payload):
        return None


class DummyAlertService:
    def record_failure(self, db, report_id, run_id, error_type):
        return None

    def clear_failure(self, db, report_id):
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a single report once.")
    parser.add_argument("--report-id", required=True)
    parser.add_argument("--report-date", required=False)
    parser.add_argument("--debug-parse", action="store_true")
    parser.add_argument("--reparse-latest", action="store_true")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    if args.debug_parse:
        if args.report_id != "HG201_CME_INDEX":
            raise SystemExit("--debug-parse currently supports HG201_CME_INDEX only")
        config = next(r for r in get_reports() if r.report_id == "HG201_CME_INDEX")
        worker = HG201CmeIndexWorker(config, DummyEmailService(), DummyAlertService())
        if args.report_date:
            worker.forced_report_date = datetime.strptime(args.report_date, "%Y-%m-%d").date()
        async with get_client() as client:
            report_date, fetch_result, _ = await worker._fetch_for_date_window(client)
            if not fetch_result or not report_date:
                raise SystemExit("No data returned for debug parse")
            parsed = worker._parse(fetch_result.payloads, report_date)
            print("report_date_used:", report_date.isoformat())
            print("payload_urls:", fetch_result.urls)
            print("parsed_fields:")
            print(parsed)
        return
    if args.reparse_latest:
        if args.report_id != "HG201_CME_INDEX":
            raise SystemExit("--reparse-latest currently supports HG201_CME_INDEX only")
        config = next(r for r in get_reports() if r.report_id == "HG201_CME_INDEX")
        worker = HG201CmeIndexWorker(config, DummyEmailService(), DummyAlertService())
        if args.report_date:
            worker.forced_report_date = datetime.strptime(args.report_date, "%Y-%m-%d").date()
        async with get_client() as client:
            report_date, fetch_result, _ = await worker._fetch_for_date_window(client)
            if not fetch_result or not report_date:
                raise SystemExit("No data returned for reparse")
            parsed = worker._parse(fetch_result.payloads, report_date)
        with SessionLocal() as db:
            version = (
                db.query(ReportVersion)
                .filter(ReportVersion.report_id == "HG201_CME_INDEX")
                .order_by(ReportVersion.created_at.desc())
                .first()
            )
            if not version:
                raise SystemExit("No HG201 report_versions found")
            version.parsed_fields = parsed
            db.commit()
        print("Reparsed latest HG201 version.")
        return
    init_workers()
    worker = get_worker(args.report_id)
    if not worker:
        raise SystemExit(f"Report not found: {args.report_id}")
    if args.report_date:
        report_date = datetime.strptime(args.report_date, "%Y-%m-%d").date()
        worker.forced_report_date = report_date
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
