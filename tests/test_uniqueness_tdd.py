from __future__ import annotations

from bingo_gen.uniqueness import row_sets_of_card, col_sets_of_card, matrix_hash, cards_hash


def test_row_col_sets_are_sorted_tuples():
    matrix = [
        [5, 1, 9],
        [2, 7, 4],
    ]
    rows = row_sets_of_card(matrix)
    cols = col_sets_of_card(matrix)
    assert rows == [(1, 5, 9), (2, 4, 7)]
    assert cols == [(2, 5), (1, 7), (4, 9)]


def test_hashes_stable_and_distinct():
    a = [[1, 2], [3, 4]]
    b = [[1, 3], [2, 4]]
    h_a = matrix_hash(a)
    h_b = matrix_hash(b)
    assert h_a.startswith("sha256:")
    assert h_b.startswith("sha256:")
    assert h_a != h_b
    agg = cards_hash([a, b])
    assert agg.startswith("sha256:")
