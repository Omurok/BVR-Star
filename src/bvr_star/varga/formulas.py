"""Versioned Parashari divisional-chart formulas."""

from __future__ import annotations

from bvr_star.chart.zodiac import normalize_longitude
from bvr_star.models.errors import BVRStarError

SUPPORTED_DIVISIONS = (2, 3, 4, 7, 9, 10, 12, 16, 20, 24, 27, 30, 40, 45, 60)


def _equal_part(degree: float, division: int) -> int:
    size = 30.0 / division
    return min(int(degree / size), division - 1)


def _modality(sign: int) -> int:
    return sign % 3  # 0 movable, 1 fixed, 2 dual


def _d30(sign: int, degree: float) -> tuple[int, int]:
    if sign % 2 == 0:
        bounds = (5.0, 10.0, 18.0, 25.0, 30.0)
        outputs = (0, 10, 8, 2, 6)
    else:
        bounds = (5.0, 12.0, 20.0, 25.0, 30.0)
        outputs = (1, 5, 11, 9, 7)
    for part, upper in enumerate(bounds):
        if degree < upper or part == len(bounds) - 1:
            return outputs[part], part
    raise AssertionError("unreachable D30 degree")


def varga_sign_and_part(longitude: float, division: int) -> tuple[int, int]:
    if division not in SUPPORTED_DIVISIONS:
        raise BVRStarError(
            "UNSUPPORTED_VARGA",
            f"D{division} is not supported by parasari_shodashavarga_v1.",
            {"supported": list(SUPPORTED_DIVISIONS)},
        )
    normalized = normalize_longitude(longitude)
    sign = int(normalized // 30.0)
    degree = normalized - sign * 30.0
    if division == 30:
        return _d30(sign, degree)
    part = _equal_part(degree, division)
    if division == 2:
        output = (4, 3)[part] if sign % 2 == 0 else (3, 4)[part]
    elif division == 3:
        output = sign + 4 * part
    elif division == 4:
        output = sign + 3 * part
    elif division == 7:
        output = (sign if sign % 2 == 0 else sign + 6) + part
    elif division == 9:
        start = (sign, sign + 8, sign + 4)[_modality(sign)]
        output = start + part
    elif division == 10:
        output = (sign if sign % 2 == 0 else sign + 8) + part
    elif division == 12:
        output = sign + part
    elif division == 16:
        output = (0, 4, 8)[_modality(sign)] + part
    elif division == 20:
        output = (0, 8, 4)[_modality(sign)] + part
    elif division == 24:
        output = (4 if sign % 2 == 0 else 3) + part
    elif division == 27:
        output = (0, 3, 6, 9)[sign % 4] + part
    elif division == 40:
        output = (0 if sign % 2 == 0 else 6) + part
    elif division == 45:
        output = (0, 4, 8)[_modality(sign)] + part
    elif division == 60:
        output = part
    else:
        raise AssertionError(f"unhandled D{division}")
    return output % 12, part


def varga_sign(longitude: float, division: int) -> int:
    return varga_sign_and_part(longitude, division)[0]


def boundary_distance(longitude: float, division: int) -> float:
    normalized = normalize_longitude(longitude)
    sign = int(normalized // 30.0)
    degree = normalized - sign * 30.0
    if division == 30:
        bounds = (
            (0.0, 5.0, 10.0, 18.0, 25.0, 30.0)
            if sign % 2 == 0
            else (0.0, 5.0, 12.0, 20.0, 25.0, 30.0)
        )
        return min(abs(degree - boundary) for boundary in bounds)
    size = 30.0 / division
    remainder = degree % size
    return min(remainder, size - remainder)
