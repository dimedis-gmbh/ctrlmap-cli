from __future__ import annotations

from urllib.parse import quote

from ctrlmap_cli.html_converter import (
    decode_description,
    html_to_markdown,
    normalize_headings,
    shift_headings,
)


class TestDecodeDescription:
    def test_double_encoded(self) -> None:
        html = "<h3>Heading</h3><p>Text.</p>"
        single = quote(html, safe="")
        double = quote(single, safe="")
        assert decode_description(double) == html

    def test_single_pass_idempotent(self) -> None:
        html = "<p>Simple paragraph</p>"
        single = quote(html, safe="")
        double = quote(single, safe="")
        result = decode_description(double)
        assert "<p>" in result
        assert "%25" not in result
        assert "%3C" not in result

    def test_empty_string(self) -> None:
        assert decode_description("") == ""

    def test_plain_text_unchanged(self) -> None:
        assert decode_description("no encoding") == "no encoding"

    def test_unicode_characters(self) -> None:
        html = "<p>Ärger mit Ümlauten</p>"
        double = quote(quote(html, safe=""), safe="")
        assert "Ärger" in decode_description(double)


class TestHtmlToMarkdown:
    def test_basic_paragraph(self) -> None:
        result = html_to_markdown("<p>Hello world.</p>")
        assert "Hello world." in result

    def test_heading_conversion(self) -> None:
        result = html_to_markdown("<h3>Section Title</h3>")
        assert "### Section Title" in result

    def test_nested_list(self) -> None:
        html = "<ul><li>A<ul><li>B</li></ul></li></ul>"
        result = html_to_markdown(html)
        assert "A" in result
        assert "B" in result

    def test_soft_hyphens_removed(self) -> None:
        result = html_to_markdown("<p>Infor\u00admations\u00adsicherheit</p>")
        assert "\u00ad" not in result
        assert "Informationssicherheit" in result

    def test_nbsp_normalized(self) -> None:
        result = html_to_markdown("<p>word\u00a0word</p>")
        assert "\u00a0" not in result
        assert "word word" in result

    def test_empty_html(self) -> None:
        assert html_to_markdown("") == ""

    def test_excessive_blank_lines_collapsed(self) -> None:
        html = "<p>A</p><br><br><br><p>B</p>"
        result = html_to_markdown(html)
        assert "\n\n\n" not in result

    def test_trailing_whitespace_stripped(self) -> None:
        result = html_to_markdown("<p>text   </p>")
        for line in result.splitlines():
            assert line == line.rstrip()

    def test_table_conversion(self) -> None:
        html = "<table><tr><th>Col</th></tr><tr><td>Val</td></tr></table>"
        result = html_to_markdown(html)
        assert "**Col**: Val" in result
        assert "|" not in result
        assert "- " not in result

    def test_bold_and_italic(self) -> None:
        result = html_to_markdown("<p><strong>bold</strong> and <em>italic</em></p>")
        assert "**bold**" in result
        assert "*italic*" in result

    def test_link_preserved(self) -> None:
        result = html_to_markdown('<p><a href="https://example.com">link</a></p>')
        assert "[link](https://example.com)" in result

    def test_wraps_long_plain_lines_to_120(self) -> None:
        long_text = " ".join(["word"] * 80)
        result = html_to_markdown(f"<p>{long_text}</p>")
        assert all(len(line) <= 120 for line in result.splitlines() if line)


class TestStrongNbspWhitespace:
    def test_strong_nbsp_becomes_space(self) -> None:
        html = "<p>dimedis<strong>&nbsp;</strong>bietet</p>"
        result = html_to_markdown(html)
        assert "dimedis bietet" in result

    def test_bold_space_becomes_space(self) -> None:
        html = "<p>dimedis<strong> </strong>GmbH</p>"
        result = html_to_markdown(html)
        assert "dimedis GmbH" in result

    def test_b_tag_nbsp_becomes_space(self) -> None:
        html = "<p>word<b>&nbsp;</b>other</p>"
        result = html_to_markdown(html)
        assert "word other" in result

    def test_multiple_strong_nbsp_in_paragraph(self) -> None:
        html = (
            "<p>Die dimedis<strong>&nbsp;</strong>GmbH"
            "<strong> </strong>hat ein ISMS eingeführt.</p>"
        )
        result = html_to_markdown(html)
        assert "dimedis GmbH hat" in result

    def test_real_gov1_pattern(self) -> None:
        html = "<p>dimedis<strong>&nbsp;</strong>unterhält Beziehungen.</p>"
        result = html_to_markdown(html)
        assert "dimedis unterhält" in result


