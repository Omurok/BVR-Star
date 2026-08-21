"""Normalized civil-time models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class NormalizedInstant(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: Literal["complete"] = "complete"
    local_datetime: datetime
    utc_datetime: datetime
    timezone: str
    utc_offset_seconds: int
    fold: int


class NormalizedDateRange(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: Literal["date_range"] = "date_range"
    timezone: str
    start_local: datetime
    end_local: datetime
    start_utc: datetime
    end_utc: datetime
