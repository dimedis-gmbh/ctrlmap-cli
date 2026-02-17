from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ProcedureDocument:
    id: int
    code: str
    title: str
    status: str
    version: str
    owner: str
    approver: str
    contributors: List[str]
    classification: str
    frequency: str
    review_date: str
    updated: str
    controls: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    body_html: str = ""
    body_markdown: str = ""
