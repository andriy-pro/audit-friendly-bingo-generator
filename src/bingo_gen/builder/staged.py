from __future__ import annotations

import itertools
from typing import List, Optional, Sequence, Set, Tuple

from ..rng import create_rng
from ..uniqueness import col_sets_of_card, matrix_hash


def has_consecutive(values: Sequence[int]) -> bool:
    s = set(values)
    return any((x + 1) in s for x in s)


def generate_row_sets_pool(
    *,
    R: int,
    n: int,
    pool_size: int,
    rng_engine: str,
    seed: int,
    max_tries: int = 2_000_000,
) -> List[Tuple[int, ...]]:
    """Generate a pool of unique row-sets (size n) without consecutive numbers.

    Sampling-based generator that draws without replacement from combinations space.
    """
    rng = create_rng(rng_engine, seed)
    pool: List[Tuple[int, ...]] = []
    seen: Set[Tuple[int, ...]] = set()
    tries = 0
    numbers = list(range(1, R + 1))
    while len(pool) < pool_size and tries < max_tries:
        tries += 1
        cand = tuple(sorted(rng.sample(numbers, n)))
        if has_consecutive(cand):
            continue
        if cand in seen:
            continue
        seen.add(cand)
        pool.append(cand)
    return pool


def order_row_min_consecutive(row_set: Tuple[int, ...], rng: object) -> List[int]:
    def h_pen(arr: List[int]) -> int:
        return sum(1 for a, b in zip(arr, arr[1:]) if abs(a - b) == 1)

    best = list(row_set)
    rng.shuffle(best)  # type: ignore
    best_score = 10**9
    for _ in range(24):
        cand = list(row_set)
        rng.shuffle(cand)  # type: ignore
        score = h_pen(cand)
        if score < best_score:
            best = cand[:]
            best_score = score
            if best_score == 0:
                break
    return best


def pack_cards_from_pool(
    *,
    pool: List[Tuple[int, ...]],
    R: int,
    T: int,
    m: int,
    n: int,
    rng_engine: str,
    seed: int,
    unique_scope: List[str],
    max_card_restarts: int = 200,
) -> Optional[List[List[List[int]]]]:
    rng = create_rng(rng_engine, seed)
    available: Set[Tuple[int, ...]] = set(pool)
    seen_col_sets: Set[Tuple[int, ...]] = set()
    seen_card_hashes: Set[str] = set()
    cards: List[List[List[int]]] = []

    for _t in range(T):
        success = False
        for _restart in range(max_card_restarts):
            # choose m row-sets with no number overlap
            chosen: List[Tuple[int, ...]] = []
            used_nums: Set[int] = set()
            # randomized order of candidates
            shuffled = list(available)
            rng.shuffle(shuffled)  # type: ignore
            for rs in shuffled:
                if used_nums.isdisjoint(rs):
                    chosen.append(rs)
                    used_nums.update(rs)
                    if len(chosen) == m:
                        break
            if len(chosen) < m:
                continue

            # order rows and columns
            row1 = order_row_min_consecutive(chosen[0], rng)
            matrix: List[List[int]] = [row1]

            def vertical_ok(col_vals: List[int]) -> bool:
                # forbid vertical neighbors
                for a, b in zip(col_vals, col_vals[1:]):
                    if abs(a - b) == 1:
                        return False
                return True

            valid = True
            for idx in range(1, m):
                base = list(chosen[idx])
                placed = None
                for perm in itertools.permutations(base):
                    cols = []
                    for j in range(n):
                        col_vals = [matrix[r][j] for r in range(len(matrix))] + [
                            perm[j]
                        ]
                        cols.append(col_vals)
                    if not all(vertical_ok(cv) for cv in cols):
                        continue
                    new_matrix = matrix + [list(perm)]
                    if "col_sets" in unique_scope and len(new_matrix) == m:
                        col_sets = col_sets_of_card(new_matrix)
                        if any(cs in seen_col_sets for cs in col_sets):
                            continue
                    placed = list(perm)
                    break
                if placed is None:
                    valid = False
                    break
                matrix.append(placed)

            if not valid:
                continue

            h = matrix_hash(matrix)
            if h in seen_card_hashes:
                continue

            # commit
            for rs in chosen:
                available.remove(rs)
            if "col_sets" in unique_scope:
                for cs in col_sets_of_card(matrix):
                    seen_col_sets.add(cs)
            seen_card_hashes.add(h)
            cards.append(matrix)
            success = True
            break

        if not success:
            return None

    return cards


def build_cards_staged(
    *,
    R: int,
    T: int,
    m: int,
    n: int,
    rng_engine: str,
    seed: int,
    unique_scope: List[str],
) -> Optional[List[List[List[int]]]]:
    pool_size = T * m
    pool = generate_row_sets_pool(
        R=R, n=n, pool_size=pool_size, rng_engine=rng_engine, seed=seed
    )
    if len(pool) < pool_size:
        return None
    cards = pack_cards_from_pool(
        pool=pool,
        R=R,
        T=T,
        m=m,
        n=n,
        rng_engine=rng_engine,
        seed=seed + 1337,
        unique_scope=unique_scope,
    )
    return cards
