from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseFormatter(ABC):
    @abstractmethod
    def write(self, data: Any, output_path: Path) -> None:
        ...

    @abstractmethod
    def file_extension(self) -> str:
        ...
