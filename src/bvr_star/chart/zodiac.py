"""Pure longitude-to-zodiac transformations."""

from __future__ import annotations

import math

from bvr_star.chart.constants import (
    NAKSHATRA_KEYS,
    NAKSHATRA_LORDS,
    NAKSHATRA_NAMES,
    SIGN_KEYS,
    SIGN_LORDS,
    SIGN_NAMES_EN,
    SIGN_NAMES_ZH,
)
from bvr_star.models.chart import ZodiacPlacement

NAKSHATRA_LENGTH = 360.0 / 27.0
PADA_LENGTH = 360.0 / 108.0


def normalize_longitude(longitude: float) -> float:
    normalized = longitude % 360.0
    return 0.0 if math.isclose(normalized, 360.0, abs_tol=1e-12) else normalized


def zodiac_placement(longitude: float) -> ZodiacPlacement:
    normalized = normalize_longitude(longitude)
    sign_index = min(int(normalized // 30.0), 11)
    degree_in_sign = normalized - sign_index * 30.0
    nakshatra_index = min(int(normalized / NAKSHATRA_LENGTH), 26)
    within_nakshatra = normalized - nakshatra_index * NAKSHATRA_LENGTH
    pada = min(int(within_nakshatra / PADA_LENGTH) + 1, 4)
    return ZodiacPlacement(
        longitude=normalized,
        sign_index=sign_index,
        sign_key=SIGN_KEYS[sign_index],
        sign_name_en=SIGN_NAMES_EN[sign_index],
        sign_name_zh=SIGN_NAMES_ZH[sign_index],
        sign_lord=SIGN_LORDS[sign_index],
        degree_in_sign=degree_in_sign,
        nakshatra_index=nakshatra_index,
        nakshatra_key=NAKSHATRA_KEYS[nakshatra_index],
        nakshatra_name=NAKSHATRA_NAMES[nakshatra_index],
        nakshatra_lord=NAKSHATRA_LORDS[nakshatra_index],
        pada=pada,
    )


def whole_sign_house(longitude: float, ascendant_longitude: float) -> int:
    planet_sign = int(normalize_longitude(longitude) // 30.0)
    ascendant_sign = int(normalize_longitude(ascendant_longitude) // 30.0)
    return ((planet_sign - ascendant_sign) % 12) + 1
