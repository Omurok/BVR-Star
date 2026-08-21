"""Versioned celestial body registry."""

from __future__ import annotations

import swisseph as swe

BODY_IDS: dict[str, int] = {
    "sun": swe.SUN,
    "moon": swe.MOON,
    "mercury": swe.MERCURY,
    "venus": swe.VENUS,
    "mars": swe.MARS,
    "jupiter": swe.JUPITER,
    "saturn": swe.SATURN,
    "rahu": swe.MEAN_NODE,
}
