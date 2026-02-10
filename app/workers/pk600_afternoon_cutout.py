from __future__ import annotations

from datetime import date
from typing import Dict, List

from app.registry import get_reports
from app.workers.base import BaseWorker


class PK600AfternoonCutoutWorker(BaseWorker):
    def _parse(self, payloads: List[List[Dict[str, object]]], report_date: date) -> Dict[str, object]:
        values_row = self._select_row(payloads[0], report_date) if payloads else None
        change_row = self._select_row(payloads[1], report_date) if len(payloads) > 1 else None
        if not values_row:
            raise ValueError("No matching values row for report date")
        parsed: Dict[str, object] = {"report_date": report_date.isoformat()}

        for field in [
            "total_loads_date_1",
            "pork_carcass",
            "pork_loin",
            "pork_butt",
            "pork_picnic",
            "pork_rib",
            "pork_ham",
            "pork_belly",
        ]:
            parsed[field] = values_row.get(field)

        if change_row:
            for field in [
                "chg_prev_carcass",
                "chg_prev_loin",
                "chg_prev_butt",
                "chg_prev_pic",
                "chg_prev_rib",
                "chg_prev_ham",
                "chg_prev_belly",
            ]:
                parsed[field] = change_row.get(field)
        return parsed


def build(email_service, alert_service):
    config = next(r for r in get_reports() if r.report_id == "PK600_AFTERNOON_CUTOUT")
    return PK600AfternoonCutoutWorker(config, email_service, alert_service)
