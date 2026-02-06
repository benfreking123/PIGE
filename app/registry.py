from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import time
from typing import Any, Dict, List, Optional


API_BASE = "https://mpr.datamart.ams.usda.gov/services/v1.1/reports"


@dataclass(frozen=True)
class EndpointConfig:
    report_number: int
    report_path: str
    absolute_url: str | None = None

    def build_url(self, report_date_str: str) -> str:
        if self.absolute_url:
            return self.absolute_url
        return f"{API_BASE}/{self.report_number}/{self.report_path}?q=report_date={report_date_str}"


@dataclass(frozen=True)
class PollingWindow:
    start: time
    end: time


@dataclass(frozen=True)
class PollingRule:
    inside_cadence_sec: int
    outside_cadence_sec: int
    max_late_hours: int
    error_backoff_base_sec: int
    error_backoff_max_sec: int
    jitter_sec: int


@dataclass(frozen=True)
class ReportSchema:
    report_id: str
    required_fields: List[str]
    select_rule: Dict[str, Any]
    derived_fields: List[str]


@dataclass(frozen=True)
class ReportConfig:
    report_id: str
    name: str
    endpoints: List[EndpointConfig]
    windows: List[PollingWindow]
    polling: PollingRule
    needs_prior_day: bool
    date_search_window_days: int
    schema: ReportSchema

    def to_db_config(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "name": self.name,
            "endpoints": [asdict(e) for e in self.endpoints],
            "windows": [{"start": w.start.isoformat(), "end": w.end.isoformat()} for w in self.windows],
            "polling": asdict(self.polling),
            "needs_prior_day": self.needs_prior_day,
            "date_search_window_days": self.date_search_window_days,
            "schema": asdict(self.schema),
        }


REPORTS: List[ReportConfig] = [
    ReportConfig(
        report_id="PK600_MORNING_CASH",
        name="PK600 Morning Cash",
        endpoints=[EndpointConfig(2674, "National Volume and Price Data")],
        windows=[PollingWindow(start=time(6, 30), end=time(9, 0))],
        polling=PollingRule(
            inside_cadence_sec=300,
            outside_cadence_sec=900,
            max_late_hours=6,
            error_backoff_base_sec=120,
            error_backoff_max_sec=1800,
            jitter_sec=30,
        ),
        needs_prior_day=False,
        date_search_window_days=1,
        schema=ReportSchema(
            report_id="PK600_MORNING_CASH",
            required_fields=["head_count", "wtd_avg", "price_low", "price_high"],
            select_rule={"type": "date_match"},
            derived_fields=[],
        ),
    ),
    ReportConfig(
        report_id="PK600_AFTERNOON_CASH",
        name="PK600 Afternoon Cash",
        endpoints=[EndpointConfig(2675, "National Volume and Price Data")],
        windows=[PollingWindow(start=time(12, 0), end=time(14, 30))],
        polling=PollingRule(
            inside_cadence_sec=300,
            outside_cadence_sec=900,
            max_late_hours=6,
            error_backoff_base_sec=120,
            error_backoff_max_sec=1800,
            jitter_sec=30,
        ),
        needs_prior_day=False,
        date_search_window_days=1,
        schema=ReportSchema(
            report_id="PK600_AFTERNOON_CASH",
            required_fields=["head_count", "wtd_avg", "price_low", "price_high"],
            select_rule={"type": "date_match"},
            derived_fields=[],
        ),
    ),
    ReportConfig(
        report_id="PK600_AFTERNOON_CUTOUT",
        name="PK600 Afternoon Pork Cutout",
        endpoints=[
            EndpointConfig(2498, "Cutout and Primal Values"),
            EndpointConfig(2498, "Change From Prior Day"),
        ],
        windows=[PollingWindow(start=time(12, 0), end=time(14, 30))],
        polling=PollingRule(
            inside_cadence_sec=300,
            outside_cadence_sec=900,
            max_late_hours=6,
            error_backoff_base_sec=120,
            error_backoff_max_sec=1800,
            jitter_sec=30,
        ),
        needs_prior_day=False,
        date_search_window_days=1,
        schema=ReportSchema(
            report_id="PK600_AFTERNOON_CUTOUT",
            required_fields=["cutout_value", "primal_value"],
            select_rule={"type": "date_match"},
            derived_fields=[],
        ),
    ),
    ReportConfig(
        report_id="XB402_AFTERNOON_CUTOUT",
        name="XB402 Afternoon Beef Cutout",
        endpoints=[
            EndpointConfig(2453, "Current Cutout Values"),
            EndpointConfig(2453, "Change From Prior Day"),
            EndpointConfig(2453, "Current Volume"),
        ],
        windows=[PollingWindow(start=time(12, 0), end=time(15, 0))],
        polling=PollingRule(
            inside_cadence_sec=300,
            outside_cadence_sec=900,
            max_late_hours=6,
            error_backoff_base_sec=120,
            error_backoff_max_sec=1800,
            jitter_sec=30,
        ),
        needs_prior_day=False,
        date_search_window_days=1,
        schema=ReportSchema(
            report_id="XB402_AFTERNOON_CUTOUT",
            required_fields=["cutout_value", "volume"],
            select_rule={"type": "date_match"},
            derived_fields=[],
        ),
    ),
    ReportConfig(
        report_id="HG201_CME_INDEX",
        name="HG201 CME Index",
        endpoints=[EndpointConfig(2511, "Barrows/Gilts")],
        windows=[PollingWindow(start=time(13, 0), end=time(16, 30))],
        polling=PollingRule(
            inside_cadence_sec=600,
            outside_cadence_sec=1800,
            max_late_hours=8,
            error_backoff_base_sec=180,
            error_backoff_max_sec=3600,
            jitter_sec=60,
        ),
        needs_prior_day=True,
        date_search_window_days=7,
        schema=ReportSchema(
            report_id="HG201_CME_INDEX",
            required_fields=["avg_net_price", "head_count"],
            select_rule={"type": "field_equals", "field": "purchase_type", "value": "Prod. Sold (All Purchase Types)"},
            derived_fields=[],
        ),
    ),
    ReportConfig(
        report_id="PK600_MORNING_CUTOUT_PDF",
        name="PK600 Morning Pork Cutout (PDF)",
        endpoints=[EndpointConfig(0, "", absolute_url="https://www.ams.usda.gov/mnreports/ams_2496.pdf")],
        windows=[PollingWindow(start=time(6, 30), end=time(9, 0))],
        polling=PollingRule(
            inside_cadence_sec=600,
            outside_cadence_sec=1800,
            max_late_hours=6,
            error_backoff_base_sec=180,
            error_backoff_max_sec=3600,
            jitter_sec=60,
        ),
        needs_prior_day=False,
        date_search_window_days=1,
        schema=ReportSchema(
            report_id="PK600_MORNING_CUTOUT_PDF",
            required_fields=[
                "loads",
                "carcass",
                "loin",
                "butt",
                "pic",
                "rib",
                "ham",
                "belly",
                "change_carcass",
                "change_loin",
                "change_butt",
                "change_pic",
                "change_rib",
                "change_ham",
                "change_belly",
                "text_excerpt",
                "page_count",
            ],
            select_rule={"type": "row_index", "index": 0},
            derived_fields=[],
        ),
    ),
]


