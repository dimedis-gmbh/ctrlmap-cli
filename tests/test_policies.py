from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch
from urllib.parse import quote

import pytest

from ctrlmap_cli.exporters.policies import PoliciesExporter


def _double_encode(html: str) -> str:
    return quote(quote(html, safe=""), safe="")


def _make_list_item(doc_id: int = 10, code: str = "POL-4") -> Dict[str, Any]:
    return {"id": doc_id, "policyCode": code}


def _make_section(
    section_id: int = 1,
    title: str = "Section Title",
    html_body: str = "<h3>Heading</h3><p>Paragraph.</p>",
) -> Dict[str, Any]:
    return {
        "id": section_id,
        "title": title,
        "description": _double_encode(html_body),
    }


def _make_detail(
    doc_id: int = 10,
    code: str = "POL-4",
    name: str = " Test Policy ",
    sections: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    if sections is None:
        sections = [_make_section(1, "Section One")]
    return {
        "id": doc_id,
        "policyCode": code,
        "name": name,
        "status": {"name": "Approved"},
        "majorVersion": 2,
        "minorVersion": 0,
        "owner": {"fullname": "Jane Owner"},
        "approver": {"fullname": "John Approver"},
        "policyContributors": [{"fullname": "Alice Contrib"}],
        "dataClassification": "Intern",
        "reviewDate": "2027-06-15",
        "updatedate": "2026-03-01T10:00:00Z",
        "sections": sections,
        "controls": [{"controlCode": "A.5.1"}],
        "requirements": [{"requirementCode": "ISO-1"}],
    }


def _setup_client(
    list_items: List[Dict[str, Any]],
    details: Dict[int, Dict[str, Any]],
) -> MagicMock:
    client = MagicMock()

    client.list_policies.return_value = list_items

    def fake_get_policy(policy_id: int) -> Any:
        return details.get(policy_id, {})

    client.get_policy.side_effect = fake_get_policy
    return client


class TestPoliciesExporterEndpoints:
    def test_list_call_uses_post_with_policy_filter(self, tmp_path: Path) -> None:
        client = _setup_client(list_items=[], details={})

        PoliciesExporter(client, tmp_path / "pols").export()

        client.list_policies.assert_called_once_with()

    def test_fetches_detail_per_document(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_items=[_make_list_item(10, "POL-4")],
            details={10: _make_detail(10, "POL-4")},
        )

        PoliciesExporter(client, tmp_path / "pols").export()

        client.list_policies.assert_called_once_with()
        client.get_policy.assert_called_once_with(10)

    def test_empty_list_creates_index_only(self, tmp_path: Path) -> None:
        client = _setup_client([], {})

        PoliciesExporter(client, tmp_path / "pols").export()

        assert (tmp_path / "pols" / "index.md").exists()
        assert not list((tmp_path / "pols").glob("POL-*.md"))


class TestPoliciesExporterOutput:
    def test_default_writes_md_only(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: _make_detail(10, "POL-4")},
        )

        PoliciesExporter(client, tmp_path / "pols").export()

        assert (tmp_path / "pols" / "POL-4.md").exists()
        assert not (tmp_path / "pols" / "POL-4.json").exists()

    def test_keep_raw_json_writes_json(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: _make_detail(10, "POL-4")},
        )

        PoliciesExporter(client, tmp_path / "pols", keep_raw_json=True).export()

        assert (tmp_path / "pols" / "POL-4.md").exists()
        assert (tmp_path / "pols" / "POL-4.json").exists()

    def test_markdown_has_frontmatter_and_title(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: _make_detail(10, "POL-4", name=" My Policy ")},
        )

        PoliciesExporter(client, tmp_path / "pols").export()

        content = (tmp_path / "pols" / "POL-4.md").read_text()
        assert content.startswith("---\n")
        assert "# POL-4 — My Policy" in content
        assert "id: POL-4" in content
        assert "status: Approved" in content
        assert "version: '2.0'" in content or 'version: "2.0"' in content

    def test_frontmatter_includes_owner_and_approver(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: _make_detail(10, "POL-4")},
        )

        PoliciesExporter(client, tmp_path / "pols").export()

        content = (tmp_path / "pols" / "POL-4.md").read_text()
        assert "owner: Jane Owner" in content
        assert "approver: John Approver" in content

    def test_frontmatter_includes_contributors(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: _make_detail(10, "POL-4")},
        )

        PoliciesExporter(client, tmp_path / "pols").export()

        content = (tmp_path / "pols" / "POL-4.md").read_text()
        assert "Alice Contrib" in content

    def test_frontmatter_includes_classification(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: _make_detail(10, "POL-4")},
        )

        PoliciesExporter(client, tmp_path / "pols").export()

        content = (tmp_path / "pols" / "POL-4.md").read_text()
        assert "classification: Intern" in content

    def test_frontmatter_includes_review_date(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: _make_detail(10, "POL-4")},
        )

        PoliciesExporter(client, tmp_path / "pols").export()

        content = (tmp_path / "pols" / "POL-4.md").read_text()
        assert "review_date: '2027-06-15'" in content or 'review_date: "2027-06-15"' in content

    def test_markdown_body_is_converted_from_html(self, tmp_path: Path) -> None:
        section = _make_section(1, "Section One", "<h3>Topic</h3><p>Content.</p>")
        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: _make_detail(10, "POL-4", sections=[section])},
        )

        PoliciesExporter(client, tmp_path / "pols").export()

        content = (tmp_path / "pols" / "POL-4.md").read_text()
        assert "Content." in content
        assert "<h3>" not in content
        assert "<p>" not in content
        assert "%25" not in content

    def test_json_includes_all_fields(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: _make_detail(10, "POL-4")},
        )

        PoliciesExporter(client, tmp_path / "pols", keep_raw_json=True).export()

        parsed = json.loads((tmp_path / "pols" / "POL-4.json").read_text())
        assert parsed["code"] == "POL-4"
        assert parsed["version"] == "2.0"
        assert parsed["owner"] == "Jane Owner"
        assert "body_html" in parsed
        assert "body_markdown" in parsed
        assert "sections" in parsed
        assert parsed["controls"] == ["A.5.1"]
        assert parsed["requirements"] == ["ISO-1"]


