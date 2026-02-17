from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class RiskScore:
    likelihood: int
    likelihood_label: str
    impact: int
    impact_label: str
    score: int
    level: str


@dataclass
class LossAnalysisArea:
    area: str
    current_level: str
    target_level: str
    current_description: str
    target_description: str


@dataclass
class RiskDocument:
    id: int
    code: str
    title: str
    description: str
    status: str
    owner: str
    treatment: str
    tags: List[str]
    inherent_risk: RiskScore
    current_risk: RiskScore
    target_risk: RiskScore
    business_impact: str
    existing_controls: str
    treatment_plan: str
    controls: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)
    threats: List[str] = field(default_factory=list)
    vulnerabilities: List[str] = field(default_factory=list)
    loss_analysis: List[LossAnalysisArea] = field(default_factory=list)
