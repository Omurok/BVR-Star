"""Location provider and normalized birthplace models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class LocationCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    display_name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    rank: float = Field(default=0.0, ge=0)
    provider_id: str | None = None
    address: dict[str, Any] = Field(default_factory=dict)


class ResolvedLocation(BaseModel):
    model_config = ConfigDict(frozen=True)

    latitude: float
    longitude: float
    timezone: str
    display_name: str
    source: Literal["explicit", "geocoder"]
    provider: str | None = None
    provider_id: str | None = None
