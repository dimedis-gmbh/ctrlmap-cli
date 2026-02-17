from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class VendorAttachment:
    id: int
    filename: str
    signed_url: str
    created: str


@dataclass
class VendorLink:
    id: int
    name: str
    url: str


@dataclass
class VendorContact:
    id: int
    name: str
    email: str


@dataclass
class VendorRisk:
    id: int
    code: str
    name: str
    owner: str
    inherent_score: int
    inherent_level: str
    current_score: int
    current_level: str
    target_score: int
    target_level: str


@dataclass
class QuickAssessmentQuestion:
    code: str
    title: str
    answer: str
    risk_level: str
    group: str


@dataclass
class VendorDocument:
    id: int
    code: str
    name: str
    status: str
    vendor_type: str
    owner: str
    tier: str
    tags: List[str]
    risk_score: float
    description: str
    documents: List[VendorAttachment] = field(default_factory=list)
    hyperlinks: List[VendorLink] = field(default_factory=list)
    contacts: List[VendorContact] = field(default_factory=list)
    risks: List[VendorRisk] = field(default_factory=list)
    quick_assessment: List[QuickAssessmentQuestion] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)
