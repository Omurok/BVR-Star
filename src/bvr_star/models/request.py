"""Canonical user input and calculation settings."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BirthInput(BaseModel):
    """Civil birth information before location and timezone normalization."""

    model_config = ConfigDict(extra="forbid")

    date: dt.date
    time: dt.time | None = None
    place: str | None = Field(default=None, min_length=2, max_length=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = Field(default=None, min_length=3, max_length=100)
    fold: Literal[0, 1] | None = None
    time_accuracy_minutes: int = Field(default=0, ge=0, le=720)

    @model_validator(mode="after")
    def validate_birth(self) -> BirthInput:
        coordinates = (self.latitude, self.longitude, self.timezone)
        if any(value is not None for value in coordinates) and not all(
            value is not None for value in coordinates
        ):
            raise ValueError("latitude, longitude, and timezone must be supplied together")
        if self.place is None and not all(value is not None for value in coordinates):
            raise ValueError("place or latitude, longitude, and timezone is required")
        if not dt.date(1900, 1, 1) <= self.date <= dt.date(2099, 12, 31):
            raise ValueError("date must be between 1900-01-01 and 2099-12-31")
        if self.fold is not None and self.time is None:
            raise ValueError("fold can only be used when birth time is provided")
        return self


class ChartSettings(BaseModel):
    """Versioned Jyotish convention profile."""

    model_config = ConfigDict(extra="forbid")

    profile: Literal["bvr_raman_v1"] = "bvr_raman_v1"
    zodiac: Literal["sidereal"] = "sidereal"
    ayanamsha: Literal["raman"] = "raman"
    node_type: Literal["mean"] = "mean"
    house_system: Literal["whole_sign"] = "whole_sign"
    aspect_system: Literal["parasari"] = "parasari"
    dasha_system: Literal["vimshottari"] = "vimshottari"


class ChartOptions(BaseModel):
    """Response-shaping options that do not change the natal chart."""

    model_config = ConfigDict(extra="forbid")

    include: list[Literal["full", "llm_context"]] = Field(
        default_factory=lambda: ["full", "llm_context"]
    )
    dasha_depth: int = Field(default=3, ge=1, le=3)
    reference_date: dt.date = Field(default_factory=dt.date.today)
    output_language: Literal["zh-TW", "en"] = "zh-TW"


class ChartRequest(BaseModel):
    """The one request type accepted by Python, CLI, and HTTP."""

    model_config = ConfigDict(extra="forbid")

    birth: BirthInput
    settings: ChartSettings = Field(default_factory=ChartSettings)
    options: ChartOptions = Field(default_factory=ChartOptions)
