from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class GovernanceDocument:
    id: int
    code: str
    title: str
    status: str
    version: str
    owner: str
    approver: str
    contributors: List[str]
    classification: str
    review_date: Optional[str]
    updated: Optional[str]
    controls: List[str]
    requirements: List[str]
    body_html: str
    body_markdown: str
