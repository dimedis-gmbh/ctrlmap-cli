from __future__ import annotations

import re
import textwrap
from urllib.parse import unquote

import markdownify

_MAX_LINE_LENGTH = 120

# Pattern: <strong>&nbsp;</strong> or <b>&nbsp;</b> or <strong> </strong>
# ControlMap editor inserts these as word separators.
_BOLD_NBSP_RE = re.compile(r"<(strong|b)>\s*(&nbsp;|\s)\s*</\1>", re.IGNORECASE)
_TABLE_BREAK_MARKER = "\x01"
_TABLE_NO_BREAK_MARKER = "\x02"


def decode_description(encoded: str) -> str:
    """Double URL-decode the ControlMap description field."""
    if not encoded:
        return ""
    return unquote(unquote(encoded))


def html_to_markdown(html: str) -> str:
    """Convert HTML to Markdown, cleaning up artifacts."""
    if not html:
        return ""
    html = _preprocess_html(html)
    md: str = markdownify.markdownify(html, heading_style="ATX")
    md = md.replace("\u00ad", "")
    md = md.replace("\u00a0", " ")
    md = md.replace("&nbsp;", " ")
    md = _convert_markdown_tables_to_lists(md)
    md = _wrap_markdown(md)
    md = "\n".join(line.rstrip() for line in md.splitlines())
    md = _apply_table_linebreak_markers(md)
    while "\n\n\n" in md:
        md = md.replace("\n\n\n", "\n\n")
    return md.strip()


def _preprocess_html(html: str) -> str:
    """Clean HTML before markdownify conversion."""
    return _BOLD_NBSP_RE.sub(" ", html)


def _convert_markdown_tables_to_lists(md: str) -> str:
    lines = md.splitlines()
    output = []
    idx = 0

    while idx < len(lines):
        line = lines[idx]
        if (
            _looks_like_table_row(line)
            and idx + 1 < len(lines)
            and _looks_like_table_separator(lines[idx + 1])
        ):
            headers = _split_table_row(line)
            idx += 2
            rows = []
            while idx < len(lines) and _looks_like_table_row(lines[idx]):
                rows.append(_split_table_row(lines[idx]))
                idx += 1
            output.extend(_table_rows_to_list(headers, rows))
            continue

        output.append(line)
        idx += 1

    return "\n".join(output)


def _looks_like_table_row(line: str) -> bool:
    return "|" in line and len(_split_table_row(line)) > 0


def _looks_like_table_separator(line: str) -> bool:
    stripped = line.strip()
    return bool(re.match(r"^\|?[\s:\-]+\|[\s:\-\|]*$", stripped))


def _split_table_row(line: str) -> list:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [part.strip() for part in stripped.split("|")]


def _strip_bold(text: str) -> str:
    """Strip surrounding ** bold markers from text."""
    s = text.strip()
    if s.startswith("**") and s.endswith("**") and len(s) > 4:
        return s[2:-2].strip()
    return s


def _table_rows_to_list(headers: list, rows: list) -> list:
    if not rows:
        return []

    # Strip bold markers from headers (markdownify may bold <th> content)
    clean_headers = [_strip_bold(h) for h in headers]

    # If all headers are empty, try to use first data row as headers
    if all(not h for h in clean_headers):
        candidate = [_strip_bold(cell) for cell in rows[0]]
        if any(c for c in candidate):
            clean_headers = candidate
            rows = rows[1:]

    if not rows:
        return []

    row_pairs: list[list[str]] = []
    for row in rows:
        padded = list(row) + [""] * max(0, len(clean_headers) - len(row))
        lines: list[str] = []
        for i, cell in enumerate(padded):
            if not cell:
                continue
            header = (
                clean_headers[i]
                if i < len(clean_headers) and clean_headers[i]
                else f"Column {i + 1}"
            )
            lines.append(f"**{header}**: {cell}")
        if lines:
            row_pairs.append(lines)

    if not row_pairs:
        return []

    converted: list[str] = []
    for row_idx, lines in enumerate(row_pairs):
        for line_idx, line in enumerate(lines):
            is_last_line_overall = row_idx == len(row_pairs) - 1 and line_idx == len(lines) - 1
            marker = _TABLE_NO_BREAK_MARKER if is_last_line_overall else _TABLE_BREAK_MARKER
            converted.append(marker + line)
        if row_idx < len(row_pairs) - 1:
            converted.append("")  # blank line between rows
    return converted