class TestPoliciesSections:
    def test_multi_section_has_h2_titles(self, tmp_path: Path) -> None:
        sections = [
            _make_section(1, "Scope", "<p>Scope content.</p>"),
            _make_section(2, "Purpose", "<p>Purpose content.</p>"),
        ]
        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: _make_detail(10, "POL-4", sections=sections)},
        )

        PoliciesExporter(client, tmp_path / "pols").export()

        content = (tmp_path / "pols" / "POL-4.md").read_text()
        assert "## Scope" in content
        assert "## Purpose" in content
        assert "Scope content." in content
        assert "Purpose content." in content

    def test_single_section_matching_name_no_h2_title(self, tmp_path: Path) -> None:
        """When a single section title equals policy name, skip the section h2."""
        sections = [
            _make_section(1, "Test Policy", "<h3>1. Zweck</h3><p>Purpose.</p>"),
        ]
        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: _make_detail(10, "POL-4", name="Test Policy", sections=sections)},
        )

        PoliciesExporter(client, tmp_path / "pols").export()

        content = (tmp_path / "pols" / "POL-4.md").read_text()
        # Should have h2 from normalized heading, not an extra "## Test Policy"
        assert "## 1. Zweck" in content
        assert "Purpose." in content
        # No duplicate section title
        lines = content.splitlines()
        h2_lines = [ln for ln in lines if ln.startswith("## ")]
        assert not any("Test Policy" in ln for ln in h2_lines)

    def test_multi_section_heading_normalization(self, tmp_path: Path) -> None:
        """Content headings within multi-section should start at h3."""
        sections = [
            _make_section(1, "Scope", "<h4>Sub topic</h4><p>Details.</p>"),
        ]
        detail = _make_detail(10, "POL-4", sections=sections)
        # Add a second section so it's multi-section
        sections.append(_make_section(2, "Purpose", "<p>More.</p>"))
        detail["sections"] = [
            {"id": 1, "title": "Scope", "description": _double_encode("<h4>Sub topic</h4><p>Details.</p>")},
            {"id": 2, "title": "Purpose", "description": _double_encode("<p>More.</p>")},
        ]
        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: detail},
        )

        PoliciesExporter(client, tmp_path / "pols").export()

        content = (tmp_path / "pols" / "POL-4.md").read_text()
        assert "## Scope" in content
        assert "### Sub topic" in content

    def test_empty_sections(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: _make_detail(10, "POL-4", sections=[])},
        )

        PoliciesExporter(client, tmp_path / "pols").export()

        content = (tmp_path / "pols" / "POL-4.md").read_text()
        assert "# POL-4" in content


