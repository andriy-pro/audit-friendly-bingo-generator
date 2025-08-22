from __future__ import annotations

from typing import List, Optional


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def _find_coprime_step(R: int, start: int) -> int:
    k = max(1, start % R)
    for _ in range(R):
        if _gcd(R, k) == 1:
            return k
        k = (k + 1) % R or 1
    return 1


def build_cards_bibd(
    *,
    R: int,
    T: int,
    m: int,
    n: int,
    uniformity: str,
) -> Optional[List[List[List[int]]]]:
    """Minimal BIBD-like attempt via cyclic Latin-style construction.

    This is a best-effort deterministic layout that often achieves equal usage
    when P % R == 0 and provides high uniqueness. Returns None if not applicable.
    """
    P = T * m * n
    if uniformity == "strict" and (P % R) != 0:
        return None
    if R < m * n:
        return None

    # Choose step k coprime to R to cycle through values evenly.
    k = _find_coprime_step(R, start=m * n + 1)

    cards: List[List[List[int]]] = []
    for t in range(T):
        matrix: List[List[int]] = []
        for i in range(m):
            row: List[int] = []
            for j in range(n):
                idx = (i * n + j + t * k) % R
                row.append(idx + 1)
            if len(set(row)) != len(row):
                return None
            matrix.append(row)
        cards.append(matrix)
    return cards


