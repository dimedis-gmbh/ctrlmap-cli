from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from ctrlmap_cli.exporters.risks import RisksExporter


def _make_score(
    likelihood: int = 3,
    likelihood_label: str = "Possible",
    impact: int = 4,
    impact_label: str = "Major",
    score: int = 12,
    score_name: str = "High",
) -> Dict[str, Any]:
    return {
        "likelihood": likelihood,
        "likelihoodLabel": likelihood_label,
        "impact": impact,
        "impactLabel": impact_label,
        "score": score,
        "scoreName": score_name,
    }


def _make_loss_area(
    title: str = "Health & Safety",
    current_id: int = 3,
    target_id: int = 2,
    levels: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    if levels is None:
        levels = [
            {
                "description": "Current level desc",
                "riskLevelDTO": {"id": current_id, "title": "Moderate"},
            },
            {
                "description": "Target level desc",
                "riskLevelDTO": {"id": target_id, "title": "Low"},
            },
        ]
    return {
        "title": title,
        "current": current_id,
        "target": target_id,
        "riskLevelAreaDTOS": levels,
    }


def _make_detail(
    doc_id: int = 32,
    risk_id: str = "RSK-1",
    name: str = " Test Risk ",
    description: str = "Risk description text",
    state: str = "red",
    score_map: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if score_map is None:
        score_map = {
            "inherent": _make_score(4, "Likely", 4, "Major", 16, "High"),
            "current": _make_score(3, "Possible", 3, "Moderate", 9, "Medium"),
            "target": _make_score(2, "Unlikely", 2, "Minor", 4, "Low"),
        }
    return {
        "id": doc_id,
        "riskid": risk_id,
        "name": name,
        "description": description,
        "state": state,
        "status": {"name": "Open"},
        "userDTO": {"fullname": "Jane Owner"},
        "systemLabels": [
            {"displayName": "ISMS"},
            {"displayName": "IT"},
        ],
        "scoreDetailMap": score_map,
        "businessImpact": "Potential data loss",
        "existingControls": "Firewall configured",
        "residualTreatmentPlan": "Implement MFA",
        "controls": [
            {"externalid": "A.8.1", "name": "Endpoint Security"},
        ],
        "actionItems": [
            {"evidenceCode": "AI-60", "title": "Deploy MFA"},
        ],
        "threats": [
            {"code": "T-1", "name": "Phishing"},
        ],
        "vulnerabilities": [
            {"code": "V-1", "name": "Weak passwords"},
        ],
    }


def _make_areas() -> List[Dict[str, Any]]:
    return [_make_loss_area()]


def _setup_client(
    list_response: Any = None,
    detail: Optional[Dict[str, Any]] = None,
    areas: Optional[List[Dict[str, Any]]] = None,
) -> MagicMock:
    client = MagicMock()

    if list_response is None:
        list_response = {"riskDTOS": []}

    client.list_risks.return_value = list_response
    client.get_risk.return_value = detail or {}
    client.get_risk_areas.return_value = areas or []
    return client


class TestRisksExporterEndpoints:
    def test_list_call(self, tmp_path: Path) -> None:
        client = _setup_client()

        RisksExporter(client, tmp_path / "risks").export()

        client.list_risks.assert_called_once()

    def test_fetches_detail_and_areas_per_risk(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response={"riskDTOS": [{"id": 32}]},
            detail=_make_detail(32, "RSK-1"),
            areas=_make_areas(),
        )

        RisksExporter(client, tmp_path / "risks").export()

        client.get_risk.assert_called_once_with(32)
        client.get_risk_areas.assert_called_once_with(32)

    def test_empty_list_creates_index_only(self, tmp_path: Path) -> None:
        client = _setup_client()

        RisksExporter(client, tmp_path / "risks").export()

        assert (tmp_path / "risks" / "index.md").exists()
        assert not list((tmp_path / "risks").glob("RSK-*.md"))

    def test_list_as_plain_list(self, tmp_path: Path) -> None:
        """If API returns a plain list instead of {riskDTOS: [...]}, handle it."""
        client = _setup_client(
            list_response=[{"id": 32}],
            detail=_make_detail(32, "RSK-1"),
        )

        RisksExporter(client, tmp_path / "risks").export()

        assert (tmp_path / "risks" / "RSK-1.md").exists()


class TestRisksExporterOutput:
    def test_default_writes_md_only(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response={"riskDTOS": [{"id": 32}]},
            detail=_make_detail(32, "RSK-1"),
        )

        RisksExporter(client, tmp_path / "risks").export()

        assert (tmp_path / "risks" / "RSK-1.md").exists()
        assert not (tmp_path / "risks" / "RSK-1.json").exists()

    def test_keep_raw_json_writes_json(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response={"riskDTOS": [{"id": 32}]},
            detail=_make_detail(32, "RSK-1"),
        )

        RisksExporter(client, tmp_path / "risks", keep_raw_json=True).export()

        assert (tmp_path / "risks" / "RSK-1.md").exists()
        assert (tmp_path / "risks" / "RSK-1.json").exists()

    def test_no_yaml_output(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response={"riskDTOS": [{"id": 32}]},
            detail=_make_detail(32, "RSK-1"),
        )

        RisksExporter(client, tmp_path / "risks").export()

        assert not list((tmp_path / "risks").glob("*.yaml"))


class TestRisksMarkdownContent:
    def _export_and_read(self, tmp_path: Path, detail: Dict[str, Any],
                         areas: Optional[List[Dict[str, Any]]] = None) -> str:
        client = _setup_client(
            list_response={"riskDTOS": [{"id": detail["id"]}]},
            detail=detail,
            areas=areas or [],
        )
        RisksExporter(client, tmp_path / "risks").export()
        code = detail.get("riskid", "") or f"RSK-{detail['id']}"
        return (tmp_path / "risks" / f"{code}.md").read_text()

    def test_frontmatter_and_title(self, tmp_path: Path) -> None:
        content = self._export_and_read(tmp_path, _make_detail())
        assert content.startswith("---\n")
        assert "# RSK-1 — Test Risk" in content
        assert "id: RSK-1" in content
        assert "status: Open" in content
        assert "owner: Jane Owner" in content
        assert "treatment: Reduce" in content

    def test_frontmatter_tags(self, tmp_path: Path) -> None:
        content = self._export_and_read(tmp_path, _make_detail())
        assert "ISMS" in content
        assert "IT" in content

    def test_frontmatter_score_objects(self, tmp_path: Path) -> None:
        content = self._export_and_read(tmp_path, _make_detail())
        assert "inherent_risk:" in content
        assert "current_risk:" in content
        assert "target_risk:" in content

    def test_description_in_body(self, tmp_path: Path) -> None:
        content = self._export_and_read(tmp_path, _make_detail())
        assert "Risk description text" in content

    def test_assessment_score_table(self, tmp_path: Path) -> None:
        content = self._export_and_read(tmp_path, _make_detail())
        assert "## Assessment & Scoring" in content
        assert "| Inherent" in content
        assert "| Current" in content
        assert "| Target" in content
        assert "Likelihood" in content
        assert "Impact" in content

    def test_business_impact(self, tmp_path: Path) -> None:
        content = self._export_and_read(tmp_path, _make_detail())
        assert "## Impact / Loss Analysis" in content
        assert "### Business Impact" in content
        assert "Potential data loss" in content

    def test_empty_business_impact(self, tmp_path: Path) -> None:
        detail = _make_detail()
        detail["businessImpact"] = ""
        content = self._export_and_read(tmp_path, detail)
        assert "[//]: # (No business impact set)" in content

    def test_loss_analysis(self, tmp_path: Path) -> None:
        content = self._export_and_read(tmp_path, _make_detail(), _make_areas())
        assert "### Loss Analysis" in content
        assert "Health & Safety" in content
        assert "Current: Moderate" in content
        assert "Target: Low" in content

    def test_empty_loss_analysis(self, tmp_path: Path) -> None:
        content = self._export_and_read(tmp_path, _make_detail(), [])
        assert "[//]: # (No loss analysis data)" in content

    def test_treatment_section(self, tmp_path: Path) -> None:
        content = self._export_and_read(tmp_path, _make_detail())
        assert "## Treatment" in content
        assert "**Treatment Option:** Reduce" in content

    def test_existing_controls(self, tmp_path: Path) -> None:
        content = self._export_and_read(tmp_path, _make_detail())
        assert "### Existing Controls" in content
        assert "Firewall configured" in content

    def test_empty_existing_controls(self, tmp_path: Path) -> None:
        detail = _make_detail()
        detail["existingControls"] = ""
        content = self._export_and_read(tmp_path, detail)
        assert "[//]: # (No existing controls set)" in content

    def test_treatment_plan_details(self, tmp_path: Path) -> None:
        content = self._export_and_read(tmp_path, _make_detail())
        assert "### Treatment Plan Details" in content
        assert "Implement MFA" in content

    def test_empty_treatment_plan(self, tmp_path: Path) -> None:
        detail = _make_detail()
        detail["residualTreatmentPlan"] = ""
        content = self._export_and_read(tmp_path, detail)
        assert "[//]: # (No treatment plan details set)" in content

    def test_action_items(self, tmp_path: Path) -> None:
        content = self._export_and_read(tmp_path, _make_detail())
        assert "### Action Items" in content
        assert "AI-60: Deploy MFA" in content

    def test_empty_action_items(self, tmp_path: Path) -> None:
        detail = _make_detail()
        detail["actionItems"] = []
        content = self._export_and_read(tmp_path, detail)
        assert "[//]: # (No action items set)" in content

    def test_mitigating_controls(self, tmp_path: Path) -> None:
        content = self._export_and_read(tmp_path, _make_detail())
        assert "### Mitigating Controls" in content
        assert "A.8.1: Endpoint Security" in content

    def test_empty_controls(self, tmp_path: Path) -> None:
        detail = _make_detail()
        detail["controls"] = []
        content = self._export_and_read(tmp_path, detail)
        assert "[//]: # (No mitigating controls set)" in content

    def test_threats(self, tmp_path: Path) -> None:
        content = self._export_and_read(tmp_path, _make_detail())
        assert "## Threats & Vulnerabilities" in content
        assert "### Threats" in content
        assert "T-1: Phishing" in content

    def test_empty_threats(self, tmp_path: Path) -> None:
        detail = _make_detail()
        detail["threats"] = []
        content = self._export_and_read(tmp_path, detail)
        assert "[//]: # (No threats set)" in content

    def test_vulnerabilities(self, tmp_path: Path) -> None:
        content = self._export_and_read(tmp_path, _make_detail())
        assert "### Vulnerabilities" in content
        assert "V-1: Weak passwords" in content

    def test_empty_vulnerabilities(self, tmp_path: Path) -> None:
        detail = _make_detail()
        detail["vulnerabilities"] = []
        content = self._export_and_read(tmp_path, detail)
        assert "[//]: # (No vulnerabilities set)" in content


class TestRisksTreatmentMapping:
    @pytest.mark.parametrize(
        "state, expected",
        [
            ("act", "Accept"),
            ("red", "Reduce"),
            ("tra", "Transfer"),
            ("avo", "Avoid"),
            ("unknown", "unknown"),
            ("", ""),
        ],
    )
    def test_treatment_mapping(self, state: str, expected: str, tmp_path: Path) -> None:
        detail = _make_detail()
        detail["state"] = state
        client = _setup_client(
            list_response={"riskDTOS": [{"id": 32}]},
            detail=detail,
        )
        RisksExporter(client, tmp_path / "risks").export()
        content = (tmp_path / "risks" / "RSK-1.md").read_text()
        assert f"treatment: {expected}" in content


class TestRisksIndex:
    def test_index_created(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response={"riskDTOS": [{"id": 32}]},
            detail=_make_detail(32, "RSK-1", name=" My Risk "),
        )

        RisksExporter(client, tmp_path / "risks").export()

        index = (tmp_path / "risks" / "index.md").read_text()
        assert "# Risks" in index
        assert "[RSK-1](RSK-1.md)" in index
        assert "My Risk" in index

    def test_index_has_frontmatter(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response={"riskDTOS": [{"id": 32}]},
            detail=_make_detail(32, "RSK-1"),
        )

        RisksExporter(client, tmp_path / "risks").export()

        index = (tmp_path / "risks" / "index.md").read_text()
        assert index.startswith("---\n")
        assert "document_count: 1" in index
        assert "generated:" in index

    def test_index_lists_metadata(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response={"riskDTOS": [{"id": 32}]},
            detail=_make_detail(32, "RSK-1"),
        )

        RisksExporter(client, tmp_path / "risks").export()

        index = (tmp_path / "risks" / "index.md").read_text()
        assert "**Owner:** Jane Owner" in index
        assert "**Status:** Open" in index
        assert "**Treatment:** Reduce" in index
        assert "**Current Risk:**" in index
        assert "**Target Risk:**" in index

    def test_index_contains_summary_line(self, tmp_path: Path) -> None:
        detail1 = _make_detail(32, "RSK-1")
        detail2 = _make_detail(33, "RSK-2", name=" Second Risk ")

        client = MagicMock()
        client.list_risks.return_value = {"riskDTOS": [{"id": 32}, {"id": 33}]}
        client.get_risk.side_effect = lambda rid: detail1 if rid == 32 else detail2
        client.get_risk_areas.return_value = []

        RisksExporter(client, tmp_path / "risks").export()

        index = (tmp_path / "risks" / "index.md").read_text()
        assert "2 risks exported on " in index

    def test_index_singular_noun(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response={"riskDTOS": [{"id": 32}]},
            detail=_make_detail(32, "RSK-1"),
        )

        RisksExporter(client, tmp_path / "risks").export()

        index = (tmp_path / "risks" / "index.md").read_text()
        assert "1 risk exported on " in index


class TestRisksEdgeCases:
    def test_missing_owner(self, tmp_path: Path) -> None:
        detail = _make_detail()
        detail["userDTO"] = None
        client = _setup_client(
            list_response={"riskDTOS": [{"id": 32}]},
            detail=detail,
        )

        RisksExporter(client, tmp_path / "risks", keep_raw_json=True).export()

        parsed = json.loads((tmp_path / "risks" / "RSK-1.json").read_text())
        assert parsed["owner"] == ""

    def test_missing_status(self, tmp_path: Path) -> None:
        detail = _make_detail()
        detail["status"] = None
        client = _setup_client(
            list_response={"riskDTOS": [{"id": 32}]},
            detail=detail,
        )

        RisksExporter(client, tmp_path / "risks").export()

        content = (tmp_path / "risks" / "RSK-1.md").read_text()
        assert "status:" in content

    def test_missing_scores(self, tmp_path: Path) -> None:
        detail = _make_detail()
        detail["scoreDetailMap"] = {}
        client = _setup_client(
            list_response={"riskDTOS": [{"id": 32}]},
            detail=detail,
        )

        RisksExporter(client, tmp_path / "risks").export()

        assert (tmp_path / "risks" / "RSK-1.md").exists()

    def test_fallback_filename_without_code(self, tmp_path: Path) -> None:
        detail = _make_detail(32, "")
        client = _setup_client(
            list_response={"riskDTOS": [{"id": 32}]},
            detail=detail,
        )

        RisksExporter(client, tmp_path / "risks").export()

        assert (tmp_path / "risks" / "RSK-32.md").exists()

    def test_missing_labels(self, tmp_path: Path) -> None:
        detail = _make_detail()
        detail["systemLabels"] = None
        client = _setup_client(
            list_response={"riskDTOS": [{"id": 32}]},
            detail=detail,
        )

        RisksExporter(client, tmp_path / "risks").export()

        assert (tmp_path / "risks" / "RSK-1.md").exists()

    def test_loss_analysis_same_current_and_target(self, tmp_path: Path) -> None:
        """When current == target, show single description without prefix."""
        area = _make_loss_area(
            current_id=3, target_id=3,
            levels=[{
                "description": "Same level desc",
                "riskLevelDTO": {"id": 3, "title": "Moderate"},
            }],
        )
        client = _setup_client(
            list_response={"riskDTOS": [{"id": 32}]},
            detail=_make_detail(),
            areas=[area],
        )

        RisksExporter(client, tmp_path / "risks").export()

        content = (tmp_path / "risks" / "RSK-1.md").read_text()
        assert "Same level desc" in content
        # Should NOT prefix with "Current:" when same level
        lines = content.splitlines()
        desc_lines = [ln for ln in lines if "Same level desc" in ln]
        assert len(desc_lines) == 1
        assert "Current:" not in desc_lines[0]

    def test_frontmatter_control_codes_only(self, tmp_path: Path) -> None:
        """Frontmatter controls should be code-only, not code: name."""
        client = _setup_client(
            list_response={"riskDTOS": [{"id": 32}]},
            detail=_make_detail(),
        )

        RisksExporter(client, tmp_path / "risks").export()

        content = (tmp_path / "risks" / "RSK-1.md").read_text()
        # In frontmatter, controls should be just codes
        # Find frontmatter section
        parts = content.split("---")
        frontmatter = parts[1] if len(parts) >= 3 else ""
        assert "A.8.1" in frontmatter
        # In body, controls should have full name
        body = content.split("---", 2)[2] if len(parts) >= 3 else content
        assert "A.8.1: Endpoint Security" in body


class TestRisksProgress:
    def test_progress_output(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        client = _setup_client(
            list_response={"riskDTOS": [{"id": 32}]},
            detail=_make_detail(32, "RSK-1"),
        )

        RisksExporter(client, tmp_path / "risks").export()

        output = capsys.readouterr().out
        assert "Exporting risks" in output
        assert "RSK-1" in output
        assert "1 documents" in output

    def test_empty_progress(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        client = _setup_client()

        RisksExporter(client, tmp_path / "risks").export()

        assert "0 documents" in capsys.readouterr().out


class TestRisksOverwrite:
    def test_force_overwrites(self, tmp_path: Path) -> None:
        risks = tmp_path / "risks"
        risks.mkdir()
        (risks / "RSK-1.md").write_text("old")

        client = _setup_client(
            list_response={"riskDTOS": [{"id": 32}]},
            detail=_make_detail(32, "RSK-1"),
        )

        RisksExporter(client, risks, force=True).export()

        content = (risks / "RSK-1.md").read_text()
        assert content != "old"
        assert "# RSK-1" in content

    def test_prompt_no_skips(self, tmp_path: Path) -> None:
        risks = tmp_path / "risks"
        risks.mkdir()
        (risks / "RSK-1.md").write_text("old")

        client = _setup_client(
            list_response={"riskDTOS": [{"id": 32}]},
            detail=_make_detail(32, "RSK-1"),
        )

        with patch("builtins.input", return_value="n"):
            RisksExporter(client, risks).export()

        assert (risks / "RSK-1.md").read_text() == "old"

    def test_new_files_no_prompt(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_response={"riskDTOS": [{"id": 32}]},
            detail=_make_detail(32, "RSK-1"),
        )

        with patch("builtins.input") as mock_input:
            RisksExporter(client, tmp_path / "risks").export()

        mock_input.assert_not_called()
        assert (tmp_path / "risks" / "RSK-1.md").exists()
