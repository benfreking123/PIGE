from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import AlertState
from app.registry import ALERTING
from app.services.email import EmailService


class AlertService:
    def __init__(self, email_service: EmailService) -> None:
        self.email_service = email_service

    def record_failure(self, db: Session, report_id: str, run_id: str, error_type: str) -> None:
        state = db.get(AlertState, report_id)
        if not state:
            state = AlertState(report_id=report_id, consecutive_failures=0)
            db.add(state)
        state.consecutive_failures += 1
        state.last_failure_at = datetime.utcnow()
        state.updated_at = datetime.utcnow()

        threshold = ALERTING.get("consecutive_failures_threshold", 3)
        if state.consecutive_failures >= threshold:
            self._send_alert(report_id, run_id, error_type, state.last_failure_at)

    def clear_failure(self, db: Session, report_id: str) -> None:
        state = db.get(AlertState, report_id)
        if not state:
            return
        state.consecutive_failures = 0
        state.updated_at = datetime.utcnow()

    def _send_alert(
        self,
        report_id: str,
        run_id: str,
        error_type: str,
        last_attempt_at: Optional[datetime],
    ) -> None:
        payload = self.email_service.render(
            "alert",
            {
                "subject": f"USDA Monitor Alert: {report_id}",
                "report_id": report_id,
                "run_id": run_id,
                "error_type": error_type,
                "last_attempt_at": last_attempt_at.isoformat() if last_attempt_at else "unknown",
            },
        )
        self.email_service.send([settings.master_alert_email], payload)
