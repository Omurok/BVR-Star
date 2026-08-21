"""Raw astronomical data returned by the Swiss Ephemeris boundary."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BodyPosition(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    longitude: float = Field(ge=0, lt=360)
    latitude: float
    distance_au: float
    speed_longitude: float
    retrograde: bool
    return_flags: int


class AnglePosition(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    longitude: float = Field(ge=0, lt=360)


class EphemerisSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    jd_et: float
    jd_ut: float
    ayanamsha: float
    ayanamsha_name: str
    bodies: dict[str, BodyPosition]
    ascendant: AnglePosition
    mc: AnglePosition
    source: str
    required_swiss_flag: int
    return_flags: int
    library_version: str
    warnings: list[str] = Field(default_factory=list)
