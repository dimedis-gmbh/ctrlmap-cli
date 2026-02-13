from __future__ import annotations

from typing import Any, Dict, List

from ctrlmap_cli.exporters.base import BaseExporter
from ctrlmap_cli.models.risks import RiskDocument


class RisksExporter(BaseExporter):
    def export(self) -> None:
        self._ensure_output_dir()
        self._log("Exporting risks...")

        raw_list: List[Dict[str, Any]] = self.client.get("/risks")

        count = 0
        for raw in raw_list:
            doc = self._parse_document(raw)
            file_stem = doc.code or f"RISK-{doc.id}"
            self._write_document(file_stem, doc)
            count += 1

        self._log(f"Exporting risks... done ({count} documents)")

    def _parse_document(self, raw: Dict[str, Any]) -> RiskDocument:
        status_obj = raw.get("status")
        if isinstance(status_obj, dict):
            status = str(status_obj.get("name", ""))
        else:
            status = str(status_obj or "")

        severity_obj = raw.get("severity")
        if isinstance(severity_obj, dict):
            severity = str(severity_obj.get("name", ""))
        else:
            severity = str(severity_obj or "")

        raw_id = raw.get("id", 0)
        item_id = raw_id if isinstance(raw_id, int) else 0

        title = str(raw.get("name") or raw.get("title") or "").strip()
        body = str(raw.get("description") or raw.get("body") or "")
        code = str(raw.get("riskCode") or raw.get("code") or "")

        return RiskDocument(
            id=item_id,
            code=code,
            title=title,
            status=status,
            severity=severity,
            body=body,
        )
