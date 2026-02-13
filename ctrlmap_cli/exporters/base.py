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
    def __init__(self, client: CtrlMapClient, output_dir: Path) -> None:
        self.client = client
        self.output_dir = output_dir
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

    def _write_document(self, name: str, data: Any) -> None:
        """Write data in Markdown, JSON, and YAML formats."""
        raw = asdict(data) if is_dataclass(data) and not isinstance(data, type) else data
        self._md_formatter.write(raw, self.output_dir / (name + ".md"))
        self._json_formatter.write(raw, self.output_dir / (name + ".json"))
        self._yaml_formatter.write(raw, self.output_dir / (name + ".yaml"))
