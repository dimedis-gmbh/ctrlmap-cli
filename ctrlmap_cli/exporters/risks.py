from __future__ import annotations

import textwrap
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List

from ctrlmap_cli.exporters.base import BaseExporter
from ctrlmap_cli.formatters.markdown_formatter import MarkdownFormatter
from ctrlmap_cli.models.risks import (
    LossAnalysisArea,
    RiskDocument,
    RiskScore,
)

_TREATMENT_MAP: Dict[str, str] = {
    "act": "Accept",
    "red": "Reduce",
    "tra": "Transfer",
    "avo": "Avoid",
}

_EMPTY_SCORE = RiskScore(
    likelihood=0, likelihood_label="", impact=0, impact_label="", score=0, level="",
)


class RisksExporter(BaseExporter):
    def export(self) -> None:
        self._ensure_output_dir()
        self._log("Exporting risks...")

        response = self.client.list_risks()
        raw_list: List[Dict[str, Any]] = []
        if isinstance(response, dict):
            raw_list = response.get("riskDTOS", [])
        elif isinstance(response, list):
            raw_list = response

        documents: List[RiskDocument] = []
        codes: List[str] = []
        for raw in raw_list:
            doc_id = _as_int(raw.get("id", 0))
            detail = self.client.get_risk(doc_id)
            areas_raw = self.client.get_risk_areas(doc_id)

            doc = self._parse_document(detail, areas_raw)
            file_stem = doc.code or f"RSK-{doc.id}"
            self._export_document(file_stem, doc)
            documents.append(doc)
            codes.append(file_stem)

        self._write_index(documents)

        if codes:
            self._log(
                "Exporting risks... "
                + ", ".join(codes)
                + f" done ({len(codes)} documents)"
            )
        else:
            self._log("Exporting risks... done (0 documents)")

    def _parse_document(
        self,
        detail: Dict[str, Any],
        areas_raw: Any,
    ) -> RiskDocument:
        raw_id = detail.get("id", 0)
        item_id = raw_id if isinstance(raw_id, int) else 0

        status_obj = detail.get("status")
        status = status_obj.get("name", "") if isinstance(status_obj, dict) else ""

        owner_obj = detail.get("userDTO")
        owner = owner_obj.get("fullname", "") if isinstance(owner_obj, dict) else ""

        state = str(detail.get("state") or "")
        treatment = _TREATMENT_MAP.get(state, state)

        tags: List[str] = []
        for label in detail.get("systemLabels", []) or []:
            if isinstance(label, dict):
                name = label.get("displayName", "")
                if name:
                    tags.append(name)

        score_map = detail.get("scoreDetailMap", {})
        inherent_risk = _parse_score(score_map.get("inherent"))
        current_risk = _parse_score(score_map.get("current"))
        target_risk = _parse_score(score_map.get("target"))

        controls: List[str] = []
        for ctrl in detail.get("controls", []) or []:
            if isinstance(ctrl, dict):
                ext_id = ctrl.get("externalid", "")
                name = ctrl.get("name", "")
                if ext_id:
                    controls.append(f"{ext_id}: {name}" if name else ext_id)

        action_items: List[str] = []
        for ai in detail.get("actionItems", []) or []:
            if isinstance(ai, dict):
                code = ai.get("evidenceCode", "")
                title = ai.get("title", "")
                if code:
                    action_items.append(f"{code}: {title}" if title else code)

        threats: List[str] = []
        for t in detail.get("threats", []) or []:
            if isinstance(t, dict):
                code = t.get("code", "")
                name = t.get("name", "")
                if code:
                    threats.append(f"{code}: {name}" if name else code)

        vulnerabilities: List[str] = []
        for v in detail.get("vulnerabilities", []) or []:
            if isinstance(v, dict):
                code = v.get("code", "")
                name = str(v.get("name", "")).strip()
                if code:
                    vulnerabilities.append(f"{code}: {name}" if name else code)

        loss_analysis = _parse_loss_analysis(areas_raw)

        return RiskDocument(
            id=item_id,
            code=str(detail.get("riskid", "") or ""),
            title=str(detail.get("name", "")).strip(),
            description=str(detail.get("description", "") or ""),
            status=status,
            owner=owner,
            treatment=treatment,
            tags=tags,
            inherent_risk=inherent_risk,
            current_risk=current_risk,
            target_risk=target_risk,
            business_impact=str(detail.get("businessImpact", "") or ""),
            existing_controls=str(detail.get("existingControls", "") or ""),
            treatment_plan=str(detail.get("residualTreatmentPlan", "") or ""),
            controls=controls,
            action_items=action_items,
            threats=threats,
            vulnerabilities=vulnerabilities,
            loss_analysis=loss_analysis,
        )

    def _export_document(self, file_stem: str, doc: RiskDocument) -> None:
        frontmatter = _build_frontmatter(doc, file_stem)
        body = _build_body(doc, file_stem)

        md_content = MarkdownFormatter.render(
            title=f"{doc.code or file_stem} — {doc.title}",
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

    def _write_index(self, documents: List[RiskDocument]) -> None:
        frontmatter: Dict[str, Any] = {
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "document_count": len(documents),
        }
        generated_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        body_parts: List[str] = []
        noun = "risk" if len(documents) == 1 else "risks"
        body_parts.append(f"{len(documents)} {noun} exported on {generated_date}.")
        body_parts.append("")
        for doc in documents:
            file_stem = doc.code or f"RSK-{doc.id}"
            doc_label = doc.code or file_stem
            body_parts.append(f"## [{doc_label}]({file_stem}.md) — {doc.title}")
            body_parts.append("")
            body_parts.append(f"- **Owner:** {doc.owner}")
            body_parts.append(f"- **Status:** {doc.status}")
            body_parts.append(f"- **Treatment:** {doc.treatment}")
            cr = doc.current_risk
            body_parts.append(f"- **Current Risk:** {cr.score} — {cr.level}")
            tr = doc.target_risk
            body_parts.append(f"- **Target Risk:** {tr.score} — {tr.level}")
            body_parts.append("")

        md_content = MarkdownFormatter.render(
            title="Risks",
            body="\n".join(body_parts),
            frontmatter=frontmatter,
        )

        index_path = self.output_dir / "index.md"
        if self._should_write(index_path):
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(md_content)


def _parse_score(data: Any) -> RiskScore:
    if not isinstance(data, dict):
        return RiskScore(
            likelihood=0, likelihood_label="",
            impact=0, impact_label="",
            score=0, level="",
        )
    return RiskScore(
        likelihood=_as_int(data.get("likelihood", 0)),
        likelihood_label=str(data.get("likelihoodLabel", "") or ""),
        impact=_as_int(data.get("impact", 0)),
        impact_label=str(data.get("impactLabel", "") or ""),
        score=_as_int(data.get("score", 0)),
        level=str(data.get("scoreName", "") or ""),
    )


def _parse_loss_analysis(areas_raw: Any) -> List[LossAnalysisArea]:
    if not isinstance(areas_raw, list):
        return []

    areas: List[LossAnalysisArea] = []
    for area in areas_raw:
        if not isinstance(area, dict):
            continue
        title = str(area.get("title", ""))
        current_id = _as_int(area.get("current", 0))
        target_id = _as_int(area.get("target", 0))

        levels = area.get("riskLevelAreaDTOS", [])
        if not isinstance(levels, list):
            levels = []

        level_map: Dict[int, str] = {}
        for level in levels:
            if isinstance(level, dict):
                rl = level.get("riskLevelDTO", {})
                if isinstance(rl, dict):
                    level_map[_as_int(rl.get("id", 0))] = str(level.get("description", ""))

        # Map level IDs to risk level names
        level_name_map: Dict[int, str] = {}
        for level in levels:
            if isinstance(level, dict):
                rl = level.get("riskLevelDTO", {})
                if isinstance(rl, dict):
                    level_name_map[_as_int(rl.get("id", 0))] = str(rl.get("title", ""))

        areas.append(LossAnalysisArea(
            area=title,
            current_level=level_name_map.get(current_id, ""),
            target_level=level_name_map.get(target_id, ""),
            current_description=level_map.get(current_id, ""),
            target_description=level_map.get(target_id, ""),
        ))
    return areas


def _build_frontmatter(doc: RiskDocument, file_stem: str) -> Dict[str, Any]:
    def _score_dict(s: RiskScore) -> Dict[str, Any]:
        return {
            "likelihood": s.likelihood,
            "likelihood_label": s.likelihood_label,
            "impact": s.impact,
            "impact_label": s.impact_label,
            "score": s.score,
            "level": s.level,
        }

    control_codes: List[str] = []
    for c in doc.controls:
        code = c.split(":")[0].strip() if ":" in c else c
        control_codes.append(code)

    return {
        "id": doc.code or file_stem,
        "title": doc.title,
        "status": doc.status,
        "owner": doc.owner,
        "treatment": doc.treatment,
        "tags": doc.tags,
        "inherent_risk": _score_dict(doc.inherent_risk),
        "current_risk": _score_dict(doc.current_risk),
        "target_risk": _score_dict(doc.target_risk),
        "controls": control_codes,
    }


def _build_body(doc: RiskDocument, file_stem: str) -> str:
    parts: List[str] = []

    # Description
    if doc.description:
        parts.append(_wrap_text(doc.description))
    parts.append("")

    # Assessment & Scoring
    parts.append("## Assessment & Scoring")
    parts.append("")
    parts.append(_build_score_table(doc))
    parts.append("")

    # Impact / Loss Analysis
    parts.append("## Impact / Loss Analysis")
    parts.append("")
    parts.append("### Business Impact")
    parts.append("")
    if doc.business_impact:
        parts.append(_format_text_as_bullets(doc.business_impact))
    else:
        parts.append("[//]: # (No business impact set)")
    parts.append("")

    parts.append("### Loss Analysis")
    parts.append("")
    if doc.loss_analysis:
        parts.append(_build_loss_analysis(doc.loss_analysis))
    else:
        parts.append("[//]: # (No loss analysis data)")
    parts.append("")

    # Treatment
    parts.append("## Treatment")
    parts.append("")
    parts.append(f"- **Treatment Option:** {doc.treatment}")
    parts.append("")

    parts.append("### Existing Controls")
    parts.append("")
    if doc.existing_controls:
        parts.append(_format_text_as_bullets(doc.existing_controls))
    else:
        parts.append("[//]: # (No existing controls set)")
    parts.append("")

    parts.append("### Treatment Plan Details")
    parts.append("")
    if doc.treatment_plan:
        parts.append(_wrap_text(doc.treatment_plan))
    else:
        parts.append("[//]: # (No treatment plan details set)")
    parts.append("")

    parts.append("### Action Items")
    parts.append("")
    if doc.action_items:
        for item in doc.action_items:
            parts.append(f"- {item}")
    else:
        parts.append("[//]: # (No action items set)")
    parts.append("")

    parts.append("### Mitigating Controls")
    parts.append("")
    if doc.controls:
        for ctrl in doc.controls:
            parts.append(f"- {ctrl}")
    else:
        parts.append("[//]: # (No mitigating controls set)")
    parts.append("")

    # Threats & Vulnerabilities
    parts.append("## Threats & Vulnerabilities")
    parts.append("")
    parts.append("### Threats")
    parts.append("")
    if doc.threats:
        for t in doc.threats:
            parts.append(f"- {t}")
    else:
        parts.append("[//]: # (No threats set)")
    parts.append("")

    parts.append("### Vulnerabilities")
    parts.append("")
    if doc.vulnerabilities:
        for v in doc.vulnerabilities:
            parts.append(f"- {v}")
    else:
        parts.append("[//]: # (No vulnerabilities set)")

    return "\n".join(parts)


def _build_score_table(doc: RiskDocument) -> str:
    def _row(label: str, s: RiskScore) -> str:
        lh = f"{s.likelihood_label} ({s.likelihood})" if s.likelihood_label else str(s.likelihood)
        im = f"{s.impact_label} ({s.impact})" if s.impact_label else str(s.impact)
        return (
            f"| {label:<9} "
            f"| {lh:<19} "
            f"| {im:<19} "
            f"| {s.score:>5} "
            f"| {s.level:<13} |"
        )

    lines = [
        "|           | Likelihood          | Impact              | Score | Level         |",
        "|-----------|---------------------|---------------------|------:|---------------|",
        _row("Inherent", doc.inherent_risk),
        _row("Current", doc.current_risk),
        _row("Target", doc.target_risk),
    ]
    return "\n".join(lines)


def _build_loss_analysis(areas: List[LossAnalysisArea]) -> str:
    parts: List[str] = []
    for area in areas:
        parts.append(
            f"- **{area.area}** — Current: {area.current_level}, "
            f"Target: {area.target_level}"
        )
        if area.current_level == area.target_level:
            if area.current_description:
                parts.append(f"  - {area.current_description}")
        else:
            if area.current_description:
                parts.append(f"  - Current: {area.current_description}")
            if area.target_description:
                parts.append(f"  - Target: {area.target_description}")
    return "\n".join(parts)


def _wrap_text(text: str) -> str:
    return textwrap.fill(text.strip(), width=120)


def _format_text_as_bullets(text: str) -> str:
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    parts: List[str] = []
    for line in lines:
        # Strip leading "- " if already present
        if line.startswith("- "):
            line = line[2:]
        wrapped = textwrap.fill(line, width=118, initial_indent="- ", subsequent_indent="  ")
        parts.append(wrapped)
    return "\n".join(parts)


def _as_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0
