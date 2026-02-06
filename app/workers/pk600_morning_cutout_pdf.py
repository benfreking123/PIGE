from __future__ import annotations

import base64
import io
import re
from datetime import date, datetime
from typing import Dict, Optional, Tuple

import pdfplumber

from app.registry import get_reports
from app.workers.base import BaseWorker, FetchResult


class PK600MorningCutoutPdfWorker(BaseWorker):
    async def _fetch_for_date_window(self, client) -> Tuple[Optional[date], Optional[FetchResult], bool]:
        endpoint = self.config.endpoints[0]
        url = endpoint.build_url("")
        resp = await client.get(url)
        resp.raise_for_status()
        content = resp.content

        text_excerpt = ""
        page_count = 0
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                page_count = len(pdf.pages)
                if pdf.pages:
                    text_excerpt = (pdf.pages[0].extract_text() or "")[:1000]
        except Exception:
            text_excerpt = ""

        report_date = self._extract_date(text_excerpt) or datetime.now(tz=self.tz).date()
        table_fields = self._extract_primal_values(text_excerpt, report_date)
        payload_row: Dict[str, object] = {
            "report_date": report_date.strftime("%m/%d/%Y"),
            "text_excerpt": text_excerpt,
            "page_count": page_count,
            "pdf_base64": base64.b64encode(content).decode("ascii"),
        }
        payload_row.update(table_fields)
        payloads = [[payload_row]]
        return report_date, FetchResult(payloads=payloads, urls=[url]), False

    def _extract_date(self, text: str) -> Optional[date]:
        match = re.search(r"\b(\d{1,2}/\d{1,2}/\d{4})\b", text)
        if not match:
            return None
        try:
            return datetime.strptime(match.group(1), "%m/%d/%Y").date()
        except ValueError:
            return None

    def _extract_primal_values(self, text: str, report_date: date) -> Dict[str, object]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        header_idx = None
        for idx, line in enumerate(lines):
            if line.startswith("Date Loads Carcass Loin Butt Pic Rib Ham Belly"):
                header_idx = idx
                break
        if header_idx is None:
            return {}

        target = report_date.strftime("%m/%d/%Y")
        data_line = None
        change_line = None
        for idx in range(header_idx + 1, len(lines)):
            line = lines[idx]
            if line.startswith(target):
                data_line = line
                if idx + 1 < len(lines) and lines[idx + 1].startswith("Change:"):
                    change_line = lines[idx + 1]
                break

        if not data_line:
            return {}

        parts = data_line.split()
        if len(parts) < 9:
            return {}

        fields: Dict[str, object] = {
            "loads": parts[1],
            "carcass": parts[2],
            "loin": parts[3],
            "butt": parts[4],
            "pic": parts[5],
            "rib": parts[6],
            "ham": parts[7],
            "belly": parts[8],
        }

        if change_line:
            change_parts = change_line.replace("Change:", "").split()
            if len(change_parts) == 7:
                fields.update(
                    {
                        "change_carcass": change_parts[0],
                        "change_loin": change_parts[1],
                        "change_butt": change_parts[2],
                        "change_pic": change_parts[3],
                        "change_rib": change_parts[4],
                        "change_ham": change_parts[5],
                        "change_belly": change_parts[6],
                    }
                )
            elif len(change_parts) >= 8:
                fields.update(
                    {
                        "change_loads": change_parts[0],
                        "change_carcass": change_parts[1],
                        "change_loin": change_parts[2],
                        "change_butt": change_parts[3],
                        "change_pic": change_parts[4],
                        "change_rib": change_parts[5],
                        "change_ham": change_parts[6],
                        "change_belly": change_parts[7],
                    }
                )

        return fields


def build(email_service, alert_service):
    config = next(r for r in get_reports() if r.report_id == "PK600_MORNING_CUTOUT_PDF")
    return PK600MorningCutoutPdfWorker(config, email_service, alert_service)
