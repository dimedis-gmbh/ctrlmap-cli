from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ctrlmap_cli.exceptions import ItemNotFoundError
from ctrlmap_cli.exporters.base import BaseExporter
from ctrlmap_cli.formatters.markdown_formatter import MarkdownFormatter
from ctrlmap_cli.html_converter import decode_description, html_to_markdown
from ctrlmap_cli.models.procedures import ProcedureDocument


class ProceduresExporter(BaseExporter):
    def export(self) -> None:
        self._ensure_output_dir()
        self._log("Exporting procedures...")

        raw_list: List[Dict[str, Any]] = self.client.list_procedures()

        documents: List[ProcedureDocument] = []
        codes: List[str] = []
        for raw in raw_list:
            doc_id = _as_int(raw.get("id", 0))
            detail = self.client.get_procedure(doc_id)
            controls_raw = self.client.get_procedure_controls(doc_id)
            requirements_raw = self.client.get_procedure_requirements(doc_id)

            doc = self._parse_document(detail, controls_raw, requirements_raw)
            file_stem = doc.code or f"PRO-{doc.id}"
            self._export_document(file_stem, doc)
            documents.append(doc)
            codes.append(file_stem)

        self._write_index(documents)

        if codes:
            self._log(
                "Exporting procedures... "
                + ", ".join(codes)
                + f" done ({len(codes)} documents)"
            )
        else:
            self._log("Exporting procedures... done (0 documents)")

    def export_single(self, item_code: str) -> None:
        self._ensure_output_dir()
        full_code, _ = self._parse_item_code(item_code, "PRO")
        self._log(f"Exporting procedure {full_code}...")

        raw_list: List[Dict[str, Any]] = self.client.list_procedures()

        match = _find_by_code(raw_list, full_code, "procedureCode")
        if match is None:
            raise ItemNotFoundError(
                f"Procedure '{full_code}' not found in ControlMap. "
                "Check the code and try again."
            )

        doc_id = _as_int(match.get("id", 0))
        detail = self.client.get_procedure(doc_id)
        controls_raw = self.client.get_procedure_controls(doc_id)
        requirements_raw = self.client.get_procedure_requirements(doc_id)

        doc = self._parse_document(detail, controls_raw, requirements_raw)
        file_stem = doc.code or f"PRO-{doc.id}"
        self._export_document(file_stem, doc)

        self._rebuild_index(raw_list)
        self._log(f"Exporting procedures... {file_stem} done")

    def _rebuild_index(self, api_list: List[Dict[str, Any]]) -> None:
        """Rebuild index from API list + local frontmatter."""
        local_fm = self._read_local_frontmatter()

        frontmatter: Dict[str, Any] = {
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "document_count": len(api_list),
        }
        generated_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        body_parts: List[str] = []
        noun = "procedure" if len(api_list) == 1 else "procedures"
        body_parts.append(f"{len(api_list)} {noun} exported on {generated_date}.")
        body_parts.append("")
        for raw in api_list:
            code = raw.get("procedureCode", "")
            file_stem = code or f"PRO-{_as_int(raw.get('id', 0))}"
            fm = local_fm.get(file_stem)
            if fm:
                doc_label = fm.get("id", file_stem)
                title = fm.get("title", "")
                owner = fm.get("owner", "")
                status = fm.get("status", "")
                classification = fm.get("classification", "")
                review_date = fm.get("review_date", "")
            else:
                doc_label = code or file_stem
                title = str(raw.get("name", "")).strip()
                owner = ""
                status = ""
                classification = ""
                review_date = ""

            heading = f"## [{doc_label}]({file_stem}.md)"
            if title:
                heading += f" — {title}"
            body_parts.append(heading)
            body_parts.append("")
            body_parts.append(f"- **Owner:** {owner}")
            body_parts.append(f"- **Status:** {status}")
            if classification:
                body_parts.append(f"- **Classification:** {classification}")
            if review_date:
                body_parts.append(f"- **Review Date:** {review_date}")
            body_parts.append("")

        md_content = MarkdownFormatter.render(
            title="Procedures",
            body="\n".join(body_parts),
            frontmatter=frontmatter,
        )

        index_path = self.output_dir / "index.md"
        if self._should_write(index_path):
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(md_content)

    def _parse_document(
        self,
        detail: Dict[str, Any],
        controls_raw: Any,
        requirements_raw: Any,
    ) -> ProcedureDocument:
        raw_id = detail.get("id", 0)
        item_id = raw_id if isinstance(raw_id, int) else 0

        status_obj = detail.get("status")
        status_name = status_obj.get("name", "") if isinstance(status_obj, dict) else ""

        major = detail.get("majorVersion", 0)
        minor = detail.get("minorVersion", 0)
        version = f"{major}.{minor}"

        owner_obj = detail.get("owner")
        owner = owner_obj.get("fullname", "") if isinstance(owner_obj, dict) else ""

        approver_obj = detail.get("approver")
        approver = approver_obj.get("fullname", "") if isinstance(approver_obj, dict) else ""

        contributors_raw_list = detail.get("procedureContributors", [])
        contributors: List[str] = []
        if isinstance(contributors_raw_list, list):
            for c in contributors_raw_list:
                if isinstance(c, dict):
                    name = c.get("fullname", "")
                    if name:
                        contributors.append(name)

        classification = str(detail.get("dataClassification") or "")

        freq_obj = detail.get("frequency")
        frequency = freq_obj.get("name", "") if isinstance(freq_obj, dict) else ""

        review_date = _extract_date(detail, "reviewDate")
        updated = _extract_date(detail, "updatedate")
        controls = _extract_codes(controls_raw, "controlCode", "code")
        requirements = _extract_codes(requirements_raw, "requirementCode", "code")

        encoded_desc = detail.get("description", "")
        body_html = decode_description(encoded_desc)
        body_markdown = html_to_markdown(body_html)

        return ProcedureDocument(
            id=item_id,
            code=str(detail.get("procedureCode", "") or ""),
            title=str(detail.get("name", "")).strip(),
            status=status_name,
            version=version,
            owner=owner,
            approver=approver,
            contributors=contributors,
            classification=classification,
            frequency=frequency,
            review_date=review_date,
            updated=updated,
            controls=controls,
            requirements=requirements,
            body_html=body_html,
            body_markdown=body_markdown,
        )

    def _export_document(self, file_stem: str, doc: ProcedureDocument) -> None:
        frontmatter_id = doc.code or file_stem
        frontmatter: Dict[str, Any] = {
            "id": frontmatter_id,
            "title": doc.title,
            "status": doc.status,
            "version": doc.version,
            "owner": doc.owner,
            "approver": doc.approver,
            "contributors": doc.contributors,
            "classification": doc.classification,
            "frequency": doc.frequency,
            "review_date": doc.review_date,
            "updated": doc.updated,
            "controls": doc.controls,
            "requirements": doc.requirements,
        }

        md_content = MarkdownFormatter.render(
            title=f"{frontmatter_id} — {doc.title}",
            body=doc.body_markdown,
            frontmatter=frontmatter,
        )

        md_path = self.output_dir / f"{file_stem}.md"
        if self._should_write(md_path):
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)

        if self.keep_raw_json:
            json_path = self.output_dir / f"{file_stem}.json"
            if self._should_write(json_path):
                raw = asdict(doc)
                self._json_formatter.write(raw, json_path)

    def _write_index(self, documents: List[ProcedureDocument]) -> None:
        frontmatter: Dict[str, Any] = {
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "document_count": len(documents),
        }
        generated_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        body_parts: List[str] = []
        noun = "procedure" if len(documents) == 1 else "procedures"
        body_parts.append(f"{len(documents)} {noun} exported on {generated_date}.")
        body_parts.append("")
        for doc in documents:
            file_stem = doc.code or f"PRO-{doc.id}"
            doc_label = doc.code or file_stem
            body_parts.append(f"## [{doc_label}]({file_stem}.md) — {doc.title}")
            body_parts.append("")
            body_parts.append(f"- **Owner:** {doc.owner}")
            body_parts.append(f"- **Status:** {doc.status}")
            if doc.classification:
                body_parts.append(f"- **Classification:** {doc.classification}")
            if doc.review_date:
                body_parts.append(f"- **Review Date:** {doc.review_date}")
            body_parts.append("")

        md_content = MarkdownFormatter.render(
            title="Procedures",
            body="\n".join(body_parts),
            frontmatter=frontmatter,
        )

        index_path = self.output_dir / "index.md"
        if self._should_write(index_path):
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(md_content)


def _find_by_code(
    items: List[Dict[str, Any]], code: str, code_key: str,
) -> Optional[Dict[str, Any]]:
    """Find an item in the API list by its code field."""
    for item in items:
        if item.get(code_key) == code:
            return item
    return None


def _extract_date(data: Dict[str, Any], *keys: str) -> str:
    """Extract a date string from the first matching key, returning date-only."""
    for key in keys:
        value = data.get(key)
        if value is not None:
            s = str(value).strip()
            if s:
                return s[:10] if len(s) >= 10 else s
    return ""


def _extract_codes(items: Any, *keys: str) -> List[str]:
    if not isinstance(items, list):
        return []

    codes: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        for key in keys:
            value = item.get(key)
            if value:
                codes.append(str(value))
                break
    return codes


def _as_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0
