from app.registry import get_reports
from app.workers.base import BaseWorker


class XB402AfternoonCutoutWorker(BaseWorker):
    pass


def build(email_service, alert_service):
    config = next(r for r in get_reports() if r.report_id == "XB402_AFTERNOON_CUTOUT")
    return XB402AfternoonCutoutWorker(config, email_service, alert_service)
