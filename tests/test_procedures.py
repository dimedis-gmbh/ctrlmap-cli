from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch
from urllib.parse import quote

import pytest

from ctrlmap_cli.exporters.procedures import ProceduresExporter


def _double_encode(html: str) -> str:
    return quote(quote(html, safe=""), safe="")


def _make_list_item(doc_id: int = 28, code: str = "PRO-3") -> Dict[str, Any]:
    return {"id": doc_id, "procedureCode": code}


def _make_detail(
    doc_id: int = 28,
    code: str = "PRO-3",
    name: str = " Test Procedure ",
    html_body: str = "<h3>Heading</h3><p>Paragraph.</p>",
) -> Dict[str, Any]:
    return {
        "id": doc_id,
        "procedureCode": code,
        "name": name,
        "status": {"name": "Approved"},
        "majorVersion": 1,
        "minorVersion": 0,
        "owner": {"fullname": "Jane Owner"},
        "approver": {"fullname": "John Approver"},
        "procedureContributors": [{"fullname": "Alice Contrib"}],
        "dataClassification": "Intern",
        "frequency": {"name": "Annual"},
        "reviewDate": "2027-01-26T09:51:14.000+00:00",
        "updatedate": "2026-01-26T09:51:34.000+00:00",
        "description": _double_encode(html_body),
    }


def _make_controls() -> List[Dict[str, Any]]:
    return [{"controlCode": "A.5.1"}, {"controlCode": "A.6.2"}]


def _make_requirements() -> List[Dict[str, Any]]:
    return [{"requirementCode": "ISO-1"}, {"requirementCode": "ISO-2"}]


def _setup_client(
    list_items: List[Dict[str, Any]],
    details: Dict[int, Dict[str, Any]],
    controls: Optional[Dict[int, List[Dict[str, Any]]]] = None,
    requirements: Optional[Dict[int, List[Dict[str, Any]]]] = None,
) -> MagicMock:
    if controls is None:
        controls = {}
    if requirements is None:
        requirements = {}

    client = MagicMock()
    client.list_procedures.return_value = list_items
    client.get_procedure.side_effect = lambda pid: details.get(pid, {})
    client.get_procedure_controls.side_effect = lambda pid: controls.get(pid, [])
    client.get_procedure_requirements.side_effect = lambda pid: requirements.get(pid, [])
    return client


class TestProceduresExporterEndpoints:
    def test_list_call_uses_list_procedures(self, tmp_path: Path) -> None:
        client = _setup_client(list_items=[], details={})

        ProceduresExporter(client, tmp_path / "pros").export()

        client.list_procedures.assert_called_once_with()

    def test_fetches_detail_per_document(self, tmp_path: Path) -> None:
        client = _setup_client(
            list_items=[_make_list_item(28, "PRO-3")],
            details={28: _make_detail(28, "PRO-3")},
        )

        ProceduresExporter(client, tmp_path / "pros").export()

        client.list_procedures.assert_called_once_with()
        client.get_procedure.assert_called_once_with(28)
        client.get_procedure_controls.assert_called_once_with(28)
        client.get_procedure_requirements.assert_called_once_with(28)

    def test_empty_list_creates_index_only(self, tmp_path: Path) -> None:
        client = _setup_client([], {})

        ProceduresExporter(client, tmp_path / "pros").export()

        assert (tmp_path / "pros" / "index.md").exists()
        assert not list((tmp_path / "pros").glob("PRO-*.md"))


