from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

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
