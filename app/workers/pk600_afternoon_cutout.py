from app.registry import get_reports
from app.workers.base import BaseWorker


class PK600AfternoonCutoutWorker(BaseWorker):
    pass


def build(email_service, alert_service):
    config = next(r for r in get_reports() if r.report_id == "PK600_AFTERNOON_CUTOUT")
    return PK600AfternoonCutoutWorker(config, email_service, alert_service)
