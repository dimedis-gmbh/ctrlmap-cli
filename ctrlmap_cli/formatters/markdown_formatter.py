from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
import textwrap
from typing import Any, Dict, Optional

import yaml

from ctrlmap_cli.formatters.base import BaseFormatter


class MarkdownFormatter(BaseFormatter):
    _MAX_LINE_LENGTH = 120

    def write(self, data: Any, output_path: Path) -> None:
        content = self._render_data(data)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

    def file_extension(self) -> str:
        return ".md"

    @classmethod
    def render(
        cls,
        title: str,
        body: str,
        frontmatter: Optional[Dict[str, Any]] = None,
    ) -> str:
        parts = []
        if frontmatter:
            fm_text = yaml.dump(
                frontmatter,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            ).rstrip("\n")
            parts.append(f"---\n{fm_text}\n---\n")
        if title:
            parts.append(f"# {title}\n")
        if body:
            wrapped_body = cls._wrap_body(body.rstrip("\n"))
            parts.append(wrapped_body + "\n")
        return "\n".join(parts)

    def _render_data(self, data: Any) -> str:
        if isinstance(data, str):
            return data

        payload: Optional[Dict[str, Any]] = None
        if isinstance(data, dict):
            payload = dict(data)
        elif is_dataclass(data) and not isinstance(data, type):
            payload = asdict(data)

        if payload is None:
            return str(data)

        title = str(payload.get("title", ""))
        body = str(payload.get("body", ""))

        frontmatter_value = payload.get("frontmatter", payload.get("metadata"))
        frontmatter: Optional[Dict[str, Any]]
        if isinstance(frontmatter_value, dict):
            frontmatter = frontmatter_value
        else:
            excluded = {"title", "body", "frontmatter", "metadata"}
            generated = {k: v for k, v in payload.items() if k not in excluded}
            frontmatter = generated or None

        return self.render(title=title, body=body, frontmatter=frontmatter)

    @classmethod
    def _wrap_body(cls, body: str) -> str:
        wrapped_lines = []
        for line in body.splitlines():
            if cls._should_preserve_line(line):
                wrapped_lines.append(line)
                continue
            wrapped_lines.append(
                textwrap.fill(
                    line,
                    width=cls._MAX_LINE_LENGTH,
                    break_long_words=False,
                    break_on_hyphens=False,
                )
            )
        return "\n".join(wrapped_lines)

    @classmethod
    def _should_preserve_line(cls, line: str) -> bool:
        if not line:
            return True
        if len(line) <= cls._MAX_LINE_LENGTH:
            return True
        if line.startswith(("#", "- ", "* ", "> ", "```", "    ", "\t")):
            return True
        if "`" in line or "](" in line or "**" in line:
            return True
        return False
