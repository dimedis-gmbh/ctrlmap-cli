from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ctrlmap_cli.formatters.json_formatter import JsonFormatter
from ctrlmap_cli.formatters.markdown_formatter import MarkdownFormatter


class TestJsonFormatter:
    def test_file_extension(self) -> None:
        assert JsonFormatter().file_extension() == ".json"

    def test_write_and_parse_back(self, tmp_path: Path) -> None:
        data = {"id": 1, "name": "Test", "tags": ["a", "b"]}
        path = tmp_path / "out.json"
        JsonFormatter().write(data, path)

        content = path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert parsed == data

    def test_indent_and_no_ascii_escape(self, tmp_path: Path) -> None:
        data = {"title": "Ärger mit Ümlauten"}
        path = tmp_path / "out.json"
        JsonFormatter().write(data, path)

        content = path.read_text(encoding="utf-8")
        assert "Ärger" in content
        assert "  " in content  # indented

    def test_trailing_newline(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        JsonFormatter().write({}, path)
        assert path.read_text(encoding="utf-8").endswith("\n")


class TestMarkdownFormatter:
    def test_file_extension(self) -> None:
        assert MarkdownFormatter().file_extension() == ".md"

    def test_render_full(self) -> None:
        result = MarkdownFormatter.render(
            title="My Document",
            body="Some content here.",
            frontmatter={"id": "GOV-1", "status": "Approved"},
        )
        assert result.startswith("---\n")
        assert "id: GOV-1" in result
        assert "---\n" in result
        assert "# My Document" in result
        assert "Some content here." in result

    def test_render_no_frontmatter(self) -> None:
        result = MarkdownFormatter.render(title="Title", body="Body text.")
        assert "---" not in result
        assert "# Title" in result
        assert "Body text." in result

    def test_render_no_title(self) -> None:
        result = MarkdownFormatter.render(
            title="",
            body="Just body.",
            frontmatter={"key": "val"},
        )
        assert "# " not in result
        assert "Just body." in result

    def test_render_empty(self) -> None:
        result = MarkdownFormatter.render(title="", body="")
        assert result == ""

    def test_write_dict_data(self, tmp_path: Path) -> None:
        data = {
            "title": "Test",
            "frontmatter": {"id": 1},
            "body": "Content.",
        }
        path = tmp_path / "out.md"
        MarkdownFormatter().write(data, path)

        content = path.read_text(encoding="utf-8")
        assert "# Test" in content
        assert "id: 1" in content

    def test_write_string_data(self, tmp_path: Path) -> None:
        path = tmp_path / "out.md"
        MarkdownFormatter().write("raw markdown content", path)

        content = path.read_text(encoding="utf-8")
        assert content == "raw markdown content"

    def test_frontmatter_unicode(self) -> None:
        result = MarkdownFormatter.render(
            title="Über uns",
            body="Inhalt.",
            frontmatter={"title": "Über uns"},
        )
        assert "Über uns" in result

    def test_render_wraps_long_plain_lines(self) -> None:
        long_line = "word " * 40
        result = MarkdownFormatter.render(title="", body=long_line.strip())
        body_lines = [line for line in result.splitlines() if line]
        assert body_lines
        assert all(len(line) <= 120 for line in body_lines)

    def test_render_preserves_inline_markdown_line(self) -> None:
        link_line = (
            "[A very long link that should remain untouched because markdown inline formatting is present]"
            "(https://example.com/some/really/long/path/that/should/not/be/wrapped)"
        )
        result = MarkdownFormatter.render(title="", body=link_line)
        assert link_line in result

    def test_write_dataclass_data(self, tmp_path: Path) -> None:
        @dataclass
        class Doc:
            title: str
            body: str
            metadata: dict

        data = Doc(
            title="Dataclass Title",
            body="Dataclass body.",
            metadata={"id": "DOC-1", "status": "approved"},
        )
        path = tmp_path / "doc.md"
        MarkdownFormatter().write(data, path)

        content = path.read_text(encoding="utf-8")
        assert content.startswith("---\n")
        assert "id: DOC-1" in content
        assert "# Dataclass Title" in content
        assert "Dataclass body." in content

    def test_write_dict_metadata_alias(self, tmp_path: Path) -> None:
        data = {
            "title": "Alias Test",
            "body": "Body",
            "metadata": {"owner": "qa"},
        }
        path = tmp_path / "alias.md"
        MarkdownFormatter().write(data, path)

        content = path.read_text(encoding="utf-8")
        assert "owner: qa" in content

    def test_write_dict_generates_frontmatter_from_extra_fields(self, tmp_path: Path) -> None:
        data = {
            "title": "Generated FM",
            "body": "Body",
            "document_id": "DOC-7",
            "version": 2,
        }
        path = tmp_path / "generated.md"
        MarkdownFormatter().write(data, path)

        content = path.read_text(encoding="utf-8")
        assert "document_id: DOC-7" in content
        assert "version: 2" in content
