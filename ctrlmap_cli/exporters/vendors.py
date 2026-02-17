from __future__ import annotations

import hashlib
import re
import textwrap
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from ctrlmap_cli.exporters.base import BaseExporter
from ctrlmap_cli.formatters.markdown_formatter import MarkdownFormatter
from ctrlmap_cli.models.vendors import (
    QuickAssessmentQuestion,
    VendorAttachment,
    VendorContact,
    VendorDocument,
    VendorLink,
    VendorRisk,
)

_RISK_WEIGHT_MAP: Dict[int, str] = {
    0: "N/A",
    1: "Low",
    2: "Medium",
    3: "High",
}

_MAX_LINE_LENGTH = 120
_MAX_SLUG_LENGTH = 40
_MAX_ATTACHMENT_FILENAME_LENGTH = 64

_MARKDOWN_PATTERN = re.compile(
    r"(?m)"
    r"(?:^#{1,6}\s)"        # headings
    r"|(?:\*\*[^*]+\*\*)"   # bold
    r"|(?:^[-*+]\s)"        # unordered list items
    r"|(?:^\d+\.\s)"        # ordered list items
    r"|(?:^>\s)"            # blockquotes
    r"|(?:```)"             # code fences
    r"|(?:\[.+?\]\(.+?\))"  # links
)


def _looks_like_markdown(text: str) -> bool:
    """Detect whether *text* appears to contain Markdown formatting."""
    return bool(_MARKDOWN_PATTERN.search(text))


def _slugify(name: str) -> str:
    """Convert a vendor name to a filesystem-safe slug."""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")[:_MAX_SLUG_LENGTH].rstrip("-")
    return slug


def _as_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _as_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _document_dir_name(file_stem: str, vendor_name: str) -> str:
    slug = _slugify(vendor_name)
    return f"{file_stem}-{slug}" if slug else file_stem


def _truncate_filename(filename: str) -> str:
    if len(filename) <= _MAX_ATTACHMENT_FILENAME_LENGTH:
        return filename

    extension = ""
    stem = filename
    if "." in filename and not filename.startswith("."):
        stem, ext = filename.rsplit(".", 1)
        extension = "." + ext

    digest = hashlib.sha1(filename.encode("utf-8")).hexdigest()[:8]
    keep = _MAX_ATTACHMENT_FILENAME_LENGTH - len(extension) - len(digest) - 1
    if keep < 1:
        return filename[:_MAX_ATTACHMENT_FILENAME_LENGTH]

    return f"{stem[:keep]}-{digest}{extension}"


def _sanitize_attachment_filename(filename: str, index: int) -> str:
    normalized = filename.replace("\\", "/")
    basename = normalized.split("/")[-1]
    basename = re.sub(r"[\x00-\x1f\x7f]+", "", basename).strip()
    basename = re.sub(r"[^A-Za-z0-9._-]+", "-", basename).strip(".-")
    if not basename:
        basename = f"attachment-{index}.bin"
    return _truncate_filename(basename)


def _with_counter(filename: str, counter: int) -> str:
    if "." in filename and not filename.startswith("."):
        stem, ext = filename.rsplit(".", 1)
        return _truncate_filename(f"{stem}-{counter}.{ext}")
    return _truncate_filename(f"{filename}-{counter}")


def _attachment_output_filenames(documents: List[VendorAttachment]) -> List[str]:
    used: Set[str] = set()
    output: List[str] = []
    for index, attachment in enumerate(documents, start=1):
        candidate = _sanitize_attachment_filename(attachment.filename, index)
        if candidate in used:
            counter = 2
            while True:
                numbered = _with_counter(candidate, counter)
                if numbered not in used:
                    candidate = numbered
                    break
                counter += 1
        used.add(candidate)
        output.append(candidate)
    return output


