from __future__ import annotations

from collections import Counter

import pytest


def test_mvp_constructs_and_respects_no_duplicates_per_card():
    from bingo_gen.builder.heuristic import build_cards

    R, T, m, n = 30, 10, 3, 3
    cards = build_cards(
        R=R, T=T, m=m, n=n, uniformity="near", rng_engine="py_random", seed=20250824
    )
    assert len(cards) == T
    # no duplicates within a single card
    for card in cards:
        flat = [x for row in card for x in row]
        assert len(flat) == len(set(flat))


def test_mvp_global_counts_match_targets():
    from bingo_gen.builder.heuristic import build_cards
    from bingo_gen.layout import build_global_frequencies

    R, T, m, n = 20, 8, 2, 5
    target = build_global_frequencies(R=R, T=T, m=m, n=n, mode="near", position_balance=False)
    cards = build_cards(R=R, T=T, m=m, n=n, uniformity="near", rng_engine="py_random", seed=42)
    counts = Counter(x for card in cards for row in card for x in row)
    assert sum(counts.values()) == sum(target.values())
    # near-equality check: differences at most 1 per number
    for x in range(1, R + 1):
        assert abs(counts[x] - target[x]) <= 1


def test_invalid_small_R_raises():
    from bingo_gen.builder.heuristic import build_cards

    with pytest.raises(ValueError):
        build_cards(R=5, T=1, m=3, n=3, uniformity="near", rng_engine="py_random", seed=1)
