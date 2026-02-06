from __future__ import annotations

import json
from datetime import date

from app.registry import get_reports
from app.services.alerts import AlertService
from app.services.email import EmailPayload
from app.workers.base import BaseWorker


def _load_fixture(name: str):
    with open(f"app/tests/fixtures/{name}.json", "r", encoding="utf-8") as f:
        return json.load(f)


class DummyEmailService:
    def render(self, template_name, context):
        return EmailPayload(subject="x", body_text="x", body_html="x")

    def send(self, recipients, payload):
        return None


def test_pk600_morning_cash_parse():
    config = next(r for r in get_reports() if r.report_id == "PK600_MORNING_CASH")
    email = DummyEmailService()
    worker = BaseWorker(config, email, AlertService(email))
    payloads = [_load_fixture("pk600_morning_cash")]
    parsed = worker._parse(payloads, date(2026, 1, 15))
    assert parsed["head_count"] == 12000
    assert parsed["wtd_avg"] == 76.5
    assert parsed["price_low"] == 74.0
    assert parsed["price_high"] == 79.0
