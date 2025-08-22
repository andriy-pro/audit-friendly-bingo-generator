from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List


@dataclass
class Feasibility:
    feasible: bool
    reasons: List[str]


def check_uniformity_strict(*, R: int, T: int, m: int, n: int) -> Feasibility:
    P = T * m * n
    ok = (P % R) == 0
    return Feasibility(feasible=ok, reasons=[] if ok else ["P % R != 0 for strict uniformity"])


def compute_near_uniform_targets(*, R: int, T: int, m: int, n: int) -> tuple[int, int]:
    P = T * m * n
    base = P // R
    remainder = P % R
    return base, remainder


def check_uniqueness_capacity(
    *, R: int, T: int, m: int, n: int, unique_scope: list[str]
) -> Feasibility:
    scope = sorted(set(unique_scope))
    reasons: List[str] = []
    ok_row = True
    ok_col = True
    if "row_sets" in scope:
        ok_row = T * m <= math.comb(R, n)
        if not ok_row:
            reasons.append("row_sets capacity exceeded: T*m > C(R,n)")
    if "col_sets" in scope:
        ok_col = T * n <= math.comb(R, m)
        if not ok_col:
            reasons.append("col_sets capacity exceeded: T*n > C(R,m)")
    feasible = ok_row and ok_col
    return Feasibility(feasible=feasible, reasons=reasons)
