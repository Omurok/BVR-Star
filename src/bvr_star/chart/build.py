"""Build the typed D1 whole-sign natal chart."""

from __future__ import annotations

from bvr_star.chart.constants import SIGN_LORDS
from bvr_star.chart.zodiac import whole_sign_house, zodiac_placement
from bvr_star.models.chart import NatalChart, PlanetPlacement
from bvr_star.models.ephemeris import EphemerisSnapshot


def build_natal_chart(snapshot: EphemerisSnapshot) -> NatalChart:
    ascendant = zodiac_placement(snapshot.ascendant.longitude)
    planets: dict[str, PlanetPlacement] = {}
    for key, body in snapshot.bodies.items():
        zodiac = zodiac_placement(body.longitude)
        planets[key] = PlanetPlacement(
            key=key,
            zodiac=zodiac,
            house=whole_sign_house(body.longitude, ascendant.longitude),
            latitude=body.latitude,
            distance_au=body.distance_au,
            speed_longitude=body.speed_longitude,
            retrograde=body.retrograde,
            return_flags=body.return_flags,
            evidence_id=f"D1:{key}",
        )
    house_signs = {
        house: (ascendant.sign_index + house - 1) % 12 for house in range(1, 13)
    }
    return NatalChart(
        ascendant=ascendant,
        mc=zodiac_placement(snapshot.mc.longitude),
        planets=planets,
        house_signs=house_signs,
        house_lords={house: SIGN_LORDS[sign] for house, sign in house_signs.items()},
    )
