from __future__ import annotations

import argparse
import asyncio
from datetime import datetime

from app.workers.registry import get_worker, init_workers


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a single report once.")
    parser.add_argument("--report-id", required=True)
    parser.add_argument("--report-date", required=False)
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
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