RECIPIENTS = [
    {"email": "recipient@example.com", "name": "Example Recipient", "reports": ["PK600_MORNING_CASH"]},
]


ALERTING = {
    "consecutive_failures_threshold": 3,
}


_REPORT_OVERRIDES: Optional[List[ReportConfig]] = None


def get_reports() -> List[ReportConfig]:
    return _REPORT_OVERRIDES or REPORTS


def set_report_overrides(reports: List[ReportConfig]) -> None:
    global _REPORT_OVERRIDES
    _REPORT_OVERRIDES = reports


def _parse_time(value: str) -> time:
    parts = value.split(":")
    if len(parts) < 2:
        raise ValueError(f"Invalid time format: {value}")
    hour = int(parts[0])
    minute = int(parts[1])
    second = int(parts[2]) if len(parts) > 2 else 0
    return time(hour=hour, minute=minute, second=second)


def report_config_from_dict(data: Dict[str, Any]) -> ReportConfig:
    endpoints = [
        EndpointConfig(
            report_number=int(e.get("report_number", 0)),
            report_path=str(e.get("report_path", "")),
            absolute_url=e.get("absolute_url"),
        )
        for e in data.get("endpoints", [])
    ]
    windows = [
        PollingWindow(start=_parse_time(w["start"]), end=_parse_time(w["end"]))
        for w in data.get("windows", [])
    ]
    polling_data = data.get("polling", {})
    polling = PollingRule(
        inside_cadence_sec=int(polling_data["inside_cadence_sec"]),
        outside_cadence_sec=int(polling_data["outside_cadence_sec"]),
        max_late_hours=int(polling_data["max_late_hours"]),
        error_backoff_base_sec=int(polling_data["error_backoff_base_sec"]),
        error_backoff_max_sec=int(polling_data["error_backoff_max_sec"]),
        jitter_sec=int(polling_data["jitter_sec"]),
    )
    schema_data = data.get("schema", {})
    schema = ReportSchema(
        report_id=str(schema_data.get("report_id", data.get("report_id"))),
        required_fields=list(schema_data.get("required_fields", [])),
        select_rule=dict(schema_data.get("select_rule", {})),
        derived_fields=list(schema_data.get("derived_fields", [])),
    )
    return ReportConfig(
        report_id=str(data["report_id"]),
        name=str(data["name"]),
        endpoints=endpoints,
        windows=windows,
        polling=polling,
        needs_prior_day=bool(data.get("needs_prior_day", False)),
        date_search_window_days=int(data.get("date_search_window_days", 1)),
        schema=schema,
    )