class TestLineWrapping:
    def test_long_bold_paragraph_wrapped(self) -> None:
        words = " ".join(["word"] * 15)
        html = f"<p>This is a **{words}** paragraph that should be wrapped.</p>"
        result = html_to_markdown(html)
        for line in result.splitlines():
            assert len(line) <= 120

    def test_long_table_value_wrapped(self) -> None:
        long_value = " ".join(["value"] * 25)
        html = f"<table><tr><th>Key</th></tr><tr><td>{long_value}</td></tr></table>"
        result = html_to_markdown(html)
        for line in result.splitlines():
            assert len(line) <= 120

    def test_heading_not_wrapped(self) -> None:
        long_heading = "A " * 70
        html = f"<h3>{long_heading.strip()}</h3>"
        result = html_to_markdown(html)
        heading_lines = [ln for ln in result.splitlines() if ln.startswith("###")]
        assert len(heading_lines) == 1
        assert long_heading.strip() in heading_lines[0]

    def test_code_block_not_wrapped(self) -> None:
        long_code = "x = " + "a" * 150
        html = f"<pre><code>{long_code}</code></pre>"
        result = html_to_markdown(html)
        assert long_code in result or "a" * 150 in result

    def test_paragraph_with_link_wrapped(self) -> None:
        words = " ".join(["word"] * 20)
        html = (
            f'<p>{words} see <a href="https://example.com">link</a>'
            f" for more {words}.</p>"
        )
        result = html_to_markdown(html)
        for line in result.splitlines():
            assert len(line) <= 120

    def test_list_continuation_indented(self) -> None:
        long_value = " ".join(["value"] * 25)
        html = f"<ul><li>{long_value}</li></ul>"
        result = html_to_markdown(html)
        lines = [ln for ln in result.splitlines() if ln]
        if len(lines) > 1:
            for continuation in lines[1:]:
                assert continuation.startswith("  ")


class TestTableFormat:
    def test_vertical_format_multi_row(self) -> None:
        html = (
            "<table>"
            "<tr><th>Category</th><th>Prio</th></tr>"
            "<tr><td>Games</td><td>0</td></tr>"
            "<tr><td>Travel</td><td>1</td></tr>"
            "</table>"
        )
        result = html_to_markdown(html)
        assert "**Category**: Games" in result
        assert "**Prio**: 0" in result
        assert "**Category**: Travel" in result
        assert "**Prio**: 1" in result

    def test_no_list_prefix(self) -> None:
        html = (
            "<table><tr><th>Key</th></tr>"
            "<tr><td>Val</td></tr></table>"
        )
        result = html_to_markdown(html)
        for line in result.splitlines():
            assert not line.lstrip().startswith("- ")

    def test_colon_outside_bold(self) -> None:
        html = (
            "<table><tr><th>Name</th></tr>"
            "<tr><td>Alice</td></tr></table>"
        )
        result = html_to_markdown(html)
        assert "**Name**: Alice" in result
        assert "**Name:**" not in result

    def test_trailing_double_space(self) -> None:
        html = (
            "<table>"
            "<tr><th>A</th><th>B</th><th>C</th></tr>"
            "<tr><td>1</td><td>2</td><td>3</td></tr>"
            "</table>"
        )
        result = html_to_markdown(html)
        lines = [ln for ln in result.splitlines() if ln.startswith("**")]
        assert len(lines) == 3
        # First two lines should have trailing double space
        assert lines[0].endswith("  ")
        assert lines[1].endswith("  ")
        # Last line should NOT have trailing double space
        assert not lines[2].endswith("  ")

    def test_non_final_row_last_line_keeps_trailing_double_space(self) -> None:
        html = (
            "<table>"
            "<tr><th>A</th><th>B</th></tr>"
            "<tr><td>1</td><td>2</td></tr>"
            "<tr><td>3</td><td>4</td></tr>"
            "</table>"
        )
        result = html_to_markdown(html)
        lines = result.splitlines()

        # Row 1 lines both end with forced line breaks.
        assert lines[0].endswith("  ")
        assert lines[1].endswith("  ")
        # Row separator blank line.
        assert lines[2] == ""
        # Final row: last pair line has no forced line break.
        assert lines[3].endswith("  ")
        assert not lines[4].endswith("  ")

    def test_blank_line_between_rows(self) -> None:
        html = (
            "<table>"
            "<tr><th>Col</th></tr>"
            "<tr><td>A</td></tr>"
            "<tr><td>B</td></tr>"
            "</table>"
        )
        result = html_to_markdown(html)
        assert "**Col**: A" in result
        assert "**Col**: B" in result
        # Row groups separated by blank line
        a_idx = result.index("**Col**: A")
        b_idx = result.index("**Col**: B")
        between = result[a_idx:b_idx]
        assert "\n\n" in between

    def test_empty_cells_skipped(self) -> None:
        html = (
            "<table>"
            "<tr><th>X</th><th>Y</th></tr>"
            "<tr><td>val</td><td></td></tr>"
            "</table>"
        )
        result = html_to_markdown(html)
        assert "**X**: val" in result
        assert "**Y**:" not in result

    def test_wrapped_table_pair_has_trailing_space_only_on_first_physical_line(self) -> None:
        long_value = " ".join(["value"] * 40)
        html = (
            "<table>"
            "<tr><th>Key</th><th>Other</th></tr>"
            f"<tr><td>{long_value}</td><td>x</td></tr>"
            "</table>"
        )
        result = html_to_markdown(html)
        lines = result.splitlines()

        key_line_index = next(i for i, line in enumerate(lines) if line.startswith("**Key**: "))
        assert lines[key_line_index].endswith("  ")
        assert not lines[key_line_index + 1].endswith("  ")

    def test_bold_first_row_used_as_headers(self) -> None:
        """When markdownify produces empty headers and bold first row, use as headers."""
        html = (
            "<table>"
            "<tr><td><strong>Partner</strong></td>"
            "<td><strong>Dienst</strong></td></tr>"
            "<tr><td>Microsoft</td><td>Azure</td></tr>"
            "<tr><td>Atlassian</td><td>Jira</td></tr>"
            "</table>"
        )
        result = html_to_markdown(html)
        assert "**Partner**: Microsoft" in result
        assert "**Dienst**: Azure" in result
        assert "**Partner**: Atlassian" in result
        assert "**Dienst**: Jira" in result
        # Should NOT have "Column 1" fallback
        assert "Column 1" not in result

    def test_no_pipe_in_output(self) -> None:
        html = (
            "<table>"
            "<tr><th>H1</th><th>H2</th></tr>"
            "<tr><td>V1</td><td>V2</td></tr>"
            "</table>"
        )
        result = html_to_markdown(html)
        assert "|" not in result


