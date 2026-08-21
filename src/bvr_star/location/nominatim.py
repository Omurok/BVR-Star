"""Low-volume Nominatim geocoder with policy-compatible throttling."""

from __future__ import annotations

from threading import Lock
from typing import Any

from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim

from bvr_star.models.errors import BVRStarError
from bvr_star.models.location import LocationCandidate


class NominatimGeocoder:
    name = "openstreetmap_nominatim"

    def __init__(self) -> None:
        geocoder = Nominatim(
            user_agent="BVR-Star/0.1 (+https://github.com/Omurok/BVR-Star)",
            timeout=10,
        )
        self._search = RateLimiter(
            geocoder.geocode,
            min_delay_seconds=1.0,
            max_retries=1,
            error_wait_seconds=2.0,
            swallow_exceptions=False,
        )
        self._cache: dict[str, list[LocationCandidate]] = {}
        self._lock = Lock()

    def search(self, query: str) -> list[LocationCandidate]:
        normalized = " ".join(query.strip().split())
        with self._lock:
            if normalized in self._cache:
                return list(self._cache[normalized])
        try:
            raw_results = self._search(
                normalized,
                exactly_one=False,
                limit=5,
                addressdetails=True,
                language="en",
            )
        except Exception as exc:
            raise BVRStarError(
                "GEOCODER_UNAVAILABLE",
                "The address provider is temporarily unavailable.",
                {"provider": self.name},
            ) from exc

        results = raw_results or []
        candidates: list[LocationCandidate] = []
        for result in results:
            raw: dict[str, Any] = dict(getattr(result, "raw", {}) or {})
            candidates.append(
                LocationCandidate(
                    display_name=str(getattr(result, "address", normalized)),
                    latitude=float(result.latitude),
                    longitude=float(result.longitude),
                    rank=max(float(raw.get("importance", 0.0)), 0.0),
                    provider_id=str(raw.get("place_id")) if raw.get("place_id") else None,
                    address=dict(raw.get("address", {}) or {}),
                )
            )
        with self._lock:
            if len(self._cache) >= 256:
                self._cache.pop(next(iter(self._cache)))
            self._cache[normalized] = candidates
        return list(candidates)
