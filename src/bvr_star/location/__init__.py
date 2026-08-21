"""Birthplace resolution."""

from bvr_star.location.nominatim import NominatimGeocoder
from bvr_star.location.resolve import resolve_location

__all__ = ["NominatimGeocoder", "resolve_location"]
