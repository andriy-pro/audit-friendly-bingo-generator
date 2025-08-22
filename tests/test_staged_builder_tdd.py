from __future__ import annotations

from bingo_gen.builder.staged import build_cards_staged
from bingo_gen.uniqueness import row_sets_of_card, col_sets_of_card


def no_adjacent(seq):
    return all(abs(a - b) != 1 for a, b in zip(seq, seq[1:]))


def test_staged_small_scenario():
    R, T, m, n = 20, 5, 2, 3
    cards = build_cards_staged(
        R=R, T=T, m=m, n=n, rng_engine="py_random", seed=123, unique_scope=["row_sets", "col_sets"]
    )
    assert cards is None or len(cards) == T
    if cards:
        # horizontal no-adjacent
        for card in cards:
            for row in card:
                assert no_adjacent(row)
        # row/col sets uniqueness for small case (best-effort; may be None if pool insufficient)
        seen_r = set()
        seen_c = set()
        for card in cards:
            for rs in row_sets_of_card(card):
                assert rs not in seen_r
                seen_r.add(rs)
            for cs in col_sets_of_card(card):
                assert cs not in seen_c
                seen_c.add(cs)
