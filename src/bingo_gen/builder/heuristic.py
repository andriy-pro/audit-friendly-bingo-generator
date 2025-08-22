from __future__ import annotations

from typing import List, Tuple, Set, Optional
import itertools

from ..layout import build_global_frequencies
from ..rng import create_rng, derive_parallel_seed
from ..uniqueness import row_sets_of_card, col_sets_of_card, matrix_hash


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
    unique_scope: List[str] | None = None,
) -> List[List[List[int]]]:
    """Heuristic MVP: fill cards respecting global counts and no duplicates per card.

    Enforces optional global uniqueness for row/column sets and forbids identical cards.
    Retries from scratch on dead-ends up to `max_attempts`.
    """
    if R < m * n:
        raise ValueError("R must be >= m*n to avoid duplicates within a card")

    unique_scope = sorted(set(unique_scope or []))
    target_freqs = build_global_frequencies(R=R, T=T, m=m, n=n, mode=uniformity, position_balance=position_balance)
    numbers = list(range(1, R + 1))

    for attempt in range(max_attempts):
        attempt_seed = derive_parallel_seed(seed, attempt, "heuristic_mvp")
        rng = create_rng(rng_engine, attempt_seed)
        remaining = dict(target_freqs)
        cards: List[List[List[int]]] = []

        seen_row_sets: Set[Tuple[int, ...]] = set()
        seen_col_sets: Set[Tuple[int, ...]] = set()
        seen_card_hashes: Set[str] = set()

        success = True
        for _t in range(T):
            need = m * n
            candidates = [x for x in numbers if remaining[x] > 0]
            if len(candidates) < need:
                success = False
                break
            candidates.sort(key=lambda x: (-remaining[x], x))

            def choose_row(pool: List[int]) -> Optional[List[int]]:
                # choose contiguous top-n slice that yields unseen row set if enforced
                for i in range(0, max(1, len(pool) - n + 1)):
                    row = pool[i : i + n]
                    if len(set(row)) != n:
                        continue
                    if "row_sets" in unique_scope:
                        if tuple(sorted(row)) in seen_row_sets:
                            continue
                    return row
                return None

            matrix: List[List[int]] = []
            used_in_card: Set[int] = set()
            # Build rows sequentially
            for r_idx in range(m):
                pool = [x for x in candidates if x not in used_in_card]
                row = choose_row(pool)
                if row is None:
                    success = False
                    break
                # Try mild randomization within row order (does not affect row set)
                rng.shuffle(row)
                matrix.append(row)
                used_in_card.update(row)
            if not success:
                break

            # For m==2 and col uniqueness, try to find a pairing avoiding collisions
            if m == 2 and "col_sets" in unique_scope:
                row1, row2 = matrix[0], matrix[1]
                ok_perm = None
                for perm in itertools.permutations(range(n)):
                    cols_ok = True
                    for j in range(n):
                        cs = tuple(sorted((row1[j], row2[perm[j]])))
                        if cs in seen_col_sets:
                            cols_ok = False
                            break
                    if cols_ok:
                        ok_perm = perm
                        break
                if ok_perm is None:
                    success = False
                    break
                matrix[1] = [row2[j] for j in ok_perm]

            # Global uniqueness checks
            card_rows = row_sets_of_card(matrix)
            card_cols = col_sets_of_card(matrix)
            if "row_sets" in unique_scope:
                if any(rs in seen_row_sets for rs in card_rows):
                    success = False
                    break
            if "col_sets" in unique_scope:
                if any(cs in seen_col_sets for cs in card_cols):
                    success = False
                    break
            h = matrix_hash(matrix)
            if h in seen_card_hashes:
                success = False
                break

            # Commit consumption and registries
            for x in used_in_card:
                remaining[x] -= 1
            cards.append(matrix)
            if "row_sets" in unique_scope:
                seen_row_sets.update(card_rows)
            if "col_sets" in unique_scope:
                seen_col_sets.update(card_cols)
            seen_card_hashes.add(h)

        if success and sum(remaining.values()) == 0:
            return cards

    raise RuntimeError("Heuristic MVP failed to construct within attempts")


