from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List

from ctrlmap_cli.exporters.base import BaseExporter
from ctrlmap_cli.formatters.markdown_formatter import MarkdownFormatter
from ctrlmap_cli.html_converter import (
    decode_description,
    html_to_markdown,
    normalize_headings,
)
from ctrlmap_cli.models.policies import PolicyDocument, PolicySection


class PoliciesExporter(BaseExporter):
    def export(self) -> None:
        self._ensure_output_dir()
        self._log("Exporting policies...")

        raw_list: List[Dict[str, Any]] = self.client.list_policies()

        documents: List[PolicyDocument] = []
        codes: List[str] = []
        for raw in raw_list:
            doc_id = _as_int(raw.get("id", 0))
            detail = self.client.get_policy(doc_id)

            doc = self._parse_document(detail)
            file_stem = doc.code or f"POL-{doc.id}"
            self._export_document(file_stem, doc)
            documents.append(doc)
            codes.append(file_stem)

        self._write_index(documents)

        if codes:
            self._log(
                "Exporting policies... "
                + ", ".join(codes)
                + f" done ({len(codes)} documents)"
            )
        else:
            self._log("Exporting policies... done (0 documents)")

    def _parse_document(self, detail: Dict[str, Any]) -> PolicyDocument:
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

        contributors_raw = detail.get("policyContributors", [])
        contributors: List[str] = []
        if isinstance(contributors_raw, list):
            for c in contributors_raw:
                if isinstance(c, dict):
                    name = c.get("fullname", "")
                    if name:
                        contributors.append(name)

        classification = str(detail.get("dataClassification") or "")
        review_date = _extract_date(detail, "reviewDate")
        updated = _extract_date(detail, "updatedate")
        controls = _extract_codes(detail.get("controls"), "controlCode", "code")
        requirements = _extract_codes(detail.get("requirements"), "requirementCode", "code")

        sections = self._parse_sections(detail.get("sections", []))
        policy_name = str(detail.get("name", "")).strip()
        body_html, body_markdown = self._render_sections(sections, policy_name)

        return PolicyDocument(
            id=item_id,
            code=str(detail.get("policyCode", "") or ""),
            title=policy_name,
            status=status_name,
            version=version,
            owner=owner,
            approver=approver,
            contributors=contributors,
            classification=classification,
            review_date=review_date,
            updated=updated,
            sections=sections,
            controls=controls,
            requirements=requirements,
            body_html=body_html,
            body_markdown=body_markdown,
        )

    @staticmethod
    def _parse_sections(raw_sections: Any) -> List[PolicySection]:
        if not isinstance(raw_sections, list):
            return []
        sections: List[PolicySection] = []
        for s in raw_sections:
            if not isinstance(s, dict):
                continue
            sections.append(PolicySection(
                id=_as_int(s.get("id", 0)),
                title=str(s.get("title", "")).strip(),
                description=str(s.get("description", "") or ""),
            ))
        return sections

    @staticmethod
    def _render_sections(
        sections: List[PolicySection], policy_name: str,
    ) -> tuple[str, str]:
        """Decode and convert all sections into combined HTML and markdown."""
        if not sections:
            return "", ""

        is_single = (
            len(sections) == 1 and sections[0].title.strip() == policy_name.strip()
        )

        html_parts: List[str] = []
        md_parts: List[str] = []
        for section in sections:
            decoded = decode_description(section.description)
            html_parts.append(decoded)
            section_md = html_to_markdown(decoded)

            if is_single:
                # Single section matching policy name: headings start at h2
                section_md = normalize_headings(section_md, target_min=2)
            else:
                # Multi-section: section title becomes h2, content starts at h3
                section_md = normalize_headings(section_md, target_min=3)
                section_md = f"## {section.title}\n\n{section_md}"

            md_parts.append(section_md)

        return "\n".join(html_parts), "\n\n".join(md_parts)

    def _export_document(self, file_stem: str, doc: PolicyDocument) -> None:
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
            "review_date": doc.review_date,
            "updated": doc.updated,
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

    def _write_index(self, documents: List[PolicyDocument]) -> None:
        frontmatter: Dict[str, Any] = {
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "document_count": len(documents),
        }
        generated_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        body_parts: List[str] = []
        noun = "policy" if len(documents) == 1 else "policies"
        body_parts.append(f"{len(documents)} {noun} exported on {generated_date}.")
        body_parts.append("")
        for doc in documents:
            file_stem = doc.code or f"POL-{doc.id}"
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
            title="Policies",
            body="\n".join(body_parts),
            frontmatter=frontmatter,
        )

        index_path = self.output_dir / "index.md"
        if self._should_write(index_path):
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(md_content)


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
