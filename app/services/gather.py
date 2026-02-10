from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple

import httpx

from app.registry import EndpointConfig, ReportConfig


def _date_range(start_date: date, end_date: date) -> List[date]:
    days = (end_date - start_date).days
    return [start_date + timedelta(days=idx) for idx in range(days + 1)]


def _build_range_url(endpoint: EndpointConfig, start_date: date, end_date: date) -> str:
    if endpoint.absolute_url:
        return endpoint.absolute_url
    start = start_date.strftime("%m/%d/%Y")
    end = end_date.strftime("%m/%d/%Y")
    return endpoint.build_url(f"{start}:{end}")


def fetch_range_payloads(
    config: ReportConfig, start_date: date, end_date: date
) -> Dict[date, List[List[Dict[str, object]]]]:
    results: Dict[date, List[List[Dict[str, object]]]] = defaultdict(list)
    timeout = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
    with httpx.Client(timeout=timeout) as client:
        for endpoint in config.endpoints:
            url = _build_range_url(endpoint, start_date, end_date)
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and isinstance(data.get("results"), list):
                rows = data["results"]
            elif isinstance(data, list):
                rows = data
            else:
                rows = []
            grouped: Dict[date, List[Dict[str, object]]] = defaultdict(list)
            for row in rows:
                report_date = _parse_row_date(row)
                if not report_date:
                    continue
                grouped[report_date].append(row)
            for report_date, row_list in grouped.items():
                results[report_date].append(row_list)
    return results


def fetch_range_rows(config: ReportConfig, start_date: date, end_date: date) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    timeout = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
    with httpx.Client(timeout=timeout) as client:
        for endpoint in config.endpoints:
            url = _build_range_url(endpoint, start_date, end_date)
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and isinstance(data.get("results"), list):
                rows.extend(data["results"])
            elif isinstance(data, list):
                rows.extend(data)
    return rows


def group_rows_by_date(rows: List[Dict[str, object]]) -> Dict[date, List[Dict[str, object]]]:
    grouped: Dict[date, List[Dict[str, object]]] = defaultdict(list)
    for row in rows:
        report_date = _parse_row_date(row)
        if not report_date:
            continue
        grouped[report_date].append(row)
    return grouped


def _parse_row_date(row: Dict[str, object]) -> date | None:
    for key in ["report_date", "report date", "reportdate", "Report Date"]:
        value = row.get(key)
        if not value:
            continue
        try:
            return datetime.strptime(str(value).strip(), "%m/%d/%Y").date()
        except ValueError:
            continue
    return None
