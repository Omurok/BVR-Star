"""Machine-readable supported feature configuration."""

from __future__ import annotations

import os

from bvr_star.varga.formulas import SUPPORTED_DIVISIONS
from bvr_star.version import __version__


def public_config() -> dict:
    return {
        "name": "BVR-Star", "version": __version__, "schema_version": "bvr-star-response-v1",
        "profiles": ["bvr_raman_v1"], "supported_date_range": ["1900-01-01", "2099-12-31"],
        "vargas": [f"D{value}" for value in SUPPORTED_DIVISIONS],
        "dasha_depth_max": 3, "languages": ["zh-TW", "en"],
        "limits": {
            "request_body_bytes": int(os.getenv("BVR_MAX_BODY_BYTES", "16384")),
            "charts_per_ip_per_minute": int(os.getenv("BVR_CHART_RATE", "30")),
            "geocodes_per_ip_per_minute": int(os.getenv("BVR_GEOCODE_RATE", "5")),
        },
        "privacy": "Requests and responses are not persisted by the application.",
        "disclaimer": "Traditional astrology calculation; not scientific, medical, legal, or financial advice.",
    }
