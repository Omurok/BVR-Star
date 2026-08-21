"""Low-volume Nominatim geocoder with policy-compatible throttling."""

from __future__ import annotations

import hashlib
import json
import os
from threading import Lock
from typing import Any

from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from redis import Redis

from bvr_star.models.errors import BVRStarError
from bvr_star.models.location import LocationCandidate


class NominatimGeocoder:
    name = "openstreetmap_nominatim"
    _cache_prefix = "bvr-star:geocode:v1:"
    _default_cache_ttl_seconds = 30 * 24 * 60 * 60

    def __init__(self, cache_client: Any | None = None, cache_ttl_seconds: int | None = None) -> None:
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
        self._cache_client = cache_client if cache_client is not None else self._build_cache_client()
        self._cache_ttl_seconds = (
            cache_ttl_seconds
            if cache_ttl_seconds is not None
            else int(os.getenv("BVR_GEOCODER_CACHE_TTL_SECONDS", str(self._default_cache_ttl_seconds)))
        )
        if self._cache_ttl_seconds <= 0:
            raise ValueError("BVR_GEOCODER_CACHE_TTL_SECONDS must be greater than zero")

    @staticmethod
    def _build_cache_client() -> Any | None:
        cache_url = os.getenv("BVR_GEOCODER_CACHE_URL")
        if not cache_url:
            return None
        return Redis.from_url(
            cache_url,
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
        )

    @classmethod
    def _cache_key(cls, normalized: str) -> str:
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"{cls._cache_prefix}{digest}"

    def _read_remote_cache(self, normalized: str) -> list[LocationCandidate] | None:
        if self._cache_client is None:
            return None
        try:
            payload = self._cache_client.get(self._cache_key(normalized))
            if payload is None:
                return None
            decoded = json.loads(payload)
            return [LocationCandidate.model_validate(item) for item in decoded]
        except Exception:
            # The cache is an optimization; a Redis outage must not take down geocoding.
            return None

    def _write_remote_cache(self, normalized: str, candidates: list[LocationCandidate]) -> None:
        if self._cache_client is None:
            return
        payload = json.dumps(
            [candidate.model_dump(mode="json") for candidate in candidates],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        try:
            self._cache_client.setex(
                self._cache_key(normalized),
                self._cache_ttl_seconds,
                payload,
            )
        except Exception:
            # The cache is an optimization; a Redis outage must not take down geocoding.
            return

    def search(self, query: str) -> list[LocationCandidate]:
        normalized = " ".join(query.strip().split())
        with self._lock:
            if normalized in self._cache:
                return list(self._cache[normalized])
        remote_cached = self._read_remote_cache(normalized)
        if remote_cached is not None:
            with self._lock:
                self._cache[normalized] = list(remote_cached)
            return list(remote_cached)
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
        self._write_remote_cache(normalized, candidates)
        return list(candidates)
