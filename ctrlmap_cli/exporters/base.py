from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Tuple

import yaml

from ctrlmap_cli.client import CtrlMapClient
from ctrlmap_cli.formatters.json_formatter import JsonFormatter


class BaseExporter(ABC):
    def __init__(
        self,
        client: CtrlMapClient,
        output_dir: Path,
        *,
        force: bool = False,
        keep_raw_json: bool = False,
    ) -> None:
        self.client = client
        self.output_dir = output_dir
        self.force = force
        self.keep_raw_json = keep_raw_json
        self._overwrite_all = False
        self._json_formatter = JsonFormatter()

    @abstractmethod
    def export(self) -> None:
        """Fetch data from API and write to output_dir."""
        ...

    @abstractmethod
    def export_single(self, item_code: str) -> None:
        """Export a single item by code and rebuild the index."""
        ...

    def _ensure_output_dir(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _log(self, message: str) -> None:
        print(message)

    def _should_write(self, path: Path) -> bool:
        """Check whether *path* should be written, prompting if needed."""
        if not path.exists():
            return True
        if self.force or self._overwrite_all:
            return True
        while True:
            answer = input(
                f"Overwrite existing {path.name}? [Yes/No/All] "
            ).strip().lower()
            if answer in ("y", "yes"):
                return True
            if answer in ("n", "no"):
                return False
            if answer in ("a", "all"):
                self._overwrite_all = True
                return True

    @staticmethod
    def _parse_item_code(code: str, prefix: str) -> Tuple[str, int]:
        """Parse an item code like 'GOV-1' or '1' into (full_code, numeric_id).

        Accepts both 'PREFIX-N' and plain 'N' formats.
        """
        code = code.strip()
        pattern = re.compile(
            r'^' + re.escape(prefix) + r'-(\d+)$', re.IGNORECASE,
        )
        match = pattern.match(code)
        if match:
            numeric = int(match.group(1))
            return f"{prefix}-{numeric}", numeric

        if code.isdigit():
            numeric = int(code)
            return f"{prefix}-{numeric}", numeric

        raise ValueError(
            f"Invalid item code '{code}'. "
            f"Expected '{prefix}-<number>' or just a number."
        )

    def _read_local_frontmatter(self) -> Dict[str, Dict[str, Any]]:
        """Read YAML frontmatter from all .md files in output_dir (except index.md).

        Returns a dict keyed by file stem (e.g. 'GOV-1').
        """
        result: Dict[str, Dict[str, Any]] = {}
        if not self.output_dir.exists():
            return result

        for md_path in sorted(self.output_dir.glob("*.md")):
            if md_path.name == "index.md":
                continue
            fm = self._extract_frontmatter(md_path)
            if fm is not None:
                result[md_path.stem] = fm
        return result

    @staticmethod
    def _extract_frontmatter(path: Path) -> Any:
        """Extract YAML frontmatter from a markdown file."""
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return None

        if not text.startswith("---\n"):
            return None

        end = text.find("\n---\n", 4)
        if end == -1:
            return None

        yaml_text = text[4:end]
        try:
            return yaml.safe_load(yaml_text)
        except yaml.YAMLError:
            return None