class TestPoliciesIndex:
    def test_index_created(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: _make_detail(10, "POL-4", name=" My Policy ")},
        )

        PoliciesExporter(client, tmp_path / "pols").export()

        index = (tmp_path / "pols" / "index.md").read_text()
        assert "# Policies" in index
        assert "[POL-4](POL-4.md)" in index
        assert "My Policy" in index

    def test_index_has_frontmatter(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: _make_detail(10, "POL-4")},
        )

        PoliciesExporter(client, tmp_path / "pols").export()

        index = (tmp_path / "pols" / "index.md").read_text()
        assert index.startswith("---\n")
        assert "document_count: 1" in index
        assert "generated:" in index

    def test_index_lists_metadata(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: _make_detail(10, "POL-4")},
        )

        PoliciesExporter(client, tmp_path / "pols").export()

        index = (tmp_path / "pols" / "index.md").read_text()
        assert "**Owner:** Jane Owner" in index
        assert "**Status:** Approved" in index
        assert "**Classification:** Intern" in index
        assert "**Review Date:** 2027-06-15" in index

    def test_index_contains_summary_line(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(10, "POL-4"), _make_list_item(11, "POL-5")],
            {
                10: _make_detail(10, "POL-4"),
                11: _make_detail(11, "POL-5"),
            },
        )

        PoliciesExporter(client, tmp_path / "pols").export()

        index = (tmp_path / "pols" / "index.md").read_text()
        assert "2 policies exported on " in index

    def test_index_multiple_documents(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(10, "POL-4"), _make_list_item(11, "POL-5")],
            {
                10: _make_detail(10, "POL-4", name=" First "),
                11: _make_detail(11, "POL-5", name=" Second "),
            },
        )

        PoliciesExporter(client, tmp_path / "pols").export()

        index = (tmp_path / "pols" / "index.md").read_text()
        assert "document_count: 2" in index
        assert "[POL-4](POL-4.md) — First" in index
        assert "[POL-5](POL-5.md) — Second" in index

    def test_index_contains_all_policy_codes_as_links(self, tmp_path: Path) -> None:
        items = [_make_list_item(i, f"POL-{i}") for i in range(1, 4)]
        details = {i: _make_detail(i, f"POL-{i}") for i in range(1, 4)}
        client = _setup_client(items, details)

        PoliciesExporter(client, tmp_path / "pols").export()

        index = (tmp_path / "pols" / "index.md").read_text()
        for i in range(1, 4):
            assert f"[POL-{i}](POL-{i}.md)" in index


