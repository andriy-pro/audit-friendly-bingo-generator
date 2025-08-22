from __future__ import annotations

import collections

from hypothesis import given, strategies as st


@given(
    R=st.integers(min_value=10, max_value=90),
    T=st.integers(min_value=1, max_value=200),
    m=st.integers(min_value=1, max_value=6),
    n=st.integers(min_value=1, max_value=6),
)
def test_strict_uniformity_frequency_sum_and_equal_counts(R, T, m, n):
    if (T * m * n) % R != 0:
        return
    from bingo_gen.layout import build_global_frequencies

    freqs = build_global_frequencies(R=R, T=T, m=m, n=n, mode="strict", position_balance=False)
    total = sum(freqs.values())
    assert total == T * m * n
    # all counts equal
    values = list(freqs.values())
    assert max(values) == min(values)


@given(
    R=st.integers(min_value=10, max_value=90),
    T=st.integers(min_value=1, max_value=200),
    m=st.integers(min_value=1, max_value=6),
    n=st.integers(min_value=1, max_value=6),
)
def test_near_uniformity_bounds(R, T, m, n):
    from bingo_gen.layout import build_global_frequencies

    freqs = build_global_frequencies(R=R, T=T, m=m, n=n, mode="near", position_balance=False)
    total = sum(freqs.values())
    assert total == T * m * n
    values = list(freqs.values())
    assert max(values) - min(values) <= 1


