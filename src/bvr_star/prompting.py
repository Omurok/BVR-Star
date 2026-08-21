"""Versioned prompt-template access for CLI and HTTP."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from bvr_star.models.errors import BVRStarError


def render_prompt(language: str = "zh-TW") -> str:
    if language not in {"zh-TW", "en"}:
        raise BVRStarError("UNSUPPORTED_LANGUAGE", "Prompt language must be zh-TW or en.")
    resource = files("bvr_star").joinpath("prompt_templates", language, "full-reading.md")
    try:
        return resource.read_text(encoding="utf-8")
    except FileNotFoundError:
        development_copy = Path(__file__).resolve().parents[2] / "prompts" / language / "full-reading.md"
        return development_copy.read_text(encoding="utf-8")
