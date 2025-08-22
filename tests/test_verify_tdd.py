from __future__ import annotations

from bingo_gen.builder.heuristic import build_cards
from bingo_gen.verify import verify


def test_verify_reports_uniqueness_and_uniformity():
    R, T, m, n = 25, 6, 2, 3
    cards = build_cards(
        R=R,
        T=T,
        m=m,
        n=n,
        uniformity="near",
        rng_engine="py_random",
        seed=123,
        unique_scope=["row_sets", "col_sets"],
    )
    rep = verify(cards, R=R, m=m, n=n, unique_scope=["row_sets", "col_sets"])
    assert rep["ok_no_duplicates_within_cards"] is True
    assert rep["ok_no_identical_cards"] is True
    assert rep["uniqueness"]["row_sets_checked"] is True
    assert rep["uniqueness"]["col_sets_checked"] is True
    assert rep["uniqueness"]["row_set_collisions"] == 0
    assert rep["uniqueness"]["col_set_collisions"] == 0
    assert rep["tests"]["global"]["chi2"]["p_value"] >= 0.0
