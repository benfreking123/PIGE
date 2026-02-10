from app.registry import get_reports
from app.workers.base import BaseWorker


class HG201CmeIndexWorker(BaseWorker):
    pass


def build(email_service, alert_service):
    config = next(r for r in get_reports() if r.report_id == "HG201_CME_INDEX")
    return HG201CmeIndexWorker(config, email_service, alert_service)