class TestProceduresExporterOutput:
    def test_default_writes_md_only(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(28, "PRO-3")],
            {28: _make_detail(28, "PRO-3")},
        )

        ProceduresExporter(client, tmp_path / "pros").export()

        assert (tmp_path / "pros" / "PRO-3.md").exists()
        assert not (tmp_path / "pros" / "PRO-3.json").exists()
        assert not list((tmp_path / "pros").glob("*.yaml"))

    def test_keep_raw_json_writes_json(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(28, "PRO-3")],
            {28: _make_detail(28, "PRO-3")},
        )

        ProceduresExporter(client, tmp_path / "pros", keep_raw_json=True).export()

        assert (tmp_path / "pros" / "PRO-3.md").exists()
        assert (tmp_path / "pros" / "PRO-3.json").exists()

    def test_markdown_has_frontmatter_and_title(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(28, "PRO-3")],
            {28: _make_detail(28, "PRO-3", name=" My Procedure ")},
        )

        ProceduresExporter(client, tmp_path / "pros").export()

        content = (tmp_path / "pros" / "PRO-3.md").read_text()
        assert content.startswith("---\n")
        assert "# PRO-3 — My Procedure" in content
        assert "id: PRO-3" in content
        assert "status: Approved" in content
        assert "version: '1.0'" in content or 'version: "1.0"' in content

    def test_frontmatter_includes_owner_and_approver(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(28, "PRO-3")],
            {28: _make_detail(28, "PRO-3")},
        )

        ProceduresExporter(client, tmp_path / "pros").export()

        content = (tmp_path / "pros" / "PRO-3.md").read_text()
        assert "owner: Jane Owner" in content
        assert "approver: John Approver" in content

    def test_frontmatter_includes_frequency(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(28, "PRO-3")],
            {28: _make_detail(28, "PRO-3")},
        )

        ProceduresExporter(client, tmp_path / "pros").export()

        content = (tmp_path / "pros" / "PRO-3.md").read_text()
        assert "frequency: Annual" in content

    def test_frontmatter_includes_contributors(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(28, "PRO-3")],
            {28: _make_detail(28, "PRO-3")},
        )

        ProceduresExporter(client, tmp_path / "pros").export()

        content = (tmp_path / "pros" / "PRO-3.md").read_text()
        assert "Alice Contrib" in content

    def test_frontmatter_includes_controls_and_requirements(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(28, "PRO-3")],
            {28: _make_detail(28, "PRO-3")},
            controls={28: _make_controls()},
            requirements={28: _make_requirements()},
        )

        ProceduresExporter(client, tmp_path / "pros").export()

        content = (tmp_path / "pros" / "PRO-3.md").read_text()
        assert "A.5.1" in content
        assert "A.6.2" in content
        assert "ISO-1" in content
        assert "ISO-2" in content

    def test_markdown_body_is_converted_from_html(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(28, "PRO-3")],
            {28: _make_detail(28, "PRO-3", html_body="<h3>Section</h3><p>Content.</p>")},
        )

        ProceduresExporter(client, tmp_path / "pros").export()

        content = (tmp_path / "pros" / "PRO-3.md").read_text()
        assert "### Section" in content
        assert "Content." in content
        assert "<h3>" not in content
        assert "<p>" not in content
        assert "%25" not in content

    def test_markdown_lines_are_max_120_chars(self, tmp_path: Path) -> None:
        long_html = "<p>" + ("word " * 70).strip() + "</p>"
        client = _setup_client(
            [_make_list_item(28, "PRO-3")],
            {28: _make_detail(28, "PRO-3", html_body=long_html)},
        )

        ProceduresExporter(client, tmp_path / "pros").export()

        content = (tmp_path / "pros" / "PRO-3.md").read_text()
        for line in content.splitlines():
            assert len(line) <= 120

    def test_json_includes_all_fields(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(28, "PRO-3")],
            {28: _make_detail(28, "PRO-3")},
            controls={28: _make_controls()},
            requirements={28: _make_requirements()},
        )

        ProceduresExporter(client, tmp_path / "pros", keep_raw_json=True).export()

        parsed = json.loads((tmp_path / "pros" / "PRO-3.json").read_text())
        assert parsed["code"] == "PRO-3"
        assert parsed["version"] == "1.0"
        assert parsed["owner"] == "Jane Owner"
        assert parsed["frequency"] == "Annual"
        assert parsed["controls"] == ["A.5.1", "A.6.2"]
        assert parsed["requirements"] == ["ISO-1", "ISO-2"]
        assert "body_html" in parsed
        assert "body_markdown" in parsed