class TestPoliciesProgress:
    def test_progress_output(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        client = _setup_client(
            [_make_list_item(10, "POL-4"), _make_list_item(11, "POL-5")],
            {
                10: _make_detail(10, "POL-4"),
                11: _make_detail(11, "POL-5"),
            },
        )

        PoliciesExporter(client, tmp_path / "pols").export()

        output = capsys.readouterr().out
        assert "Exporting policies" in output
        assert "POL-4" in output
        assert "POL-5" in output
        assert "2 documents" in output

    def test_empty_list_progress(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        client = _setup_client([], {})

        PoliciesExporter(client, tmp_path / "pols").export()

        assert "0 documents" in capsys.readouterr().out


class TestPoliciesEdgeCases:
    def test_missing_owner_and_approver(self, tmp_path: Path) -> None:
        detail = _make_detail(10, "POL-4")
        detail["owner"] = None
        detail["approver"] = None
        detail["policyContributors"] = []

        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: detail},
        )

        PoliciesExporter(client, tmp_path / "pols", keep_raw_json=True).export()

        parsed = json.loads((tmp_path / "pols" / "POL-4.json").read_text())
        assert parsed["owner"] == ""
        assert parsed["approver"] == ""
        assert parsed["contributors"] == []

    def test_missing_version_fields(self, tmp_path: Path) -> None:
        detail = _make_detail(10, "POL-4")
        del detail["majorVersion"]
        del detail["minorVersion"]

        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: detail},
        )

        PoliciesExporter(client, tmp_path / "pols", keep_raw_json=True).export()

        parsed = json.loads((tmp_path / "pols" / "POL-4.json").read_text())
        assert parsed["version"] == "0.0"

    def test_empty_description_in_section(self, tmp_path: Path) -> None:
        section = {"id": 1, "title": "Empty", "description": ""}
        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: _make_detail(10, "POL-4", sections=[section])},
        )

        PoliciesExporter(client, tmp_path / "pols").export()

        assert (tmp_path / "pols" / "POL-4.md").exists()

    def test_fallback_filename_without_code(self, tmp_path: Path) -> None:
        detail = _make_detail(10, "", name="Unnamed Policy")
        client = _setup_client(
            [_make_list_item(10, "")],
            {10: detail},
        )

        PoliciesExporter(client, tmp_path / "pols").export()

        assert (tmp_path / "pols" / "POL-10.md").exists()

    def test_updated_date_truncated_to_date_only(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: _make_detail(10, "POL-4")},
        )

        PoliciesExporter(client, tmp_path / "pols").export()

        content = (tmp_path / "pols" / "POL-4.md").read_text()
        assert "updated: '2026-03-01'" in content or 'updated: "2026-03-01"' in content


class TestPoliciesOverwrite:
    def test_force_overwrites_without_prompt(self, tmp_path: Path) -> None:
        pols = tmp_path / "pols"
        pols.mkdir()
        (pols / "POL-4.md").write_text("old content")

        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: _make_detail(10, "POL-4")},
        )

        PoliciesExporter(client, pols, force=True).export()

        content = (pols / "POL-4.md").read_text()
        assert content != "old content"
        assert "# POL-4" in content

    def test_prompt_no_skips_file(self, tmp_path: Path) -> None:
        pols = tmp_path / "pols"
        pols.mkdir()
        (pols / "POL-4.md").write_text("old content")

        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: _make_detail(10, "POL-4")},
        )

        with patch("builtins.input", return_value="n"):
            PoliciesExporter(client, pols).export()

        assert (pols / "POL-4.md").read_text() == "old content"

    def test_new_files_written_without_prompt(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: _make_detail(10, "POL-4")},
        )

        with patch("builtins.input") as mock_input:
            PoliciesExporter(client, tmp_path / "pols").export()

        mock_input.assert_not_called()
        assert (tmp_path / "pols" / "POL-4.md").exists()

    def test_index_respects_should_write(self, tmp_path: Path) -> None:
        pols = tmp_path / "pols"
        pols.mkdir()
        (pols / "index.md").write_text("old index")

        client = _setup_client(
            [_make_list_item(10, "POL-4")],
            {10: _make_detail(10, "POL-4")},
        )

        with patch("builtins.input", return_value="n"):
            PoliciesExporter(client, pols).export()

        assert (pols / "index.md").read_text() == "old index"
