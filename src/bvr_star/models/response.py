"""Stable public response schemas shared by Python, CLI, and HTTP."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from bvr_star.models.analysis import RuleAnalysis
from bvr_star.models.chart import NatalChart
from bvr_star.models.dasha import VimshottariTimeline
from bvr_star.models.location import ResolvedLocation
from bvr_star.models.request import ChartRequest, ChartSettings
from bvr_star.models.time import NormalizedDateRange, NormalizedInstant
from bvr_star.models.varga import VargaChart


class Provenance(BaseModel):
    model_config = ConfigDict(frozen=True)

    engine: str
    engine_version: str
    calculation_profile: str
    ephemeris_library: str
    ephemeris_version: str
    ephemeris_source: str
    ephemeris_files_ready: bool
    ayanamsha_degrees: float | None = None
    ayanamsha_name: str | None = None
    rule_set: str = "bvr_rules_v1"
    varga_rule_set: str = "parasari_shodashavarga_v1"


class SensitivityResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    evaluated: bool
    accuracy_minutes: int
    stable: list[str] = Field(default_factory=list)
    changed: list[str] = Field(default_factory=list)
    endpoints: list[dict[str, Any]] = Field(default_factory=list)


class ChartResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = "bvr-star-response-v1"
    mode: Literal["complete"] = "complete"
    request: ChartRequest
    settings: ChartSettings
    location: ResolvedLocation
    time: NormalizedInstant
    provenance: Provenance
    chart: NatalChart
    vargas: dict[str, VargaChart]
    dashas: VimshottariTimeline
    rules: RuleAnalysis
    sensitivity: SensitivityResult
    warnings: list[str] = Field(default_factory=list)
    llm_context: dict[str, Any] = Field(default_factory=dict)


class DateRangeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = "bvr-star-response-v1"
    mode: Literal["date_range"] = "date_range"
    request: ChartRequest
    settings: ChartSettings
    location: ResolvedLocation
    time: NormalizedDateRange
    provenance: Provenance
    planetary_ranges: dict[str, dict[str, Any]]
    crossings: list[dict[str, Any]] = Field(default_factory=list)
    omitted_time_sensitive_fields: list[str]
    warnings: list[str] = Field(default_factory=list)
    llm_context: dict[str, Any] = Field(default_factory=dict)


ChartResult = ChartResponse | DateRangeResponse