class TestShiftHeadings:
    def test_shift_down(self) -> None:
        assert shift_headings("## Heading", 1) == "### Heading"

    def test_shift_up(self) -> None:
        assert shift_headings("### Heading", -1) == "## Heading"

    def test_clamped_at_h1(self) -> None:
        assert shift_headings("# Heading", -1) == "# Heading"

    def test_clamped_at_h6(self) -> None:
        assert shift_headings("###### Heading", 1) == "###### Heading"

    def test_zero_delta_unchanged(self) -> None:
        md = "## Title\n\nParagraph.\n\n### Sub"
        assert shift_headings(md, 0) == md

    def test_multiple_headings(self) -> None:
        md = "## A\n\nText\n\n### B\n\n#### C"
        result = shift_headings(md, 1)
        assert "### A" in result
        assert "#### B" in result
        assert "##### C" in result

    def test_code_fence_not_affected(self) -> None:
        md = "```\n## not a heading\n```"
        assert shift_headings(md, 1) == md

    def test_non_heading_hash_not_affected(self) -> None:
        md = "Use #channel for updates."
        assert shift_headings(md, 1) == md


class TestNormalizeHeadings:
    def test_h3_h4_to_h2_h3(self) -> None:
        md = "### Top\n\n#### Sub"
        result = normalize_headings(md, target_min=2)
        assert "## Top" in result
        assert "### Sub" in result

    def test_already_correct(self) -> None:
        md = "## Top\n\n### Sub"
        result = normalize_headings(md, target_min=2)
        assert result == md

    def test_no_headings_unchanged(self) -> None:
        md = "Just plain text.\n\nAnother paragraph."
        assert normalize_headings(md, target_min=2) == md

    def test_target_min_3(self) -> None:
        md = "# Deep\n\n## Deeper"
        result = normalize_headings(md, target_min=3)
        assert "### Deep" in result
        assert "#### Deeper" in result

    def test_code_fence_headings_ignored(self) -> None:
        md = "```\n# code comment\n```\n\n### Real heading"
        result = normalize_headings(md, target_min=2)
        assert "## Real heading" in result
        assert "```\n# code comment\n```" in result
