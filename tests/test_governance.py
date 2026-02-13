from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch
from urllib.parse import quote

import pytest

from ctrlmap_cli.exporters.governance import GovernanceExporter


def _double_encode(html: str) -> str:
    """Mimic the ControlMap double-URL-encoding."""
    return quote(quote(html, safe=""), safe="")


def _make_list_item(doc_id: int = 37, code: str = "GOV-1") -> Dict[str, Any]:
    """Minimal item as returned by the list endpoint."""
    return {"id": doc_id, "procedureCode": code}


def _make_detail(
    doc_id: int = 37,
    code: str = "GOV-1",
    name: str = " Test Title ",
    html_body: str = "<h3>Heading</h3><p>Paragraph.</p>",
) -> Dict[str, Any]:
    return {
        "id": doc_id,
        "procedureCode": code,
        "name": name,
        "description": _double_encode(html_body),
        "status": {"name": "Approved"},
        "majorVersion": 1,
        "minorVersion": 2,
        "owner": {"fullname": "Jane Owner"},
        "approver": {"fullname": "John Approver"},
        "contributors": [{"fullname": "Alice Contrib"}],
        "classification": "Intern",
        "reviewDate": "2027-01-07",
        "updatedate": "2026-01-07",
    }


def _make_controls() -> List[Dict[str, Any]]:
    return [{"controlCode": "A.5.1"}, {"controlCode": "A.6.2"}]


def _make_requirements() -> List[Dict[str, Any]]:
    return [{"requirementCode": "ISO-1"}, {"requirementCode": "ISO-2"}]


def _setup_client(
    list_items: List[Dict[str, Any]],
    details: Dict[int, Dict[str, Any]],
    controls: Dict[int, List[Dict[str, Any]]],
    requirements: Dict[int, List[Dict[str, Any]]],
) -> MagicMock:
    """Create a mock client that returns different data per endpoint."""
    client = MagicMock()

    def fake_post(path: str, json: Any = None) -> Any:
        if path == "/procedures":
            return list_items
        return []

    def fake_get(path: str, params: Any = None) -> Any:
        for doc_id, detail in details.items():
            if path == f"/procedure/{doc_id}":
                return detail
            if path == f"/procedure/{doc_id}/controls":
                return controls.get(doc_id, [])
            if path == f"/procedure/{doc_id}/requirements":
                return requirements.get(doc_id, [])
        return []

    client.post.side_effect = fake_post
    client.get.side_effect = fake_get
    return client


class TestGovernanceExporterEndpoints:
    def test_list_call_uses_post_with_governance_filter(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_items=[],
            details={},
            controls={},
            requirements={},
        )

        GovernanceExporter(client, tmp_path / "govs").export()

        call_args = client.post.call_args
        assert call_args[0][0] == "/procedures"
        body = call_args[1]["json"]
        assert body["startpos"] == 0
        assert body["pagesize"] == 500
        assert body["sortby"] is None
        assert body["rules"][0]["field"] == "type"
        assert body["rules"][0]["value"] == "governance"

    def test_fetches_list_then_detail_per_document(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_items=[_make_list_item(37, "GOV-1")],
            details={37: _make_detail(37, "GOV-1")},
            controls={37: []},
            requirements={37: []},
        )

        GovernanceExporter(client, tmp_path / "govs").export()

        assert client.post.call_count == 1
        paths_called = [c.args[0] for c in client.get.call_args_list]
        assert "/procedure/37" in paths_called
        assert "/procedure/37/controls" in paths_called
        assert "/procedure/37/requirements" in paths_called

    def test_empty_list_creates_index_only(self, tmp_path: Path) -> None:
        client = _setup_client([], {}, {}, {})

        GovernanceExporter(client, tmp_path / "govs").export()

        assert (tmp_path / "govs" / "index.md").exists()
        assert not list((tmp_path / "govs").glob("GOV-*.md"))


