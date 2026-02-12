from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import logging

import boto3
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class EmailPayload:
    subject: str
    body_text: str
    body_html: str


class EmailService:
    def __init__(self) -> None:
        self.enabled = settings.email_enabled
        self.client = boto3.client("ses", region_name=settings.ses_region) if self.enabled else None
        self.env = Environment(
            loader=FileSystemLoader("app/templates"),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render(self, template_name: str, context: Dict[str, object]) -> EmailPayload:
        html_template = self.env.get_template(f"{template_name}.html.j2")
        text_template = self.env.get_template(f"{template_name}.txt.j2")
        subject = context.get("subject", "USDA Report Update")
        return EmailPayload(
            subject=subject,
            body_text=text_template.render(**context),
            body_html=html_template.render(**context),
        )

    def send(self, recipients: List[str], payload: EmailPayload) -> None:
        if not self.enabled:
            return
        if not recipients:
            return
        if not self.client:
            return
        for recipient in recipients:
            try:
                self.client.send_email(
                    Source=settings.ses_sender,
                    Destination={"ToAddresses": [recipient]},
                    Message={
                        "Subject": {"Data": payload.subject},
                        "Body": {
                            "Text": {"Data": payload.body_text},
                            "Html": {"Data": payload.body_html},
                        },
                    },
                )
            except Exception as exc:
                logger.exception("email send failed", extra={"recipient": recipient, "error": str(exc)})
