from __future__ import annotations

from bingo_gen.builder.bibd import build_cards_bibd


def test_bibd_returns_none_when_not_applicable():
    # R too small to avoid duplicates within a card
    assert build_cards_bibd(R=5, T=2, m=2, n=3, uniformity="strict") is None


def test_bibd_basic_construction_strict():
    R, T, m, n = 12, 4, 2, 3
    cards = build_cards_bibd(R=R, T=T, m=m, n=n, uniformity="strict")
    assert cards is not None
    for card in cards:
        # no duplicates per row and expected shape
        assert len(card) == m
        assert all(len(row) == n for row in card)
        for row in card:
            assert len(set(row)) == len(row)
