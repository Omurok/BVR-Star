"""Produce compact AI-ready data solely from typed calculated results."""

from __future__ import annotations

from typing import Any

from bvr_star.models.analysis import RuleAnalysis
from bvr_star.models.chart import NatalChart
from bvr_star.models.dasha import DashaPeriod, VimshottariTimeline
from bvr_star.models.response import SensitivityResult
from bvr_star.models.varga import VargaChart


def _active_path(periods: list[DashaPeriod]) -> list[dict[str, Any]]:
    for period in periods:
        if period.active:
            return [{
                "level": period.level,
                "lord": period.lord,
                "start_utc": period.start_utc.isoformat(),
                "end_utc": period.end_utc.isoformat(),
            }] + _active_path(period.children)
    return []


def build_llm_context(
    chart: NatalChart,
    vargas: dict[str, VargaChart],
    dashas: VimshottariTimeline,
    rules: RuleAnalysis,
    sensitivity: SensitivityResult,
    warnings: list[str],
) -> dict[str, Any]:
    planets = {
        key: {
            "sign": value.zodiac.sign_name_zh,
            "sign_key": value.zodiac.sign_key,
            "degree": round(value.zodiac.degree_in_sign, 6),
            "house": value.house,
            "nakshatra": value.zodiac.nakshatra_name,
            "pada": value.zodiac.pada,
            "retrograde": value.retrograde,
            "evidence_id": value.evidence_id,
        }
        for key, value in chart.planets.items()
    }
    important = sorted(rules.facts, key=lambda fact: fact.strength, reverse=True)[:30]
    return {
        "instruction": "Use these computed facts as the sole chart data; do not recalculate degrees.",
        "ascendant": {
            "sign": chart.ascendant.sign_name_zh,
            "sign_key": chart.ascendant.sign_key,
            "degree": round(chart.ascendant.degree_in_sign, 6),
            "nakshatra": chart.ascendant.nakshatra_name,
            "pada": chart.ascendant.pada,
            "evidence_id": "angle.ascendant",
        },
        "planets": planets,
        "house_lords": chart.house_lords,
        "varga_ascendants": {
            key: {"sign": value.ascendant.sign_name_zh, "sign_key": value.ascendant.sign_key}
            for key, value in vargas.items()
        },
        "active_dasha": _active_path(dashas.periods),
        "important_rule_facts": [fact.model_dump(mode="json") for fact in important],
        "sensitivity": sensitivity.model_dump(mode="json"),
        "warnings": warnings,
        "interpretation_boundary": "Astrology is a traditional symbolic framework, not a scientific, medical, legal, or financial diagnosis.",
    }
