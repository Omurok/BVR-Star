"""Thread-safe Raman sidereal calculations with explicit source provenance."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from threading import RLock

import swisseph as swe

from bvr_star.ephemeris.constants import BODY_IDS
from bvr_star.models.ephemeris import AnglePosition, BodyPosition, EphemerisSnapshot
from bvr_star.models.location import ResolvedLocation
from bvr_star.models.time import NormalizedInstant


class SwissEphemeris:
    """The only project component allowed to call the Swiss Ephemeris API."""

    _lock = RLock()

    def __init__(self, ephe_path: str | Path | None = None) -> None:
        configured = ephe_path or os.getenv("BVR_EPHE_PATH") or Path.cwd() / "ephe"
        self.ephe_path = Path(configured).resolve()

    @property
    def required_files(self) -> tuple[Path, Path]:
        return self.ephe_path / "sepl_18.se1", self.ephe_path / "semo_18.se1"

    def files_ready(self) -> bool:
        return all(path.is_file() and path.stat().st_size > 0 for path in self.required_files)

    @staticmethod
    def _utc_julian(utc_datetime: datetime) -> tuple[float, float]:
        seconds = utc_datetime.second + utc_datetime.microsecond / 1_000_000
        jd_et, jd_ut = swe.utc_to_jd(
            utc_datetime.year,
            utc_datetime.month,
            utc_datetime.day,
            utc_datetime.hour,
            utc_datetime.minute,
            seconds,
            swe.GREG_CAL,
        )
        return float(jd_et), float(jd_ut)

    @staticmethod
    def _source(return_flags: list[int]) -> tuple[str, list[str]]:
        if return_flags and all(flags & swe.FLG_SWIEPH for flags in return_flags):
            return "swiss_ephemeris", []
        if return_flags and all(flags & swe.FLG_MOSEPH for flags in return_flags):
            return "moshier", ["EPHEMERIS_FALLBACK"]
        return "mixed", ["EPHEMERIS_FALLBACK"]

    def _calculate_bodies_locked(self, jd_ut: float) -> tuple[dict[str, BodyPosition], list[int]]:
        flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
        bodies: dict[str, BodyPosition] = {}
        return_flags: list[int] = []
        for key, body_id in BODY_IDS.items():
            coordinates, returned = swe.calc_ut(jd_ut, body_id, flags)
            returned_int = int(returned)
            return_flags.append(returned_int)
            bodies[key] = BodyPosition(
                key=key,
                longitude=float(coordinates[0] % 360),
                latitude=float(coordinates[1]),
                distance_au=float(coordinates[2]),
                speed_longitude=float(coordinates[3]),
                retrograde=float(coordinates[3]) < 0,
                return_flags=returned_int,
            )
        rahu = bodies["rahu"]
        bodies["ketu"] = BodyPosition(
            key="ketu",
            longitude=(rahu.longitude + 180.0) % 360.0,
            latitude=-rahu.latitude,
            distance_au=rahu.distance_au,
            speed_longitude=rahu.speed_longitude,
            retrograde=rahu.retrograde,
            return_flags=rahu.return_flags,
        )
        return bodies, return_flags

    def calculate_bodies(self, utc_datetime: datetime) -> dict[str, BodyPosition]:
        """Calculate bodies only, used by the missing-time date-range response."""

        with self._lock:
            swe.set_ephe_path(str(self.ephe_path))
            swe.set_sid_mode(swe.SIDM_RAMAN)
            _, jd_ut = self._utc_julian(utc_datetime)
            bodies, _ = self._calculate_bodies_locked(jd_ut)
            return bodies

    def calculate(
        self,
        instant: NormalizedInstant,
        location: ResolvedLocation,
    ) -> EphemerisSnapshot:
        """Calculate the Raman sidereal bodies, Ascendant, and MC."""

        with self._lock:
            swe.set_ephe_path(str(self.ephe_path))
            swe.set_sid_mode(swe.SIDM_RAMAN)
            jd_et, jd_ut = self._utc_julian(instant.utc_datetime)
            bodies, returned_flags = self._calculate_bodies_locked(jd_ut)
            _, ascmc = swe.houses_ex(
                jd_ut,
                location.latitude,
                location.longitude,
                b"W",
                swe.FLG_SIDEREAL,
            )
            source, warnings = self._source(returned_flags)
            combined_flags = returned_flags[0]
            for value in returned_flags[1:]:
                combined_flags &= value
            version_value = getattr(swe, "version", "unknown")
            version = version_value() if callable(version_value) else str(version_value)
            return EphemerisSnapshot(
                jd_et=jd_et,
                jd_ut=jd_ut,
                ayanamsha=float(swe.get_ayanamsa_ut(jd_ut)),
                ayanamsha_name=str(swe.get_ayanamsa_name(swe.SIDM_RAMAN)),
                bodies=bodies,
                ascendant=AnglePosition(key="ascendant", longitude=float(ascmc[0] % 360)),
                mc=AnglePosition(key="mc", longitude=float(ascmc[1] % 360)),
                source=source,
                required_swiss_flag=int(swe.FLG_SWIEPH),
                return_flags=combined_flags,
                library_version=version,
                warnings=warnings,
            )