_TABLE_PAIR_RE = re.compile(r"^\*\*.+?\*\*: ")


def _is_table_pair_line(line: str) -> bool:
    """Check if a line matches the **Header**: Value table format."""
    return bool(_TABLE_PAIR_RE.match(_strip_table_marker(line)))


def _strip_table_marker(line: str) -> str:
    if line.startswith((_TABLE_BREAK_MARKER, _TABLE_NO_BREAK_MARKER)):
        return line[1:]
    return line


def _table_marker(line: str) -> str:
    if line.startswith((_TABLE_BREAK_MARKER, _TABLE_NO_BREAK_MARKER)):
        return line[0]
    return ""


def _apply_table_linebreak_markers(md: str) -> str:
    """Apply pair-level hard line breaks marked during table conversion."""
    output: list[str] = []
    for line in md.splitlines():
        marker = _table_marker(line)
        content = _strip_table_marker(line)
        if marker == _TABLE_BREAK_MARKER:
            output.append(content + "  ")
            continue
        output.append(content)
    return "\n".join(output)


def _wrap_markdown(md: str) -> str:
    wrapped = []
    in_code_fence = False
    for line in md.splitlines():
        marker = _table_marker(line)
        clean_line = _strip_table_marker(line)

        if clean_line.lstrip().startswith("```"):
            in_code_fence = not in_code_fence
            wrapped.append(line)
            continue
        if not clean_line:
            wrapped.append("")
            continue

        # Table lines marked for hard breaks get '  ' appended later; use reduced width.
        effective_width = _MAX_LINE_LENGTH - 2 if marker == _TABLE_BREAK_MARKER else _MAX_LINE_LENGTH

        if in_code_fence or len(clean_line) <= effective_width or _should_preserve_line(clean_line):
            wrapped.append(line)
            continue

        stripped = clean_line.lstrip()
        leading = clean_line[: len(clean_line) - len(stripped)]

        if stripped.startswith(("- ", "* ")):
            subsequent = leading + "  "
        else:
            subsequent = leading

        wrapped_text = textwrap.fill(
            stripped,
            width=effective_width,
            initial_indent=leading,
            subsequent_indent=subsequent,
            break_long_words=False,
            break_on_hyphens=False,
        )
        if marker:
            wrapped_lines = wrapped_text.splitlines()
            wrapped_lines[0] = marker + wrapped_lines[0]
            wrapped.append("\n".join(wrapped_lines))
            continue
        wrapped.append(wrapped_text)
    return "\n".join(wrapped)


_HEADING_RE = re.compile(r"^(#{1,6})\s")


def shift_headings(md: str, delta: int) -> str:
    """Shift all markdown heading levels by *delta*.

    Positive *delta* increases depth (h2 -> h3), negative decreases (h3 -> h2).
    Levels are clamped to the 1-6 range.
    """
    if delta == 0:
        return md

    def _shift(m: re.Match) -> str:  # type: ignore[type-arg]
        hashes = m.group(1)
        new_level = max(1, min(6, len(hashes) + delta))
        return "#" * new_level + " "

    lines = md.splitlines()
    result: list[str] = []
    in_code_fence = False
    for line in lines:
        if line.lstrip().startswith("```"):
            in_code_fence = not in_code_fence
        if not in_code_fence:
            line = _HEADING_RE.sub(_shift, line)
        result.append(line)
    return "\n".join(result)


def normalize_headings(md: str, target_min: int = 2) -> str:
    """Shift all headings so the highest level becomes *target_min*.

    If the text has h3 and h4 and *target_min* is 2, h3 becomes h2 and
    h4 becomes h3.  Text without headings is returned unchanged.
    """
    min_level = 7
    in_code_fence = False
    for line in md.splitlines():
        if line.lstrip().startswith("```"):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            continue
        m = _HEADING_RE.match(line)
        if m:
            min_level = min(min_level, len(m.group(1)))
    if min_level > 6:
        return md  # no headings found
    return shift_headings(md, target_min - min_level)


def _should_preserve_line(line: str) -> bool:
    stripped = line.lstrip()
    if stripped.startswith(("#", ">", "```")):
        return True
    if line.startswith(("    ", "\t")):
        return True
    if stripped == "---":
        return True
    return False
