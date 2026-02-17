from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class PolicySection:
    id: int
    title: str
    description: str  # double-URL-encoded HTML


@dataclass
class PolicyDocument:
    id: int
    code: str
    title: str
    status: str
    version: str
    owner: str
    approver: str
    contributors: List[str]
    classification: str
    review_date: str
    updated: str
    sections: List[PolicySection] = field(default_factory=list)
    controls: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    body_html: str = ""
    body_markdown: str = ""
