from __future__ import annotations

from typing import Any, Dict, List

from ctrlmap_cli.exporters.base import BaseExporter
from ctrlmap_cli.models.policies import PolicyDocument


class PoliciesExporter(BaseExporter):
    _LIST_PARAMS: Dict[str, str] = {"type": "policy"}

    def export(self) -> None:
        self._ensure_output_dir()
        self._log("Exporting policies...")

        raw_list: List[Dict[str, Any]] = self.client.get(
            "/procedures", params=self._LIST_PARAMS,
        )

        count = 0
        for raw in raw_list:
            doc = self._parse_document(raw)
            file_stem = doc.code or f"POL-{doc.id}"
            self._write_document(file_stem, doc)
            count += 1

        self._log(f"Exporting policies... done ({count} documents)")

    def _parse_document(self, raw: Dict[str, Any]) -> PolicyDocument:
        status_obj = raw.get("status")
        status_name = status_obj.get("name", "") if isinstance(status_obj, dict) else ""
        raw_id = raw.get("id", 0)
        item_id = raw_id if isinstance(raw_id, int) else 0
        return PolicyDocument(
            id=item_id,
            code=raw.get("procedureCode", ""),
            title=raw.get("name", "").strip(),
            status=status_name,
            body=raw.get("description", ""),
        )
