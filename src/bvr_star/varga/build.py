"""Build all supported divisional charts from one D1 chart."""

from __future__ import annotations

from bvr_star.chart.constants import SIGN_KEYS, SIGN_LORDS, SIGN_NAMES_EN, SIGN_NAMES_ZH
from bvr_star.models.chart import NatalChart
from bvr_star.models.varga import VargaChart, VargaPlacement
from bvr_star.varga.formulas import (
    SUPPORTED_DIVISIONS,
    boundary_distance,
    varga_sign_and_part,
)


def _placement(key: str, longitude: float, division: int) -> VargaPlacement:
    sign, part = varga_sign_and_part(longitude, division)
    return VargaPlacement(
        key=key,
        division=division,
        sign_index=sign,
        sign_key=SIGN_KEYS[sign],
        sign_name_en=SIGN_NAMES_EN[sign],
        sign_name_zh=SIGN_NAMES_ZH[sign],
        sign_lord=SIGN_LORDS[sign],
        part_index=part,
        boundary_distance_degrees=boundary_distance(longitude, division),
        evidence_id=f"D{division}:{key}",
    )


def build_vargas(chart: NatalChart) -> dict[str, VargaChart]:
    charts: dict[str, VargaChart] = {}
    for division in SUPPORTED_DIVISIONS:
        key = f"D{division}"
        charts[key] = VargaChart(
            key=key,
            division=division,
            ascendant=_placement("ascendant", chart.ascendant.longitude, division),
            placements={
                planet_key: _placement(planet_key, planet.zodiac.longitude, division)
                for planet_key, planet in chart.planets.items()
            },
        )
    return charts