def _format_bullet(text: str, break_long_words: bool = False) -> str:
    return textwrap.fill(
        f"- {text}",
        width=_MAX_LINE_LENGTH,
        subsequent_indent="  ",
        break_long_words=break_long_words,
        break_on_hyphens=False,
    )


def _append_document_link(parts: List[str], filename: str, rel_path: str) -> None:
    line = f"- [{filename}]({rel_path})"
    if len(line) <= _MAX_LINE_LENGTH:
        parts.append(line)
        return
    parts.append(_format_bullet(filename))
    parts.append(
        textwrap.fill(
            f"  path: {rel_path}",
            width=_MAX_LINE_LENGTH,
            subsequent_indent="    ",
            break_long_words=True,
            break_on_hyphens=False,
        )
    )


def _append_hyperlink(parts: List[str], name: str, url: str) -> None:
    line = f"- [{name}]({url})"
    if len(line) <= _MAX_LINE_LENGTH:
        parts.append(line)
        return
    parts.append(_format_bullet(name or "Link"))
    parts.append(
        textwrap.fill(
            f"  url: {url}",
            width=_MAX_LINE_LENGTH,
            subsequent_indent="    ",
            break_long_words=True,
            break_on_hyphens=False,
        )
    )


def _document_title(doc: VendorDocument, file_stem: str) -> str:
    label = doc.code or file_stem
    if doc.name:
        title_with_name = f"{label} — {doc.name}"
        if len(f"# {title_with_name}") <= _MAX_LINE_LENGTH:
            return title_with_name
    return label


