"""Resolve explicit or geocoded birthplace data into one coordinate and timezone."""

from __future__ import annotations

from functools import lru_cache

from timezonefinder import TimezoneFinder

from bvr_star.location.contracts import Geocoder
from bvr_star.models.errors import BVRStarError
from bvr_star.models.location import LocationCandidate, ResolvedLocation
from bvr_star.models.request import BirthInput


@lru_cache(maxsize=1)
def _timezone_finder() -> TimezoneFinder:
    return TimezoneFinder(in_memory=True)


def _timezone_for(candidate: LocationCandidate) -> str:
    timezone_name = _timezone_finder().timezone_at(
        lng=candidate.longitude,
        lat=candidate.latitude,
    )
    if timezone_name is None:
        raise BVRStarError(
            "TIMEZONE_NOT_FOUND",
            "No IANA timezone could be derived for the resolved coordinates.",
            {"latitude": candidate.latitude, "longitude": candidate.longitude},
        )
    return timezone_name


def _choose_candidate(candidates: list[LocationCandidate]) -> LocationCandidate:
    if not candidates:
        raise BVRStarError("LOCATION_NOT_FOUND", "The birthplace could not be resolved.")
    ordered = sorted(candidates, key=lambda item: item.rank, reverse=True)
    if len(ordered) == 1 or ordered[0].rank - ordered[1].rank >= 0.05:
        return ordered[0]
    raise BVRStarError(
        "LOCATION_AMBIGUOUS",
        "The birthplace resolved to multiple similarly ranked locations.",
        {"candidates": [candidate.model_dump(mode="json") for candidate in ordered[:5]]},
    )


def resolve_location(birth: BirthInput, geocoder: Geocoder | None) -> ResolvedLocation:
    """Resolve birthplace while giving explicit coordinates precedence."""

    if birth.latitude is not None and birth.longitude is not None and birth.timezone is not None:
        return ResolvedLocation(
            latitude=birth.latitude,
            longitude=birth.longitude,
            timezone=birth.timezone,
            display_name=birth.place or f"{birth.latitude:.6f},{birth.longitude:.6f}",
            source="explicit",
        )
    if geocoder is None or birth.place is None:
        raise BVRStarError(
            "GEOCODER_REQUIRED",
            "An address-only request requires a configured geocoder.",
        )
    candidate = _choose_candidate(geocoder.search(birth.place))
    return ResolvedLocation(
        latitude=candidate.latitude,
        longitude=candidate.longitude,
        timezone=_timezone_for(candidate),
        display_name=candidate.display_name,
        source="geocoder",
        provider=geocoder.name,
        provider_id=candidate.provider_id,
    )
