"""High-level chart orchestration used identically by Python, CLI, and HTTP."""

from __future__ import annotations

from datetime import timedelta

from bvr_star import version
from bvr_star.chart.build import build_natal_chart
from bvr_star.chart.zodiac import zodiac_placement
from bvr_star.dasha.vimshottari import build_vimshottari
from bvr_star.ephemeris.swiss import SwissEphemeris
from bvr_star.llm_context import build_llm_context
from bvr_star.location.contracts import Geocoder
from bvr_star.location.nominatim import NominatimGeocoder
from bvr_star.location.resolve import resolve_location
from bvr_star.models.ephemeris import EphemerisSnapshot
from bvr_star.models.request import ChartRequest
from bvr_star.models.response import (
    ChartResponse,
    ChartResult,
    DateRangeResponse,
    Provenance,
    SensitivityResult,
)
from bvr_star.models.time import NormalizedDateRange, NormalizedInstant
from bvr_star.rules.evaluate import evaluate_chart
from bvr_star.timekeeping.normalize import normalize_birth_time
from bvr_star.varga.build import build_vargas


class ChartService:
    """One deterministic entry point for all supported interfaces."""

    def __init__(self, ephemeris: SwissEphemeris | None = None, geocoder: Geocoder | None = None) -> None:
        self.ephemeris = ephemeris or SwissEphemeris()
        self.geocoder = geocoder if geocoder is not None else NominatimGeocoder()

    def _provenance(self, snapshot: EphemerisSnapshot | None = None) -> Provenance:
        return Provenance(
            engine="BVR-Star", engine_version=version.__version__,
            calculation_profile="bvr_raman_v1", ephemeris_library="pyswisseph",
            ephemeris_version=snapshot.library_version if snapshot else "unknown",
            ephemeris_source=snapshot.source if snapshot else ("swiss_ephemeris" if self.ephemeris.files_ready() else "unavailable"),
            ephemeris_files_ready=self.ephemeris.files_ready(),
            ayanamsha_degrees=snapshot.ayanamsha if snapshot else None,
            ayanamsha_name=snapshot.ayanamsha_name if snapshot else None,
        )

    def _sensitivity(self, request: ChartRequest, location, instant: NormalizedInstant, baseline) -> SensitivityResult:
        minutes = request.birth.time_accuracy_minutes
        if minutes <= 0:
            return SensitivityResult(evaluated=False, accuracy_minutes=0, stable=["recorded_birth_instant"])
        endpoints = []
        signatures = []
        for direction in (-1, 1):
            shifted_utc = instant.utc_datetime + timedelta(minutes=direction * minutes)
            shifted_local = shifted_utc.astimezone(instant.local_datetime.tzinfo)
            shifted = NormalizedInstant(
                local_datetime=shifted_local, utc_datetime=shifted_utc, timezone=instant.timezone,
                utc_offset_seconds=int(shifted_local.utcoffset().total_seconds()), fold=shifted_local.fold,
            )
            snapshot = self.ephemeris.calculate(shifted, location)
            chart = build_natal_chart(snapshot)
            vargas = build_vargas(chart)
            signature = {
                "ascendant_sign": chart.ascendant.sign_key,
                "planet_houses": {key: value.house for key, value in chart.planets.items()},
                "varga_ascendants": {key: value.ascendant.sign_key for key, value in vargas.items()},
            }
            signatures.append(signature)
            endpoints.append({"local_datetime": shifted.local_datetime.isoformat(), **signature})
        base_vargas = build_vargas(baseline)
        base_signature = {
            "ascendant_sign": baseline.ascendant.sign_key,
            "planet_houses": {key: value.house for key, value in baseline.planets.items()},
            "varga_ascendants": {key: value.ascendant.sign_key for key, value in base_vargas.items()},
        }
        changed, stable = [], []
        for field in ("ascendant_sign", "planet_houses", "varga_ascendants"):
            target = changed if any(item[field] != base_signature[field] for item in signatures) else stable
            target.append(field)
        return SensitivityResult(evaluated=True, accuracy_minutes=minutes, stable=stable, changed=changed, endpoints=endpoints)

    def _date_range(self, request: ChartRequest, location, time_range: NormalizedDateRange) -> DateRangeResponse:
        start = self.ephemeris.calculate_bodies(time_range.start_utc)
        end = self.ephemeris.calculate_bodies(time_range.end_utc - timedelta(microseconds=1))
        ranges, crossings = {}, []
        for key in start:
            first, last = zodiac_placement(start[key].longitude), zodiac_placement(end[key].longitude)
            ranges[key] = {
                "start_longitude": start[key].longitude, "end_longitude": end[key].longitude,
                "start_sign": first.sign_key, "end_sign": last.sign_key,
                "start_nakshatra": first.nakshatra_name, "end_nakshatra": last.nakshatra_name,
            }
            if first.sign_key != last.sign_key or first.nakshatra_name != last.nakshatra_name:
                crossings.append({"body": key, "sign_changed": first.sign_key != last.sign_key, "nakshatra_changed": first.nakshatra_name != last.nakshatra_name})
        warnings = ["BIRTH_TIME_MISSING", "TIME_SENSITIVE_FIELDS_OMITTED"]
        return DateRangeResponse(
            request=request, settings=request.settings, location=location, time=time_range,
            provenance=self._provenance(), planetary_ranges=ranges, crossings=crossings,
            omitted_time_sensitive_fields=["ascendant", "houses", "varga_ascendants", "dashas", "rules_requiring_houses", "sensitivity"],
            warnings=warnings,
            llm_context={"mode": "date_range", "planetary_ranges": ranges, "crossings": crossings, "warnings": warnings, "instruction": "Do not infer an Ascendant, houses, divisional ascendants, or dasha balance without a birth time."},
        )

    def calculate(self, request: ChartRequest | dict) -> ChartResult:
        if not isinstance(request, ChartRequest):
            request = ChartRequest.model_validate(request)
        location = resolve_location(request.birth, self.geocoder)
        normalized = normalize_birth_time(request.birth, location.timezone)
        if isinstance(normalized, NormalizedDateRange):
            return self._date_range(request, location, normalized)
        snapshot = self.ephemeris.calculate(normalized, location)
        chart = build_natal_chart(snapshot)
        vargas = build_vargas(chart)
        dashas = build_vimshottari(chart.planets["moon"], normalized.utc_datetime, request.options.reference_date, request.options.dasha_depth)
        rules = evaluate_chart(chart)
        sensitivity = self._sensitivity(request, location, normalized, chart)
        warnings = list(snapshot.warnings)
        llm = build_llm_context(chart, vargas, dashas, rules, sensitivity, warnings)
        return ChartResponse(
            request=request, settings=request.settings, location=location, time=normalized,
            provenance=self._provenance(snapshot), chart=chart, vargas=vargas, dashas=dashas,
            rules=rules, sensitivity=sensitivity, warnings=warnings, llm_context=llm,
        )