class TestGovernanceExporterOutput:
    def test_default_writes_md_only(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(37, "GOV-1")],
            {37: _make_detail(37, "GOV-1")},
            {37: []},
            {37: []},
        )

        GovernanceExporter(client, tmp_path / "govs").export()

        assert (tmp_path / "govs" / "GOV-1.md").exists()
        assert not (tmp_path / "govs" / "GOV-1.json").exists()
        assert not (tmp_path / "govs" / "GOV-1.yaml").exists()

    def test_keep_raw_json_writes_json(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(37, "GOV-1")],
            {37: _make_detail(37, "GOV-1")},
            {37: []},
            {37: []},
        )

        GovernanceExporter(client, tmp_path / "govs", keep_raw_json=True).export()

        assert (tmp_path / "govs" / "GOV-1.md").exists()
        assert (tmp_path / "govs" / "GOV-1.json").exists()
        assert not (tmp_path / "govs" / "GOV-1.yaml").exists()

    def test_markdown_has_frontmatter_and_title(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(37, "GOV-1")],
            {37: _make_detail(37, "GOV-1", name=" My Gov Doc ")},
            {37: []},
            {37: []},
        )

        GovernanceExporter(client, tmp_path / "govs").export()

        content = (tmp_path / "govs" / "GOV-1.md").read_text()
        assert content.startswith("---\n")
        assert "# GOV-1 — My Gov Doc" in content
        assert "id: GOV-1" in content
        assert "status: Approved" in content
        assert "version: '1.2'" in content or "version: \"1.2\"" in content

    def test_markdown_body_is_converted_from_html(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(37, "GOV-1")],
            {37: _make_detail(37, "GOV-1", html_body="<h3>Section</h3><p>Content.</p>")},
            {37: []},
            {37: []},
        )

        GovernanceExporter(client, tmp_path / "govs").export()

        content = (tmp_path / "govs" / "GOV-1.md").read_text()
        assert "### Section" in content
        assert "Content." in content
        # No HTML artifacts
        assert "<h3>" not in content
        assert "<p>" not in content
        assert "%25" not in content

    def test_markdown_lines_are_max_120_chars(self, tmp_path: Path) -> None:
        long_html = "<p>" + ("word " * 70).strip() + "</p>"
        client = _setup_client(
            [_make_list_item(37, "GOV-1")],
            {37: _make_detail(37, "GOV-1", html_body=long_html)},
            {37: []},
            {37: []},
        )

        GovernanceExporter(client, tmp_path / "govs").export()

        content = (tmp_path / "govs" / "GOV-1.md").read_text()
        for line in content.splitlines():
            assert len(line) <= 120

    def test_frontmatter_includes_owner_and_approver(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(37, "GOV-1")],
            {37: _make_detail(37, "GOV-1")},
            {37: []},
            {37: []},
        )

        GovernanceExporter(client, tmp_path / "govs").export()

        content = (tmp_path / "govs" / "GOV-1.md").read_text()
        assert "owner: Jane Owner" in content
        assert "approver: John Approver" in content

    def test_frontmatter_includes_contributors(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(37, "GOV-1")],
            {37: _make_detail(37, "GOV-1")},
            {37: []},
            {37: []},
        )

        GovernanceExporter(client, tmp_path / "govs").export()

        content = (tmp_path / "govs" / "GOV-1.md").read_text()
        assert "Alice Contrib" in content

    def test_frontmatter_includes_controls_and_requirements(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(37, "GOV-1")],
            {37: _make_detail(37, "GOV-1")},
            {37: _make_controls()},
            {37: _make_requirements()},
        )

        GovernanceExporter(client, tmp_path / "govs").export()

        content = (tmp_path / "govs" / "GOV-1.md").read_text()
        assert "A.5.1" in content
        assert "A.6.2" in content
        assert "ISO-1" in content
        assert "ISO-2" in content

    def test_json_includes_all_fields(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(37, "GOV-1")],
            {37: _make_detail(37, "GOV-1")},
            {37: _make_controls()},
            {37: _make_requirements()},
        )

        GovernanceExporter(client, tmp_path / "govs", keep_raw_json=True).export()

        parsed = json.loads((tmp_path / "govs" / "GOV-1.json").read_text())
        assert parsed["code"] == "GOV-1"
        assert parsed["version"] == "1.2"
        assert parsed["owner"] == "Jane Owner"
        assert parsed["controls"] == ["A.5.1", "A.6.2"]
        assert "body_html" in parsed
        assert "body_markdown" in parsed

    def test_soft_hyphens_removed_from_body(self, tmp_path: Path) -> None:
        html = "<p>Infor\u00admations\u00adsicherheit</p>"
        client = _setup_client(
            [_make_list_item(37, "GOV-1")],
            {37: _make_detail(37, "GOV-1", html_body=html)},
            {37: []},
            {37: []},
        )

        GovernanceExporter(client, tmp_path / "govs").export()

        content = (tmp_path / "govs" / "GOV-1.md").read_text()
        assert "\u00ad" not in content
        assert "Informationssicherheit" in content

    def test_classification_and_review_date_from_properties_fallback(self, tmp_path: Path) -> None:
        detail = _make_detail(37, "GOV-1")
        detail["classification"] = ""
        detail["reviewDate"] = None
        detail["properties"] = {
            "classification": "Intern",
            "reviewDate": "2027-05-01",
        }

        client = _setup_client(
            [_make_list_item(37, "GOV-1")],
            {37: detail},
            {37: []},
            {37: []},
        )

        GovernanceExporter(client, tmp_path / "govs").export()
        content = (tmp_path / "govs" / "GOV-1.md").read_text()
        assert "classification: Intern" in content
        assert "review_date: '2027-05-01'" in content or "review_date: \"2027-05-01\"" in content


