"""Vimshottari dasha response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DashaPeriod(BaseModel):
    model_config = ConfigDict(frozen=True)

    level: int = Field(ge=1, le=3)
    lord: str
    start_utc: datetime
    end_utc: datetime
    active: bool = False
    children: list[DashaPeriod] = Field(default_factory=list)


class VimshottariTimeline(BaseModel):
    model_config = ConfigDict(frozen=True)

    system: str = "vimshottari_120_year_v1"
    birth_nakshatra: str
    birth_nakshatra_lord: str
    elapsed_fraction_at_birth: float
    balance_fraction_at_birth: float
    balance_years_at_birth: float
    reference_utc: datetime
    periods: list[DashaPeriod]
