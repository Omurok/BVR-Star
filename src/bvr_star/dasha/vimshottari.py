"""Deterministic Vimshottari Mahadasha, Antardasha, and Pratyantardasha."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from bvr_star.chart.constants import DASHA_LORDS, DASHA_YEARS
from bvr_star.models.chart import PlanetPlacement
from bvr_star.models.dasha import DashaPeriod, VimshottariTimeline

SIDEREAL_CYCLE_YEARS = 120.0
VIMSHOTTARI_YEAR_DAYS = 365.25


def _ordered_lords(start_lord: str) -> list[str]:
    start = DASHA_LORDS.index(start_lord)
    return [DASHA_LORDS[(start + offset) % len(DASHA_LORDS)] for offset in range(9)]


def _children(
    parent_lord: str,
    start: datetime,
    end: datetime,
    level: int,
    depth: int,
    reference: datetime,
) -> list[DashaPeriod]:
    if level > depth:
        return []
    duration = end - start
    cursor = start
    result: list[DashaPeriod] = []
    for lord in _ordered_lords(parent_lord):
        child_end = cursor + duration * (DASHA_YEARS[lord] / SIDEREAL_CYCLE_YEARS)
        if lord == _ordered_lords(parent_lord)[-1]:
            child_end = end
        active = cursor <= reference < child_end
        result.append(
            DashaPeriod(
                level=level,
                lord=lord,
                start_utc=cursor,
                end_utc=child_end,
                active=active,
                children=(
                    _children(lord, cursor, child_end, level + 1, depth, reference)
                    if level < 2 or active
                    else []
                ),
            )
        )
        cursor = child_end
    return result


def build_vimshottari(
    moon: PlanetPlacement,
    birth_utc: datetime,
    reference_date: date,
    depth: int = 3,
) -> VimshottariTimeline:
    """Build the full 120-year cycle containing birth and nested active periods."""

    reference = datetime.combine(reference_date, datetime.min.time(), UTC)
    start_lord = moon.zodiac.nakshatra_lord
    nakshatra_span = 360.0 / 27.0
    elapsed = (moon.zodiac.longitude % nakshatra_span) / nakshatra_span
    balance = 1.0 - elapsed
    birth_lord_years = DASHA_YEARS[start_lord]
    birth_lord_start = birth_utc - timedelta(
        days=birth_lord_years * elapsed * VIMSHOTTARI_YEAR_DAYS
    )
    cursor = birth_lord_start
    periods: list[DashaPeriod] = []
    for lord in _ordered_lords(start_lord):
        end = cursor + timedelta(days=DASHA_YEARS[lord] * VIMSHOTTARI_YEAR_DAYS)
        periods.append(
            DashaPeriod(
                level=1,
                lord=lord,
                start_utc=cursor,
                end_utc=end,
                active=cursor <= reference < end,
                children=_children(lord, cursor, end, 2, depth, reference),
            )
        )
        cursor = end
    return VimshottariTimeline(
        birth_nakshatra=moon.zodiac.nakshatra_name,
        birth_nakshatra_lord=start_lord,
        elapsed_fraction_at_birth=elapsed,
        balance_fraction_at_birth=balance,
        balance_years_at_birth=birth_lord_years * balance,
        reference_utc=reference,
        periods=periods,
    )
