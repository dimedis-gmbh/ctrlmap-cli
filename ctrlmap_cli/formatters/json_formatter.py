from __future__ import annotations

import json
from pathlib import Path
from typing import Any


from ctrlmap_cli.formatters.base import BaseFormatter


class JsonFormatter(BaseFormatter):
    def write(self, data: Any, output_path: Path) -> None:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

    def file_extension(self) -> str:
        return ".json"
