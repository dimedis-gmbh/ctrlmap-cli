from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ctrlmap_cli.formatters.base import BaseFormatter


class YamlFormatter(BaseFormatter):
    def write(self, data: Any, output_path: Path) -> None:
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(
                data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

    def file_extension(self) -> str:
        return ".yaml"
