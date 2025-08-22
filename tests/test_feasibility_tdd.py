from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

import pytest
from hypothesis import given, strategies as st


@dataclass
class FeasibilityResult:
    feasible: bool
    reasons: List[str]


def theoretical_feasible(R: int, T: int, m: int, n: int, unique_scope: list[str]) -> bool:
    P = T * m * n
    # Uniformity strict feasibility check (if P % R == 0) not enforced here; property below will assert equivalence
    ok_row = True
    ok_col = True
    if "row_sets" in unique_scope:
        ok_row = T * m <= math.comb(R, n)
    if "col_sets" in unique_scope:
        ok_col = T * n <= math.comb(R, m)
    return ok_row and ok_col


@given(
    R=st.integers(min_value=5, max_value=90),
    T=st.integers(min_value=1, max_value=200),
    m=st.integers(min_value=1, max_value=6),
    n=st.integers(min_value=1, max_value=6),
    scope=st.lists(st.sampled_from(["row_sets", "col_sets"]), min_size=0, max_size=2)
)
def test_combinatorial_capacity_property(R, T, m, n, scope):
    scope = sorted(set(scope))
    if R < max(m, n):
        pytest.skip("Out of conceptual domain: R must be >= max(m,n)")
    from bingo_gen.feasibility import check_uniqueness_capacity

    result = check_uniqueness_capacity(R=R, T=T, m=m, n=n, unique_scope=scope)
    assert result.feasible == theoretical_feasible(R, T, m, n, scope)


@given(
    R=st.integers(min_value=5, max_value=90),
    T=st.integers(min_value=1, max_value=200),
    m=st.integers(min_value=1, max_value=6),
    n=st.integers(min_value=1, max_value=6),
)
def test_uniformity_strict_equivalence(R, T, m, n):
    if R < 1:
        pytest.skip("R>=1")
    from bingo_gen.feasibility import check_uniformity_strict

    P = T * m * n
    res = check_uniformity_strict(R=R, T=T, m=m, n=n)
    assert res.feasible == (P % R == 0)


def test_near_uniformity_bounds_example():
    from bingo_gen.feasibility import compute_near_uniform_targets

    base, remainder = compute_near_uniform_targets(R=10, T=3, m=2, n=2)
    assert base == 1
    assert remainder == 2  # P=12, base=1, remainder=2


