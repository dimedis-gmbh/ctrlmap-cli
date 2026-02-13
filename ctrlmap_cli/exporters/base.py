from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from ctrlmap_cli.client import CtrlMapClient
from ctrlmap_cli.formatters.json_formatter import JsonFormatter
from ctrlmap_cli.formatters.markdown_formatter import MarkdownFormatter
from ctrlmap_cli.formatters.yaml_formatter import YamlFormatter


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
        self._md_formatter = MarkdownFormatter()
        self._json_formatter = JsonFormatter()
        self._yaml_formatter = YamlFormatter()

    @abstractmethod
    def export(self) -> None:
        """Fetch data from API and write to output_dir."""
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

    def _write_document(self, name: str, data: Any) -> None:
        """Write data in Markdown, JSON, and YAML formats."""
        raw = asdict(data) if is_dataclass(data) and not isinstance(data, type) else data

        md_path = self.output_dir / (name + ".md")
        if self._should_write(md_path):
            self._md_formatter.write(raw, md_path)

        if self.keep_raw_json:
            json_path = self.output_dir / (name + ".json")
            if self._should_write(json_path):
                self._json_formatter.write(raw, json_path)

        yaml_path = self.output_dir / (name + ".yaml")
        if self._should_write(yaml_path):
            self._yaml_formatter.write(raw, yaml_path)
