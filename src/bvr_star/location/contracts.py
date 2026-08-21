"""Geocoder boundary used by the deterministic calculation service."""

from __future__ import annotations

from typing import Protocol

from bvr_star.models.location import LocationCandidate


class Geocoder(Protocol):
    name: str

    def search(self, query: str) -> list[LocationCandidate]: ...