class TestProceduresIndex:
    def test_index_created(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(28, "PRO-3")],
            {28: _make_detail(28, "PRO-3", name=" My Procedure ")},
        )

        ProceduresExporter(client, tmp_path / "pros").export()

        index = (tmp_path / "pros" / "index.md").read_text()
        assert "# Procedures" in index
        assert "[PRO-3](PRO-3.md)" in index
        assert "My Procedure" in index

    def test_index_has_frontmatter(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(28, "PRO-3")],
            {28: _make_detail(28, "PRO-3")},
        )

        ProceduresExporter(client, tmp_path / "pros").export()

        index = (tmp_path / "pros" / "index.md").read_text()
        assert index.startswith("---\n")
        assert "document_count: 1" in index
        assert "generated:" in index

    def test_index_lists_metadata(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(28, "PRO-3")],
            {28: _make_detail(28, "PRO-3")},
        )

        ProceduresExporter(client, tmp_path / "pros").export()

        index = (tmp_path / "pros" / "index.md").read_text()
        assert "**Owner:** Jane Owner" in index
        assert "**Status:** Approved" in index
        assert "**Classification:** Intern" in index
        assert "**Review Date:** 2027-01-26" in index

    def test_index_contains_summary_line(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(28, "PRO-3"), _make_list_item(29, "PRO-5")],
            {
                28: _make_detail(28, "PRO-3"),
                29: _make_detail(29, "PRO-5"),
            },
        )

        ProceduresExporter(client, tmp_path / "pros").export()

        index = (tmp_path / "pros" / "index.md").read_text()
        assert "2 procedures exported on " in index

    def test_index_multiple_documents(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(28, "PRO-3"), _make_list_item(29, "PRO-5")],
            {
                28: _make_detail(28, "PRO-3", name=" First "),
                29: _make_detail(29, "PRO-5", name=" Second "),
            },
        )

        ProceduresExporter(client, tmp_path / "pros").export()

        index = (tmp_path / "pros" / "index.md").read_text()
        assert "document_count: 2" in index
        assert "[PRO-3](PRO-3.md) — First" in index
        assert "[PRO-5](PRO-5.md) — Second" in index

    def test_index_contains_all_codes_as_links(self, tmp_path: Path) -> None:
        items = [_make_list_item(i, f"PRO-{i}") for i in range(1, 4)]
        details = {i: _make_detail(i, f"PRO-{i}") for i in range(1, 4)}
        client = _setup_client(items, details)

        ProceduresExporter(client, tmp_path / "pros").export()

        index = (tmp_path / "pros" / "index.md").read_text()
        for i in range(1, 4):
            assert f"[PRO-{i}](PRO-{i}.md)" in index


