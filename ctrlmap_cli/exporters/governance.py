from __future__ import annotations

from typing import Any, Dict, List

from ctrlmap_cli.exporters.base import BaseExporter
from ctrlmap_cli.models.governance import GovernanceDocument


class GovernanceExporter(BaseExporter):
    _LIST_PARAMS: Dict[str, str] = {"type": "governance"}

    def export(self) -> None:
        self._ensure_output_dir()
        self._log("Exporting governance documents...")

        raw_list: List[Dict[str, Any]] = self.client.get(
            "/procedures", params=self._LIST_PARAMS,
        )

        codes: List[str] = []
        for raw in raw_list:
            doc = self._parse_document(raw)
            file_stem = doc.code or f"GOV-{doc.id}"
            self._write_document(file_stem, doc)
            codes.append(file_stem)

        if codes:
            self._log(
                "Exporting governance... "
                + ", ".join(codes)
                + f" done ({len(codes)} documents)"
            )
        else:
            self._log("Exporting governance... done (0 documents)")

    def _parse_document(self, raw: Dict[str, Any]) -> GovernanceDocument:
        status_obj = raw.get("status")
        status_name = status_obj.get("name", "") if isinstance(status_obj, dict) else ""
        raw_id = raw.get("id", 0)
        item_id = raw_id if isinstance(raw_id, int) else 0
        return GovernanceDocument(
            id=item_id,
            code=raw.get("procedureCode", ""),
            title=raw.get("name", "").strip(),
            status=status_name,
            body=raw.get("description", ""),
        )
