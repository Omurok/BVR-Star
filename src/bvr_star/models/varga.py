"""Divisional-chart models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class VargaPlacement(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    division: int
    sign_index: int = Field(ge=0, le=11)
    sign_key: str
    sign_name_en: str
    sign_name_zh: str
    sign_lord: str
    part_index: int = Field(ge=0)
    boundary_distance_degrees: float = Field(ge=0)
    evidence_id: str


class VargaChart(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    division: int
    rule_set: str = "parasari_shodashavarga_v1"
    ascendant: VargaPlacement
    placements: dict[str, VargaPlacement]