class TestGovernanceExporterIndex:
    def test_index_created(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(37, "GOV-1")],
            {37: _make_detail(37, "GOV-1", name=" Doc Title ")},
            {37: []},
            {37: []},
        )

        GovernanceExporter(client, tmp_path / "govs").export()

        index = (tmp_path / "govs" / "index.md").read_text()
        assert "# Governance Documents" in index
        assert "[GOV-1](GOV-1.md)" in index
        assert "Doc Title" in index

    def test_index_has_frontmatter(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(37, "GOV-1")],
            {37: _make_detail(37, "GOV-1")},
            {37: []},
            {37: []},
        )

        GovernanceExporter(client, tmp_path / "govs").export()

        index = (tmp_path / "govs" / "index.md").read_text()
        assert index.startswith("---\n")
        assert "document_count: 1" in index
        assert "generated:" in index

    def test_index_lists_metadata(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(37, "GOV-1")],
            {37: _make_detail(37, "GOV-1")},
            {37: []},
            {37: []},
        )

        GovernanceExporter(client, tmp_path / "govs").export()

        index = (tmp_path / "govs" / "index.md").read_text()
        assert "**Owner:** Jane Owner" in index
        assert "**Status:** Approved" in index
        assert "**Classification:** Intern" in index
        assert "**Review Date:** 2027-01-07" in index

    def test_index_multiple_documents(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(37, "GOV-1"), _make_list_item(38, "GOV-2")],
            {
                37: _make_detail(37, "GOV-1", name=" First "),
                38: _make_detail(38, "GOV-2", name=" Second "),
            },
            {37: [], 38: []},
            {37: [], 38: []},
        )

        GovernanceExporter(client, tmp_path / "govs").export()

        index = (tmp_path / "govs" / "index.md").read_text()
        assert "document_count: 2" in index
        assert "[GOV-1](GOV-1.md) — First" in index
        assert "[GOV-2](GOV-2.md) — Second" in index


