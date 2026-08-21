"""Conservative Parashari aspect, conjunction, dignity, and yoga detection."""

from __future__ import annotations

from bvr_star.models.analysis import AnalysisFact, EvidenceRef, RuleAnalysis
from bvr_star.models.chart import NatalChart

EXALTATION = {"sun": 0, "moon": 1, "mars": 9, "mercury": 5, "jupiter": 3, "venus": 11, "saturn": 6}
DEBILITATION = {"sun": 6, "moon": 7, "mars": 3, "mercury": 11, "jupiter": 9, "venus": 5, "saturn": 0}
OWN_SIGNS = {
    "sun": {4}, "moon": {3}, "mars": {0, 7}, "mercury": {2, 5},
    "jupiter": {8, 11}, "venus": {1, 6}, "saturn": {9, 10},
}
ASPECT_OFFSETS = {
    "mars": {3, 6, 7}, "jupiter": {4, 6, 8}, "saturn": {2, 6, 9},
}
NATURAL_BENEFICS = {"jupiter", "venus", "mercury", "moon"}


def _dignity(body: str, sign: int) -> str:
    if body in EXALTATION and EXALTATION[body] == sign:
        return "exalted"
    if body in DEBILITATION and DEBILITATION[body] == sign:
        return "debilitated"
    if sign in OWN_SIGNS.get(body, set()):
        return "own_sign"
    return "neutral"


def _angular_distance(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def evaluate_chart(chart: NatalChart) -> RuleAnalysis:
    facts: list[AnalysisFact] = []
    dignity = {key: _dignity(key, planet.zodiac.sign_index) for key, planet in chart.planets.items()}
    for key, status in dignity.items():
        if status != "neutral":
            facts.append(AnalysisFact(
                id=f"dignity.{key}.{status}", category="dignity",
                title_zh=f"{key}：{status}", title_en=f"{key}: {status}", strength=0.9,
                data={"planet": key, "status": status},
                evidence=EvidenceRef(ids=[f"planet.{key}"], explanation="Classical sign dignity lookup."),
            ))
    keys = list(chart.planets)
    for i, first in enumerate(keys):
        for second in keys[i + 1:]:
            distance = _angular_distance(chart.planets[first].zodiac.longitude, chart.planets[second].zodiac.longitude)
            if distance <= 8.0:
                facts.append(AnalysisFact(
                    id=f"conjunction.{first}.{second}", category="conjunction",
                    title_zh=f"{first} 與 {second} 合相", title_en=f"{first} conjunct {second}",
                    strength=max(0.25, 1.0 - distance / 10.0),
                    data={"planets": [first, second], "orb_degrees": distance},
                    evidence=EvidenceRef(ids=[f"planet.{first}", f"planet.{second}"], explanation="Absolute ecliptic separation is at most 8 degrees."),
                ))
    for source, source_planet in chart.planets.items():
        offsets = ASPECT_OFFSETS.get(source, {6})
        for target, target_planet in chart.planets.items():
            if source == target:
                continue
            offset = (target_planet.zodiac.sign_index - source_planet.zodiac.sign_index) % 12
            if offset in offsets:
                facts.append(AnalysisFact(
                    id=f"aspect.{source}.{target}.{offset + 1}", category="aspect",
                    title_zh=f"{source} 照射 {target}", title_en=f"{source} aspects {target}", strength=0.75,
                    data={"source": source, "target": target, "parasari_house_distance": offset + 1},
                    evidence=EvidenceRef(ids=[f"planet.{source}", f"planet.{target}"], explanation="Parashari whole-sign graha drishti."),
                ))
    angular_houses = {1, 4, 7, 10}
    for body, status in dignity.items():
        if status in {"own_sign", "exalted"} and chart.planets[body].house in angular_houses:
            facts.append(AnalysisFact(
                id=f"yoga.mahapurusha.{body}", category="yoga",
                title_zh=f"{body} 大士瑜伽條件", title_en=f"{body} Mahapurusha condition",
                strength=0.92, data={"planet": body, "house": chart.planets[body].house, "dignity": status},
                evidence=EvidenceRef(ids=[f"planet.{body}", "angle.ascendant"], explanation="Planet is exalted or in own sign in a kendra from Lagna."),
            ))
    for body in NATURAL_BENEFICS:
        planet = chart.planets.get(body)
        if planet and planet.house in {2, 5, 9, 11}:
            facts.append(AnalysisFact(
                id=f"support.benefic.{body}.house{planet.house}", category="house_support",
                title_zh=f"天然吉星 {body} 支持第 {planet.house} 宮", title_en=f"Natural benefic {body} supports house {planet.house}",
                strength=0.62, data={"planet": body, "house": planet.house},
                evidence=EvidenceRef(ids=[f"planet.{body}", "angle.ascendant"], explanation="Natural benefic occupies a trine or wealth/gains house."),
            ))
    return RuleAnalysis(dignity=dignity, facts=facts)
