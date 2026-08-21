"""Derived D1 chart models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ZodiacPlacement(BaseModel):
    model_config = ConfigDict(frozen=True)

    longitude: float = Field(ge=0, lt=360)
    sign_index: int = Field(ge=0, le=11)
    sign_key: str
    sign_name_en: str
    sign_name_zh: str
    sign_lord: str
    degree_in_sign: float = Field(ge=0, lt=30)
    nakshatra_index: int = Field(ge=0, le=26)
    nakshatra_key: str
    nakshatra_name: str
    nakshatra_lord: str
    pada: int = Field(ge=1, le=4)


class PlanetPlacement(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    zodiac: ZodiacPlacement
    house: int = Field(ge=1, le=12)
    latitude: float
    distance_au: float
    speed_longitude: float
    retrograde: bool
    return_flags: int
    evidence_id: str


class NatalChart(BaseModel):
    model_config = ConfigDict(frozen=True)

    ascendant: ZodiacPlacement
    mc: ZodiacPlacement
    planets: dict[str, PlanetPlacement]
    house_signs: dict[int, int]
    house_lords: dict[int, str]
