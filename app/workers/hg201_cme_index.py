from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.registry import get_reports
from app.workers.base import BaseWorker, FetchResult, ParseError


class HG201CmeIndexWorker(BaseWorker):
    CATEGORY_MAP = {
        "negotiated": "Prod. Sold Negotiated",
        "formula": "Prod. Sold Swine or Pork Market Formula",
        "negotiated_formula": "Prod. Sold Negotiated Formula",
    }

    async def _fetch_for_date_window(self, client) -> Tuple[Optional[date], Optional[FetchResult], bool]:
        today = self.forced_report_date or datetime.now(tz=self.tz).date()
        start = today - timedelta(days=self.config.date_search_window_days - 1)
        report_range = f"{start.strftime('%m/%d/%Y')}:{today.strftime('%m/%d/%Y')}"
        endpoint = self.config.endpoints[0]
        url = endpoint.build_url(report_range)
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and isinstance(data.get("results"), list):
            rows = data["results"]
        elif isinstance(data, list):
            rows = data
        else:
            rows = []
        if not rows:
            return today, None, self._should_mark_holiday(today)

        grouped = self._group_by_date(rows)
        if today not in grouped:
            return today, None, self._should_mark_holiday(today)
        latest_any = self._latest_any_date(rows)
        if not latest_any:
            return today, None, self._should_mark_holiday(today)

        payloads = [rows]
        return latest_any, FetchResult(payloads=payloads, urls=[url]), False

    def _parse(self, payloads: List[List[Dict[str, Any]]], report_date: date) -> Dict[str, Any]:
        if not payloads or not payloads[0]:
            raise ParseError("No HG201 rows available")
        rows = payloads[0]
        day1 = self._latest_any_date(rows)
        if not day1:
            raise ParseError("No report dates available for index calculation")
        index_payload = self.compute_index_for_date(rows, day1)
        return index_payload

    def _group_by_date(self, rows: List[Dict[str, Any]]) -> Dict[date, Dict[str, Dict[str, Optional[float]]]]:
        grouped: Dict[date, Dict[str, Dict[str, Optional[float]]]] = {}
        for row in rows:
            report_date = self._parse_row_date(row)
            if not report_date:
                continue
            category = self._category_for_row(row)
            if not category:
                continue
            head_count = self._parse_number(row.get("head_count"))
            carcass_weight = self._parse_number(row.get("avg_carcass_weight"))
            net_price = self._parse_number(row.get("avg_net_price"))
            grouped.setdefault(report_date, {})[category] = {
                "head_count": head_count,
                "avg_carcass_weight": carcass_weight,
                "avg_net_price": net_price,
            }
        return grouped

    def _valid_dates(self, grouped: Dict[date, Dict[str, Dict[str, Optional[float]]]]) -> List[date]:
        dates = []
        for report_date, categories in grouped.items():
            if categories:
                dates.append(report_date)
        return sorted(dates, reverse=True)

    def _compute_day(self, data: Dict[str, Dict[str, Optional[float]]]) -> Dict[str, float]:
        negotiated = self._weight_value(data.get("negotiated"))
        formula = self._weight_value(data.get("formula"))
        negotiated_formula = self._weight_value(data.get("negotiated_formula"))
        total_weight = negotiated["weight"] + formula["weight"] + negotiated_formula["weight"]
        total_value = negotiated["value"] + formula["value"] + negotiated_formula["value"]
        return {
            "negotiated_weight": negotiated["weight"],
            "formula_weight": formula["weight"],
            "negotiated_formula_weight": negotiated_formula["weight"],
            "negotiated_value": negotiated["value"],
            "formula_value": formula["value"],
            "negotiated_formula_value": negotiated_formula["value"],
            "total_weight": total_weight,
            "total_value": total_value,
        }

    @staticmethod
    def compute_daily_components(rows: List[Dict[str, Any]], report_date: date) -> Dict[str, float]:
        worker = HG201CmeIndexWorker.__new__(HG201CmeIndexWorker)
        grouped = worker._group_by_date(rows)
        day_data = grouped.get(report_date, {})
        return worker._compute_day(day_data)

    def _weight_value(self, row: Optional[Dict[str, Optional[float]]]) -> Dict[str, float]:
        if not row:
            return {"weight": 0.0, "value": 0.0}
        head_count = row.get("head_count") or 0.0
        carcass_weight = row.get("avg_carcass_weight") or 0.0
        net_price = row.get("avg_net_price") or 0.0
        weight = head_count * carcass_weight
        value = weight * net_price
        return {"weight": weight, "value": value}

    def _category_for_row(self, row: Dict[str, Any]) -> Optional[str]:
        purchase_type = row.get("purchase_type")
        for key, value in self.CATEGORY_MAP.items():
            if purchase_type == value:
                return key
        return None

    def _parse_row_date(self, row: Dict[str, Any]) -> Optional[date]:
        for key in ["report_date", "report date", "reportdate", "Report Date"]:
            value = row.get(key)
            if not value:
                continue
            try:
                return datetime.strptime(str(value).strip(), "%m/%d/%Y").date()
            except ValueError:
                continue
        return None

    def _parse_number(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        text = str(value).strip().replace(",", "")
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def _latest_any_date(self, rows: List[Dict[str, Any]]) -> Optional[date]:
        grouped = self._group_by_date(rows)
        valid_dates = self._valid_dates(grouped)
        return valid_dates[0] if valid_dates else None

    def _prior_reported_date(self, rows: List[Dict[str, Any]], report_date: date) -> Optional[date]:
        grouped = self._group_by_date(rows)
        valid_dates = self._valid_dates(grouped)
        for idx, value in enumerate(valid_dates):
            if value == report_date and idx + 1 < len(valid_dates):
                return valid_dates[idx + 1]
        return None

    def compute_index_for_date(self, rows: List[Dict[str, Any]], report_date: date) -> Dict[str, Any]:
        grouped = self._group_by_date(rows)
        prior_date = self._prior_reported_date(rows, report_date)
        day1_data = grouped.get(report_date, {})
        day2_data = grouped.get(prior_date, {}) if prior_date else {}

        day1_calc = self._compute_day(day1_data)
        day2_calc = self._compute_day(day2_data)

        two_day_total_weight = day1_calc["total_weight"] + day2_calc["total_weight"]
        two_day_total_value = day1_calc["total_value"] + day2_calc["total_value"]
        index_value = two_day_total_value / two_day_total_weight if two_day_total_weight else 0.0

        return {
            "report_date": report_date.isoformat(),
            "prior_day_date": prior_date.isoformat() if prior_date else None,
            "negotiated_weight": day1_calc["negotiated_weight"],
            "formula_weight": day1_calc["formula_weight"],
            "negotiated_formula_weight": day1_calc["negotiated_formula_weight"],
            "negotiated_value": day1_calc["negotiated_value"],
            "formula_value": day1_calc["formula_value"],
            "negotiated_formula_value": day1_calc["negotiated_formula_value"],
            "total_weight": day1_calc["total_weight"],
            "total_value": day1_calc["total_value"],
            "prior_day_total_weight": day2_calc["total_weight"],
            "prior_day_total_value": day2_calc["total_value"],
            "index_value": index_value,
        }


def build(email_service, alert_service):
    config = next(r for r in get_reports() if r.report_id == "HG201_CME_INDEX")
    return HG201CmeIndexWorker(config, email_service, alert_service)