class VendorsExporter(BaseExporter):
    def export(self) -> None:
        self._ensure_output_dir()
        self._log("Exporting vendors...")

        response = self.client.list_vendors()
        raw_list: List[Dict[str, Any]] = []
        if isinstance(response, list):
            raw_list = response
        elif isinstance(response, dict):
            # The API may wrap the list in an object
            for key in ("vendorDTOS", "vendors", "content"):
                if key in response and isinstance(response[key], list):
                    raw_list = response[key]
                    break

        documents: List[VendorDocument] = []
        codes: List[str] = []
        for raw in raw_list:
            vendor_id = _as_int(raw.get("id", 0))
            if not vendor_id:
                continue

            detail = self.client.get_vendor(vendor_id)
            risks_raw = self.client.get_vendor_risks(vendor_id)
            hyperlinks_raw = self.client.get_vendor_hyperlinks(vendor_id)
            contacts_raw = self.client.get_vendor_contacts(vendor_id)

            quick_assessment_raw = self._fetch_quick_assessment(detail)

            doc = self._parse_document(
                detail, risks_raw, hyperlinks_raw, contacts_raw, quick_assessment_raw,
            )
            code_number = doc.code.replace("VND-", "") if doc.code.startswith("VND-") else str(doc.id)
            file_stem = f"VND-{code_number}"
            self._export_document(file_stem, doc)
            documents.append(doc)
            codes.append(file_stem)

        self._write_index(documents)

        if codes:
            self._log(
                "Exporting vendors... "
                + ", ".join(codes)
                + f" done ({len(codes)} documents)"
            )
        else:
            self._log("Exporting vendors... done (0 documents)")

    def _fetch_quick_assessment(self, detail: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        assessment_id = _as_int(detail.get("vendorQuickAssessmentId"))
        link_id = _as_int(detail.get("currentAssessmentLinkId"))
        if assessment_id > 0 and link_id > 0:
            return self.client.get_vendor_quick_assessment(assessment_id, link_id)
        return None

    def _parse_document(
        self,
        detail: Dict[str, Any],
        risks_raw: Any,
        hyperlinks_raw: Any,
        contacts_raw: Any,
        quick_assessment_raw: Optional[Dict[str, Any]],
    ) -> VendorDocument:
        raw_id = _as_int(detail.get("id", 0))
        code = str(detail.get("code", "") or "")
        name = str(detail.get("vendorName", "") or "").strip()

        status_obj = detail.get("vendorStatus")
        status = status_obj.get("name", "") if isinstance(status_obj, dict) else ""

        type_obj = detail.get("vendorType")
        vendor_type = type_obj.get("name", "") if isinstance(type_obj, dict) else ""

        contact_obj = detail.get("internalContact")
        owner = contact_obj.get("fullname", "") if isinstance(contact_obj, dict) else ""

        tier_obj = detail.get("vendorTier")
        tier = tier_obj.get("name", "") if isinstance(tier_obj, dict) else ""

        tags: List[str] = []
        for tag in detail.get("tags", []) or []:
            if isinstance(tag, dict):
                tag_name = tag.get("name", "") or tag.get("displayName", "")
                if tag_name:
                    tags.append(str(tag_name))
            elif isinstance(tag, str) and tag:
                tags.append(tag)

        risk_score = _as_float(detail.get("avgRiskScore", 0.0))
        description = str(detail.get("description", "") or "").strip()

        documents = self._parse_attachments(detail.get("documentDTOSet", []))
        hyperlinks = self._parse_hyperlinks(hyperlinks_raw)
        contacts = self._parse_contacts(contacts_raw)
        risks = self._parse_risks(risks_raw)
        quick_assessment = self._parse_quick_assessment(quick_assessment_raw)

        action_items: List[str] = []
        for ai in detail.get("actionItems", []) or []:
            if isinstance(ai, dict):
                ai_code = ai.get("evidenceCode", "") or ai.get("code", "")
                ai_title = ai.get("title", "")
                if ai_code:
                    action_items.append(f"{ai_code}: {ai_title}" if ai_title else str(ai_code))

        return VendorDocument(
            id=raw_id,
            code=code,
            name=name,
            status=status,
            vendor_type=vendor_type,
            owner=owner,
            tier=tier,
            tags=tags,
            risk_score=risk_score,
            description=description,
            documents=documents,
            hyperlinks=hyperlinks,
            contacts=contacts,
            risks=risks,
            quick_assessment=quick_assessment,
            action_items=action_items,
        )

    def _parse_attachments(self, raw: Any) -> List[VendorAttachment]:
        if not isinstance(raw, list):
            return []
        attachments: List[VendorAttachment] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            attachments.append(VendorAttachment(
                id=_as_int(item.get("id", 0)),
                filename=str(item.get("filename", "") or ""),
                signed_url=str(item.get("signedURL", "") or ""),
                created=str(item.get("createdate", "") or ""),
            ))
        return attachments

    def _parse_hyperlinks(self, raw: Any) -> List[VendorLink]:
        if not isinstance(raw, list):
            return []
        links: List[VendorLink] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            links.append(VendorLink(
                id=_as_int(item.get("id", 0)),
                name=str(item.get("name", "") or ""),
                url=str(item.get("hyperLink", "") or ""),
            ))
        return links

    def _parse_contacts(self, raw: Any) -> List[VendorContact]:
        if not isinstance(raw, list):
            return []
        contacts: List[VendorContact] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            contacts.append(VendorContact(
                id=_as_int(item.get("id", 0)),
                name=str(item.get("name", "") or item.get("fullname", "") or ""),
                email=str(item.get("email", "") or ""),
            ))
        return contacts

    def _parse_risks(self, raw: Any) -> List[VendorRisk]:
        if not isinstance(raw, list):
            return []
        risks: List[VendorRisk] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            owner_obj = item.get("userDTO")
            owner = owner_obj.get("fullname", "") if isinstance(owner_obj, dict) else ""

            score_map = item.get("scoreDetailMap", {})
            if not isinstance(score_map, dict):
                score_map = {}

            def _score(key: str) -> Dict[str, Any]:
                s = score_map.get(key, {})
                return s if isinstance(s, dict) else {}

            inherent = _score("inherent")
            current = _score("current")
            target = _score("target")

            risks.append(VendorRisk(
                id=_as_int(item.get("id", 0)),
                code=str(item.get("riskid", "") or ""),
                name=str(item.get("name", "") or ""),
                owner=owner,
                inherent_score=_as_int(inherent.get("score", 0)),
                inherent_level=str(inherent.get("scoreName", "") or ""),
                current_score=_as_int(current.get("score", 0)),
                current_level=str(current.get("scoreName", "") or ""),
                target_score=_as_int(target.get("score", 0)),
                target_level=str(target.get("scoreName", "") or ""),
            ))
        return risks

    def _parse_quick_assessment(self, raw: Optional[Dict[str, Any]]) -> List[QuickAssessmentQuestion]:
        if not isinstance(raw, dict):
            return []
        questions_raw = raw.get("vendorQuestionAnswerDTOList", [])
        if not isinstance(questions_raw, list):
            return []

        questions: List[QuickAssessmentQuestion] = []
        for q in questions_raw:
            if not isinstance(q, dict):
                continue
            code = str(q.get("code", "") or "")
            title = str(q.get("title", "") or "")
            group = str(q.get("groupName", "") or "")

            # Find selected answer text
            selected_id = q.get("selectedAnswerId")
            answer = ""
            for ans in q.get("answersList", []) or []:
                if isinstance(ans, dict) and ans.get("id") == selected_id:
                    answer = str(ans.get("answer", ""))
                    break

            weight = _as_int(q.get("answerWeightage", 0))
            risk_level = _RISK_WEIGHT_MAP.get(weight, "Unknown")

            questions.append(QuickAssessmentQuestion(
                code=code,
                title=title,
                answer=answer,
                risk_level=risk_level,
                group=group,
            ))
        return questions

    def _export_document(self, file_stem: str, doc: VendorDocument) -> None:
        attachment_filenames = _attachment_output_filenames(doc.documents)
        frontmatter = _build_frontmatter(doc, file_stem)
        body = _build_body(doc, file_stem, attachment_filenames)

        md_content = MarkdownFormatter.render(
            title=_document_title(doc, file_stem),
            body=body,
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

        # Download attached documents
        if doc.documents:
            self._download_documents(file_stem, doc, attachment_filenames)

    def _download_documents(self, file_stem: str, doc: VendorDocument, filenames: List[str]) -> None:
        doc_dir_name = _document_dir_name(file_stem, doc.name)
        doc_dir = self.output_dir / "documents" / doc_dir_name
        doc_dir.mkdir(parents=True, exist_ok=True)

        for attachment, output_name in zip(doc.documents, filenames):
            if not attachment.signed_url or not attachment.filename:
                continue
            file_path = doc_dir / output_name
            if not self._should_write(file_path):
                continue
            try:
                data = self.client.download_file(attachment.signed_url)
                with open(file_path, "wb") as f:
                    f.write(data)
                self._log(f"  Downloaded {output_name}")
            except Exception:
                self._log(f"  Warning: failed to download {output_name}")

    def _write_index(self, documents: List[VendorDocument]) -> None:
        frontmatter: Dict[str, Any] = {
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "document_count": len(documents),
        }
        generated_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        body_parts: List[str] = []
        noun = "vendor" if len(documents) == 1 else "vendors"
        body_parts.append(f"{len(documents)} {noun} exported on {generated_date}.")
        body_parts.append("")
        for doc in documents:
            code_number = doc.code.replace("VND-", "") if doc.code.startswith("VND-") else str(doc.id)
            file_stem = f"VND-{code_number}"
            doc_label = doc.code or file_stem
            heading = f"## [{doc_label}]({file_stem}.md) — {doc.name}"
            if doc.name and len(heading) <= _MAX_LINE_LENGTH:
                body_parts.append(heading)
            else:
                body_parts.append(f"## [{doc_label}]({file_stem}.md)")
                if doc.name:
                    body_parts.append("")
                    body_parts.append(_format_bullet(f"**Name:** {doc.name}"))
            body_parts.append("")
            body_parts.append(_format_bullet(f"**Status:** {doc.status}"))
            body_parts.append(_format_bullet(f"**Vendor Type:** {doc.vendor_type}"))
            body_parts.append(_format_bullet(f"**Risk Score:** {doc.risk_score}"))
            body_parts.append(_format_bullet(f"**Tier:** {doc.tier}"))
            body_parts.append(_format_bullet(f"**Risks:** {len(doc.risks)}"))
            body_parts.append(_format_bullet(f"**Action Items:** {len(doc.action_items)}"))
            body_parts.append("")

        md_content = MarkdownFormatter.render(
            title="Vendors",
            body="\n".join(body_parts),
            frontmatter=frontmatter,
        )

        index_path = self.output_dir / "index.md"
        if self._should_write(index_path):
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(md_content)


def _build_frontmatter(doc: VendorDocument, file_stem: str) -> Dict[str, Any]:
    fm: Dict[str, Any] = {
        "id": doc.code or file_stem,
        "title": doc.name,
        "status": doc.status,
        "vendor_type": doc.vendor_type,
        "owner": doc.owner,
        "tier": doc.tier,
        "risk_score": doc.risk_score,
    }
    if doc.tags:
        fm["tags"] = doc.tags
    return fm


def _build_body(doc: VendorDocument, file_stem: str, attachment_filenames: List[str]) -> str:
    parts: List[str] = []

    # == Documents & Links ==
    parts.append("## Documents & Links")
    parts.append("")

    parts.append("### Documents")
    parts.append("")
    if doc.documents:
        doc_dir_name = _document_dir_name(file_stem, doc.name)
        for att, output_name in zip(doc.documents, attachment_filenames):
            rel_path = f"documents/{doc_dir_name}/{output_name}"
            _append_document_link(parts, output_name, rel_path)
    else:
        parts.append("[//]: # (No documents attached)")
    parts.append("")

    parts.append("### Links")
    parts.append("")
    if doc.hyperlinks:
        for link in doc.hyperlinks:
            _append_hyperlink(parts, link.name, link.url)
    else:
        parts.append("[//]: # (No links)")
    parts.append("")

    parts.append("### Notes and Descriptions")
    parts.append("")
    if doc.description:
        if _looks_like_markdown(doc.description):
            parts.append("```markdown")
            parts.append(doc.description)
            parts.append("```")
        else:
            parts.append(textwrap.fill(doc.description, width=_MAX_LINE_LENGTH))
    else:
        parts.append("[//]: # (No notes or descriptions)")
    parts.append("")

    # == Quick Assessment ==
    parts.append("## Quick Assessment")
    parts.append("")
    if doc.quick_assessment:
        for q in doc.quick_assessment:
            parts.append(
                textwrap.fill(
                    f"- **{q.code}:** {q.title} — **{q.answer}** ({q.risk_level})",
                    width=_MAX_LINE_LENGTH,
                    subsequent_indent="  ",
                    break_long_words=False,
                    break_on_hyphens=False,
                )
            )
    else:
        parts.append("[//]: # (No quick assessment data)")
    parts.append("")

    # == Risks & Action Items ==
    parts.append("## Risks & Action Items")
    parts.append("")

    parts.append("### Risks")
    parts.append("")
    if doc.risks:
        for risk in doc.risks:
            parts.append(_format_bullet(
                f"**{risk.code}:** {risk.name} — "
                f"Current: {risk.current_level} ({risk.current_score}), "
                f"Target: {risk.target_level} ({risk.target_score})"
            ))
    else:
        parts.append("[//]: # (No risks)")
    parts.append("")

    parts.append("### Action Items")
    parts.append("")
    if doc.action_items:
        for item in doc.action_items:
            parts.append(_format_bullet(item, break_long_words=True))
    else:
        parts.append("[//]: # (No action items)")

    return "\n".join(parts)