class TestProceduresProgress:
    def test_progress_output(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        client = _setup_client(
            [_make_list_item(28, "PRO-3"), _make_list_item(29, "PRO-5")],
            {
                28: _make_detail(28, "PRO-3"),
                29: _make_detail(29, "PRO-5"),
            },
        )

        ProceduresExporter(client, tmp_path / "pros").export()

        output = capsys.readouterr().out
        assert "Exporting procedures" in output
        assert "PRO-3" in output
        assert "PRO-5" in output
        assert "2 documents" in output

    def test_empty_list_progress(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        client = _setup_client([], {})

        ProceduresExporter(client, tmp_path / "pros").export()

        assert "0 documents" in capsys.readouterr().out


class TestProceduresEdgeCases:
    def test_missing_owner_and_approver(self, tmp_path: Path) -> None:
        detail = _make_detail(28, "PRO-3")
        detail["owner"] = None
        detail["approver"] = None
        detail["procedureContributors"] = []

        client = _setup_client(
            [_make_list_item(28, "PRO-3")],
            {28: detail},
        )

        ProceduresExporter(client, tmp_path / "pros", keep_raw_json=True).export()

        parsed = json.loads((tmp_path / "pros" / "PRO-3.json").read_text())
        assert parsed["owner"] == ""
        assert parsed["approver"] == ""
        assert parsed["contributors"] == []

    def test_missing_version_fields(self, tmp_path: Path) -> None:
        detail = _make_detail(28, "PRO-3")
        del detail["majorVersion"]
        del detail["minorVersion"]

        client = _setup_client(
            [_make_list_item(28, "PRO-3")],
            {28: detail},
        )

        ProceduresExporter(client, tmp_path / "pros", keep_raw_json=True).export()

        parsed = json.loads((tmp_path / "pros" / "PRO-3.json").read_text())
        assert parsed["version"] == "0.0"

    def test_missing_frequency(self, tmp_path: Path) -> None:
        detail = _make_detail(28, "PRO-3")
        detail["frequency"] = None

        client = _setup_client(
            [_make_list_item(28, "PRO-3")],
            {28: detail},
        )

        ProceduresExporter(client, tmp_path / "pros", keep_raw_json=True).export()

        parsed = json.loads((tmp_path / "pros" / "PRO-3.json").read_text())
        assert parsed["frequency"] == ""

    def test_empty_description(self, tmp_path: Path) -> None:
        detail = _make_detail(28, "PRO-3")
        detail["description"] = ""

        client = _setup_client(
            [_make_list_item(28, "PRO-3")],
            {28: detail},
        )

        ProceduresExporter(client, tmp_path / "pros", keep_raw_json=True).export()

        parsed = json.loads((tmp_path / "pros" / "PRO-3.json").read_text())
        assert parsed["body_html"] == ""
        assert parsed["body_markdown"] == ""

    def test_fallback_filename_without_code(self, tmp_path: Path) -> None:
        detail = _make_detail(28, "", name="Unnamed Procedure")
        client = _setup_client(
            [_make_list_item(28, "")],
            {28: detail},
        )

        ProceduresExporter(client, tmp_path / "pros").export()

        assert (tmp_path / "pros" / "PRO-28.md").exists()

    def test_updated_date_truncated_to_date_only(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(28, "PRO-3")],
            {28: _make_detail(28, "PRO-3")},
        )

        ProceduresExporter(client, tmp_path / "pros").export()

        content = (tmp_path / "pros" / "PRO-3.md").read_text()
        assert "updated: '2026-01-26'" in content or 'updated: "2026-01-26"' in content


class TestProceduresOverwrite:
    def test_force_overwrites_without_prompt(self, tmp_path: Path) -> None:
        pros = tmp_path / "pros"
        pros.mkdir()
        (pros / "PRO-3.md").write_text("old content")

        client = _setup_client(
            [_make_list_item(28, "PRO-3")],
            {28: _make_detail(28, "PRO-3")},
        )

        ProceduresExporter(client, pros, force=True).export()

        content = (pros / "PRO-3.md").read_text()
        assert content != "old content"
        assert "# PRO-3" in content

    def test_prompt_no_skips_file(self, tmp_path: Path) -> None:
        pros = tmp_path / "pros"
        pros.mkdir()
        (pros / "PRO-3.md").write_text("old content")

        client = _setup_client(
            [_make_list_item(28, "PRO-3")],
            {28: _make_detail(28, "PRO-3")},
        )

        with patch("builtins.input", return_value="n"):
            ProceduresExporter(client, pros).export()

        assert (pros / "PRO-3.md").read_text() == "old content"

    def test_new_files_written_without_prompt(self, tmp_path: Path) -> None:
        client = _setup_client(
            [_make_list_item(28, "PRO-3")],
            {28: _make_detail(28, "PRO-3")},
        )

        with patch("builtins.input") as mock_input:
            ProceduresExporter(client, tmp_path / "pros").export()

        mock_input.assert_not_called()
        assert (tmp_path / "pros" / "PRO-3.md").exists()

    def test_index_respects_should_write(self, tmp_path: Path) -> None:
        pros = tmp_path / "pros"
        pros.mkdir()
        (pros / "index.md").write_text("old index")

        client = _setup_client(
            [_make_list_item(28, "PRO-3")],
            {28: _make_detail(28, "PRO-3")},
        )

        with patch("builtins.input", return_value="n"):
            ProceduresExporter(client, pros).export()

        assert (pros / "index.md").read_text() == "old index"
