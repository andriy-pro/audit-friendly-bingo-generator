from __future__ import annotations

import hashlib
import json
from typing import Iterable, List, Sequence, Tuple


def row_sets_of_card(matrix: Sequence[Sequence[int]]) -> List[Tuple[int, ...]]:
    return [tuple(sorted(row)) for row in matrix]


def col_sets_of_card(matrix: Sequence[Sequence[int]]) -> List[Tuple[int, ...]]:
    if not matrix:
        return []
    m = len(matrix)
    n = len(matrix[0])
    cols: List[Tuple[int, ...]] = []
    for j in range(n):
        col = [matrix[i][j] for i in range(m)]
        cols.append(tuple(sorted(col)))
    return cols


def matrix_hash(matrix: Sequence[Sequence[int]]) -> str:
    payload = json.dumps(matrix, ensure_ascii=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def cards_hash(matrices: Iterable[Sequence[Sequence[int]]]) -> str:
    hashes = [matrix_hash(m) for m in matrices]
    payload = json.dumps(hashes, ensure_ascii=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()