class TestGovernanceExporterProgress:
    def test_progress_output(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        client = _setup_client(
            [_make_list_item(37, "GOV-1"), _make_list_item(38, "GOV-2")],
            {
                37: _make_detail(37, "GOV-1"),
                38: _make_detail(38, "GOV-2"),
            },
            {37: [], 38: []},
            {37: [], 38: []},
        )

        GovernanceExporter(client, tmp_path / "govs").export()

        output = capsys.readouterr().out
        assert "Exporting governance" in output
        assert "GOV-1" in output
        assert "GOV-2" in output
        assert "2 documents" in output

    def test_empty_list_progress(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        client = _setup_client([], {}, {}, {})

        GovernanceExporter(client, tmp_path / "govs").export()

        assert "0 documents" in capsys.readouterr().out


class TestGovernanceExporterEdgeCases:
    def test_missing_owner_and_approver(self, tmp_path: Path) -> None:
        detail = _make_detail(37, "GOV-1")
        detail["owner"] = None
        detail["approver"] = None
        detail["contributors"] = []

        client = _setup_client(
            [_make_list_item(37, "GOV-1")],
            {37: detail},
            {37: []},
            {37: []},
        )

        GovernanceExporter(client, tmp_path / "govs", keep_raw_json=True).export()

        parsed = json.loads((tmp_path / "govs" / "GOV-1.json").read_text())
        assert parsed["owner"] == ""
        assert parsed["approver"] == ""
        assert parsed["contributors"] == []

    def test_missing_version_fields(self, tmp_path: Path) -> None:
        detail = _make_detail(37, "GOV-1")
        del detail["majorVersion"]
        del detail["minorVersion"]

        client = _setup_client(
            [_make_list_item(37, "GOV-1")],
            {37: detail},
            {37: []},
            {37: []},
        )

        GovernanceExporter(client, tmp_path / "govs", keep_raw_json=True).export()

        parsed = json.loads((tmp_path / "govs" / "GOV-1.json").read_text())
        assert parsed["version"] == "0.0"

    def test_empty_description(self, tmp_path: Path) -> None:
        detail = _make_detail(37, "GOV-1")
        detail["description"] = ""

        client = _setup_client(
            [_make_list_item(37, "GOV-1")],
            {37: detail},
            {37: []},
            {37: []},
        )

        GovernanceExporter(client, tmp_path / "govs", keep_raw_json=True).export()

        parsed = json.loads((tmp_path / "govs" / "GOV-1.json").read_text())
        assert parsed["body_html"] == ""
        assert parsed["body_markdown"] == ""


class TestGovernanceOverwrite:
    def test_force_overwrites_without_prompt(self, tmp_path: Path) -> None:
        govs = tmp_path / "govs"
        govs.mkdir()
        (govs / "GOV-1.md").write_text("old content")

        client = _setup_client(
            [_make_list_item(37, "GOV-1")],
            {37: _make_detail(37, "GOV-1")},
            {37: []},
            {37: []},
        )

        GovernanceExporter(client, govs, force=True).export()

        content = (govs / "GOV-1.md").read_text()
        assert content != "old content"
        assert "# GOV-1" in content

    def test_prompt_no_skips_file(self, tmp_path: Path) -> None:
        govs = tmp_path / "govs"
        govs.mkdir()
        (govs / "GOV-1.md").write_text("old content")

        client = _setup_client(
            [_make_list_item(37, "GOV-1")],
            {37: _make_detail(37, "GOV-1")},
            {37: []},
            {37: []},
        )

        with patch("builtins.input", return_value="n"):
            GovernanceExporter(client, govs).export()

        assert (govs / "GOV-1.md").read_text() == "old content"

    def test_prompt_yes_overwrites(self, tmp_path: Path) -> None:
        govs = tmp_path / "govs"
        govs.mkdir()
        (govs / "GOV-1.md").write_text("old content")

        client = _setup_client(
            [_make_list_item(37, "GOV-1")],
            {37: _make_detail(37, "GOV-1")},
            {37: []},
            {37: []},
        )

        with patch("builtins.input", return_value="y"):
            GovernanceExporter(client, govs).export()

        content = (govs / "GOV-1.md").read_text()
        assert "# GOV-1" in content

    def test_prompt_all_overwrites_remaining(self, tmp_path: Path) -> None:
        govs = tmp_path / "govs"
        govs.mkdir()
        (govs / "GOV-1.md").write_text("old1")
        (govs / "GOV-2.md").write_text("old2")
        (govs / "index.md").write_text("old index")

        client = _setup_client(
            [_make_list_item(37, "GOV-1"), _make_list_item(38, "GOV-2")],
            {
                37: _make_detail(37, "GOV-1"),
                38: _make_detail(38, "GOV-2"),
            },
            {37: [], 38: []},
            {37: [], 38: []},
        )

        with patch("builtins.input", return_value="a") as mock_input:
            GovernanceExporter(client, govs).export()

        # "All" should stop further prompts — only prompted once
        assert mock_input.call_count == 1
        assert "# GOV-1" in (govs / "GOV-1.md").read_text()
        assert "# GOV-2" in (govs / "GOV-2.md").read_text()

    def test_new_files_written_without_prompt(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(37, "GOV-1")],
            {37: _make_detail(37, "GOV-1")},
            {37: []},
            {37: []},
        )

        with patch("builtins.input") as mock_input:
            GovernanceExporter(client, tmp_path / "govs").export()

        mock_input.assert_not_called()
        assert (tmp_path / "govs" / "GOV-1.md").exists()
