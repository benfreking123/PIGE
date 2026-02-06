from __future__ import annotations

from typing import Dict, Optional

from app.registry import get_reports
from app.services.alerts import AlertService
from app.services.email import EmailService
from app.workers.base import BaseWorker
from app.workers.hg201_cme_index import build as build_hg201
from app.workers.pk600_afternoon_cash import build as build_pk600_afternoon_cash
from app.workers.pk600_afternoon_cutout import build as build_pk600_afternoon_cutout
from app.workers.pk600_morning_cash import build as build_pk600_morning_cash
from app.workers.pk600_morning_cutout_pdf import build as build_pk600_morning_cutout_pdf
from app.workers.xb402_afternoon_cutout import build as build_xb402_afternoon_cutout


_workers: Dict[str, BaseWorker] = {}


def init_workers() -> None:
    email_service = EmailService()
    alert_service = AlertService(email_service)
    builders = [
        build_pk600_morning_cash,
        build_pk600_morning_cutout_pdf,
        build_pk600_afternoon_cash,
        build_pk600_afternoon_cutout,
        build_xb402_afternoon_cutout,
        build_hg201,
    ]
    for builder in builders:
        worker = builder(email_service, alert_service)
        _workers[worker.config.report_id] = worker


def reload_workers() -> None:
    _workers.clear()
    init_workers()


def get_worker(report_id: str) -> Optional[BaseWorker]:
    return _workers.get(report_id)
