"""Small, stable HTTP contract for Custom GPT and other AI actions."""

from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bvr_star.models.request import BirthInput, ChartOptions, ChartRequest
from bvr_star.models.response import ChartResult


class ActionChartRequest(BaseModel):
    """Flat input that language-model tools can construct reliably."""

    model_config = ConfigDict(extra="forbid")

    birth_date: dt.date
    birth_time: dt.time | None = None
    birth_place: str = Field(min_length=2, max_length=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = Field(default=None, min_length=3, max_length=100)
    time_accuracy_minutes: int = Field(default=0, ge=0, le=720)
    reference_date: dt.date | None = None
    output_language: Literal["zh-TW"] = "zh-TW"

    @model_validator(mode="after")
    def validate_coordinates(self) -> ActionChartRequest:
        coordinates = (self.latitude, self.longitude, self.timezone)
        if any(value is not None for value in coordinates) and not all(
            value is not None for value in coordinates
        ):
            raise ValueError("latitude, longitude, and timezone must be supplied together")
        return self

    def to_chart_request(self) -> ChartRequest:
        birth = BirthInput(
            date=self.birth_date,
            time=self.birth_time,
            place=self.birth_place,
            latitude=self.latitude,
            longitude=self.longitude,
            timezone=self.timezone,
            time_accuracy_minutes=self.time_accuracy_minutes,
        )
        option_values: dict[str, Any] = {"output_language": self.output_language}
        if self.reference_date is not None:
            option_values["reference_date"] = self.reference_date
        return ChartRequest(birth=birth, options=ChartOptions(**option_values))


def compact_ai_result(
    result: ChartResult,
    extra_warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Project a typed result into the facts an AI needs for interpretation."""

    data = result.model_dump(mode="json")
    return {
        "schema_version": data["schema_version"],
        "mode": data["mode"],
        "provenance": data["provenance"],
        "location": data["location"],
        "time": data["time"],
        "llm_context": data["llm_context"],
        "warnings": [*(extra_warnings or []), *data["warnings"]],
        "data_handling": {
            "application_storage": "BVR-Star does not persist this request or response.",
            "interpretation": (
                "The API calculates chart data only; interpretation is produced by "
                "the user's chosen AI model."
            ),
        },
    }
