from __future__ import annotations

from typing import List

from ..layout import build_global_frequencies
from ..rng import create_rng, derive_parallel_seed


def build_cards(
    *,
    R: int,
    T: int,
    m: int,
    n: int,
    uniformity: str,
    rng_engine: str,
    seed: int,
    position_balance: bool = False,
    max_attempts: int = 50,
) -> List[List[List[int]]]:
    """Heuristic MVP: fill cards respecting global counts and no duplicates per card.

    This MVP does not enforce row/column set global uniqueness yet. It retries
    from scratch on dead-ends up to `max_attempts`.
    """
    if R < m * n:
        raise ValueError("R must be >= m*n to avoid duplicates within a card")

    target_freqs = build_global_frequencies(R=R, T=T, m=m, n=n, mode=uniformity, position_balance=position_balance)
    numbers = list(range(1, R + 1))

    for attempt in range(max_attempts):
        attempt_seed = derive_parallel_seed(seed, attempt, "heuristic_mvp")
        rng = create_rng(rng_engine, attempt_seed)
        remaining = dict(target_freqs)
        cards: List[List[List[int]]] = []

        success = True
        for _t in range(T):
            candidates = [x for x in numbers if remaining[x] > 0]
            need = m * n
            if len(candidates) < need:
                success = False
                break
            candidates.sort(key=lambda x: (-remaining[x], x))
            chosen = candidates[:need]
            # Randomize placement order only
            rng.shuffle(chosen)

            matrix: List[List[int]] = []
            k = 0
            for _i in range(m):
                row = chosen[k : k + n]
                k += n
                matrix.append(row)
            for x in chosen:
                remaining[x] -= 1
            cards.append(matrix)

        if success and sum(remaining.values()) == 0:
            return cards

    raise RuntimeError("Heuristic MVP failed to construct within attempts")


