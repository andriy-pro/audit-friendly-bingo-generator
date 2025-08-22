from __future__ import annotations

from bingo_gen.builder.heuristic import build_cards
from bingo_gen.uniqueness import row_sets_of_card, col_sets_of_card, matrix_hash


def test_global_uniqueness_row_and_col_sets():
    R, T, m, n = 30, 12, 2, 3
    cards = build_cards(
        R=R,
        T=T,
        m=m,
        n=n,
        uniformity="near",
        rng_engine="py_random",
        seed=20250824,
        unique_scope=["row_sets", "col_sets"],
    )
    seen_rows = set()
    seen_cols = set()
    seen_cards = set()
    for card in cards:
        for rs in row_sets_of_card(card):
            assert rs not in seen_rows
            seen_rows.add(rs)
        for cs in col_sets_of_card(card):
            assert cs not in seen_cols
            seen_cols.add(cs)
        h = matrix_hash(card)
        assert h not in seen_cards
        seen_cards.add(h)
