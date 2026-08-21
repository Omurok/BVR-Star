"""Convert local civil time into unambiguous UTC instants."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from bvr_star.models.errors import BVRStarError
from bvr_star.models.request import BirthInput
from bvr_star.models.time import NormalizedDateRange, NormalizedInstant


def _zone(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise BVRStarError(
            "TIMEZONE_NOT_FOUND",
            f"Unknown IANA timezone: {timezone_name}",
            {"timezone": timezone_name},
        ) from exc


def _valid_candidates(naive: datetime, zone: ZoneInfo) -> list[datetime]:
    candidates: list[datetime] = []
    for fold in (0, 1):
        aware = naive.replace(tzinfo=zone, fold=fold)
        roundtrip = aware.astimezone(UTC).astimezone(zone)
        if roundtrip.replace(tzinfo=None) == naive and roundtrip.fold == fold:
            candidates.append(aware)
    return candidates


def _resolve_local(naive: datetime, timezone_name: str, fold: int | None) -> datetime:
    zone = _zone(timezone_name)
    candidates = _valid_candidates(naive, zone)
    if not candidates:
        raise BVRStarError(
            "LOCAL_TIME_NONEXISTENT",
            "The supplied local time did not exist because of a civil-time transition.",
            {"local_datetime": naive.isoformat(), "timezone": timezone_name},
        )
    if len(candidates) == 2 and candidates[0].utcoffset() != candidates[1].utcoffset():
        if fold is None:
            raise BVRStarError(
                "LOCAL_TIME_AMBIGUOUS",
                "The supplied local time occurred twice; choose fold 0 or 1.",
                {
                    "local_datetime": naive.isoformat(),
                    "timezone": timezone_name,
                    "folds": [0, 1],
                },
            )
        return candidates[fold]
    if fold not in (None, 0):
        raise BVRStarError(
            "FOLD_NOT_APPLICABLE",
            "fold=1 is only valid for an overlapping civil time.",
            {"local_datetime": naive.isoformat(), "timezone": timezone_name},
        )
    return candidates[0]


def _midnight(day: date, timezone_name: str) -> datetime:
    naive = datetime.combine(day, time.min)
    candidates = _valid_candidates(naive, _zone(timezone_name))
    if not candidates:
        raise BVRStarError(
            "LOCAL_DATE_BOUNDARY_NONEXISTENT",
            "The local civil date has no midnight boundary in this timezone.",
            {"date": day.isoformat(), "timezone": timezone_name},
        )
    return min(candidates, key=lambda value: value.astimezone(UTC))


def normalize_birth_time(
    birth: BirthInput, timezone_name: str
) -> NormalizedInstant | NormalizedDateRange:
    """Normalize a birth time or represent the full local date without inventing noon."""

    if birth.time is None:
        start_local = _midnight(birth.date, timezone_name)
        end_local = _midnight(birth.date + timedelta(days=1), timezone_name)
        return NormalizedDateRange(
            timezone=timezone_name,
            start_local=start_local,
            end_local=end_local,
            start_utc=start_local.astimezone(UTC),
            end_utc=end_local.astimezone(UTC),
        )

    naive = datetime.combine(birth.date, birth.time)
    local_datetime = _resolve_local(naive, timezone_name, birth.fold)
    offset = local_datetime.utcoffset()
    if offset is None:
        raise BVRStarError("UTC_OFFSET_MISSING", "Unable to derive UTC offset.")
    return NormalizedInstant(
        local_datetime=local_datetime,
        utc_datetime=local_datetime.astimezone(UTC),
        timezone=timezone_name,
        utc_offset_seconds=int(offset.total_seconds()),
        fold=local_datetime.fold,
    )
