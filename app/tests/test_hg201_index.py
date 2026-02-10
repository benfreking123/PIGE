from __future__ import annotations

import json
from datetime import date

from app.registry import get_reports
from app.services.alerts import AlertService
from app.services.email import EmailPayload
from app.workers.hg201_cme_index import HG201CmeIndexWorker


class DummyEmailService:
    def render(self, template_name, context):
        return EmailPayload(subject="x", body_text="x", body_html="x")

    def send(self, recipients, payload):
        return None


def _load_fixture(name: str):
    with open(f"app/tests/fixtures/{name}.json", "r", encoding="utf-8") as f:
        return json.load(f)


def test_hg201_two_day_index():
    config = next(r for r in get_reports() if r.report_id == "HG201_CME_INDEX")
    email = DummyEmailService()
    worker = HG201CmeIndexWorker(config, email, AlertService(email))
    rows = _load_fixture("hg201_two_day")
    parsed = worker._parse([rows], date(2026, 2, 9))

    assert parsed["report_date_1"] == "2026-02-09"
    assert parsed["report_date_2"] == "2026-02-06"
    assert parsed["day1_total_weight"] == 7000.0
    assert parsed["day2_total_weight"] == 5320.0
    assert round(parsed["two_day_total_weight"], 2) == 12320.0
    assert round(parsed["two_day_total_value"], 2) == 892920.0
    assert round(parsed["index_value"], 3) == 72.477
