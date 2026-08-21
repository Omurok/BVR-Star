"""Auditable rule-engine facts; prose interpretation is intentionally external."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EvidenceRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    ids: list[str]
    explanation: str


class AnalysisFact(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    category: str
    title_zh: str
    title_en: str
    strength: float = Field(ge=0, le=1)
    data: dict[str, Any] = Field(default_factory=dict)
    evidence: EvidenceRef


class RuleAnalysis(BaseModel):
    model_config = ConfigDict(frozen=True)

    ruleset: str = "bvr_rules_v1"
    dignity: dict[str, str]
    facts: list[AnalysisFact]
