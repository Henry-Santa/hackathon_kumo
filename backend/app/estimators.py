from __future__ import annotations

from typing import Optional, Tuple


# Approximate ACT-SAT concordance mapping (2018). Ranges are inclusive.
_ACT_TO_SAT_RANGE: dict[int, Tuple[int, int]] = {
    36: (1590, 1600),
    35: (1540, 1580),
    34: (1490, 1530),
    33: (1450, 1480),
    32: (1420, 1440),
    31: (1390, 1410),
    30: (1360, 1380),
    29: (1330, 1350),
    28: (1300, 1320),
    27: (1260, 1290),
    26: (1230, 1250),
    25: (1200, 1220),
    24: (1160, 1190),
    23: (1130, 1150),
    22: (1100, 1120),
    21: (1060, 1090),
    20: (1030, 1050),
    19: (990, 1020),
    18: (960, 980),
    17: (920, 950),
    16: (880, 910),
    15: (830, 870),
    14: (780, 820),
    13: (730, 770),
    12: (690, 720),
    11: (650, 680),
    10: (620, 640),
    9: (590, 610),
}


def estimate_act_from_sat_total(sat_total: int) -> int:
    """Estimate ACT composite from SAT total using concordance ranges.

    Values below the minimum clamp to 9, above the max clamp to 36.
    """
    if sat_total is None:
        raise ValueError("sat_total is required")
    sat_total = int(sat_total)
    if sat_total <= 610:
        return 9
    if sat_total >= 1590:
        return 36
    # Find the ACT whose SAT range contains sat_total; if multiple, choose highest ACT
    for act in sorted(_ACT_TO_SAT_RANGE.keys(), reverse=True):
        lo, hi = _ACT_TO_SAT_RANGE[act]
        if lo <= sat_total <= hi:
            return act
    # Fallback: interpolate linearly between 610 and 1590
    return max(9, min(36, round(9 + (sat_total - 610) * (27 / (1590 - 610)))))


def estimate_sat_total_from_act(act: int) -> int:
    """Estimate SAT total from ACT composite using concordance ranges.

    Uses midpoint of the SAT range for the given ACT.
    Clamps to 400..1600.
    """
    if act is None:
        raise ValueError("act is required")
    act = int(act)
    act = max(9, min(36, act))
    sat_range = _ACT_TO_SAT_RANGE.get(act)
    if sat_range:
        lo, hi = sat_range
        return int(round((lo + hi) / 2, -1))  # round to nearest 10
    # Fallback linear mapping roughly aligning 9->610 and 36->1590
    approx = int(round(610 + (act - 9) * ((1590 - 610) / 27), -1))
    return max(400, min(1600, approx))


def estimate_sat_parts_from_total(
    sat_total: int, known_erw: Optional[int] = None, known_math: Optional[int] = None
) -> Tuple[Optional[int], Optional[int]]:
    """Estimate SAT ERW and Math from total. Attempts to split evenly, respecting 200..800 bounds.

    If one part is known, assigns the other as the remainder clamped to 200..800.
    Returns (erw, math) which may include None if infeasible.
    """
    if sat_total is None:
        return known_erw, known_math
    sat_total = int(sat_total)
    if known_erw is not None and known_math is not None:
        return int(known_erw), int(known_math)

    if known_erw is not None:
        other = max(200, min(800, sat_total - int(known_erw)))
        return int(known_erw), int(other)

    if known_math is not None:
        other = max(200, min(800, sat_total - int(known_math)))
        return int(other), int(known_math)

    # Even split if nothing is known
    erw = int(round(sat_total / 2, -1))
    math = sat_total - erw
    erw = max(200, min(800, erw))
    math = max(200, min(800, math))
    return erw, math


