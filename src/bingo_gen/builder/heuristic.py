from __future__ import annotations

import itertools
from typing import List, Optional, Set, Tuple

from ..layout import build_global_frequencies
from ..rng import create_rng, derive_parallel_seed
from ..uniqueness import col_sets_of_card, matrix_hash, row_sets_of_card


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
    target_freqs = build_global_frequencies(
        R=R, T=T, m=m, n=n, mode=uniformity, position_balance=position_balance
    )
    numbers = list(range(1, R + 1))

    def horizontal_consecutive_penalty(arr: List[int]) -> int:
        return sum(1 for a, b in zip(arr, arr[1:]) if abs(a - b) == 1)

    def order_row_min_consecutive(
        row: List[int], anchors: Optional[List[int]], rng
    ) -> List[int]:
        # Try multiple shuffles and keep the one with the smallest penalty combining horizontal and vertical (to anchors)
        best = row[:]
        rng.shuffle(best)
        best_score = 10**9
        for _ in range(50):
            candidate = row[:]
            rng.shuffle(candidate)
            score = horizontal_consecutive_penalty(candidate)
            if anchors is not None:
                score += sum(
                    1
                    for j, a in enumerate(anchors)
                    if a is not None and abs(candidate[j] - a) == 1
                )
            if score < best_score:
                best_score = score
                best = candidate[:]
                if best_score == 0:
                    break
        return best

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
            candidates_master = [x for x in numbers if remaining[x] > 0]
            if len(candidates_master) < need:
                success = False
                break
            # Shuffle before sorting to break ties randomly
            rng.shuffle(candidates_master)
            candidates_master.sort(key=lambda x: (-remaining[x], rng.random()))

            # Fast path: if no global uniqueness constraints, do simple greedy fill
            if not unique_scope:
                chosen = candidates_master[:need]
                rng.shuffle(chosen)
                matrix: List[List[int]] = []
                k = 0
                for _i in range(m):
                    row = chosen[k : k + n]
                    k += n
                    # ensure no duplicates within the row
                    if len(set(row)) != len(row):
                        success = False
                        break
                    matrix.append(row)
                if not success:
                    break
                for x in chosen:
                    remaining[x] -= 1
                cards.append(matrix)
                continue

            def choose_row(
                pool: List[int], anchors: Optional[List[int]]
            ) -> Optional[List[int]]:
                # Sample candidate sets from top-K pool and pick minimal-penalty ordering
                if len(pool) < n:
                    return None
                top_k = min(len(pool), max(2 * n, 50))
                top = pool[:top_k]
                picked: Optional[List[int]] = None
                best_score = 10**9
                # Try random samples
                for _ in range(200):
                    cand = rng.sample(top, n)
                    if len(set(cand)) != n:
                        continue
                    if (
                        "row_sets" in unique_scope
                        and tuple(sorted(cand)) in seen_row_sets
                    ):
                        continue
                    ordered = order_row_min_consecutive(cand, anchors, rng)
                    score = horizontal_consecutive_penalty(ordered)
                    if anchors is not None:
                        score += sum(
                            1
                            for j, a in enumerate(anchors)
                            if a is not None and abs(ordered[j] - a) == 1
                        )
                    if score < best_score:
                        best_score = score
                        picked = ordered
                        if best_score == 0:
                            break
                # Fallback: contiguous slice strategy
                if picked is None:
                    for i in range(0, max(1, len(pool) - n + 1)):
                        row = pool[i : i + n]
                        if len(set(row)) != n:
                            continue
                        if (
                            "row_sets" in unique_scope
                            and tuple(sorted(row)) in seen_row_sets
                        ):
                            continue
                        picked = order_row_min_consecutive(row, anchors, rng)
                        break
                return picked

            # Per-card restarts
            card_built = False
            snapshot_remaining = remaining.copy()
            for card_try in range(200):
                matrix: List[List[int]] = []
                used_in_card: Set[int] = set()
                candidates = candidates_master[:]
                # Build rows sequentially with anchors to reduce vertical adjacency
                for r_idx in range(m):
                    pool = [x for x in candidates if x not in used_in_card]
                    anchors_for_row: Optional[List[int]] = (
                        None if r_idx == 0 else matrix[0]
                    )
                    row = choose_row(pool, anchors_for_row)
                    if row is None:
                        break
                    matrix.append(row)
                    used_in_card.update(row)
                else:
                    # Adjust columns to avoid col_set collisions
                    if m >= 2 and "col_sets" in unique_scope:
                        anchors = matrix[0]
                        row_perms = []
                        for r_idx in range(1, m):
                            base = matrix[r_idx]
                            perms = list(itertools.permutations(range(n)))
                            if len(perms) > 120:
                                perms = perms[:120]
                            row_perms.append((r_idx, base, perms))
                        assigned = None
                        for perm_combo in itertools.product(*[p[2] for p in row_perms]):
                            cols_ok = True
                            for j in range(n):
                                col_vals = [anchors[j]]
                                for combo_idx, (r_idx, base, _perms) in enumerate(
                                    row_perms
                                ):
                                    perm = perm_combo[combo_idx]
                                    col_vals.append(base[perm[j]])
                                cs = tuple(sorted(col_vals))
                                if cs in seen_col_sets:
                                    cols_ok = False
                                    break
                            if cols_ok:
                                assigned = perm_combo
                                break
                        if assigned is None:
                            # restart this card
                            continue
                        for combo_idx, (r_idx, base, _) in enumerate(row_perms):
                            perm = assigned[combo_idx]
                            matrix[r_idx] = [base[perm[j]] for j in range(n)]

                    # Global uniqueness checks
                    card_rows = row_sets_of_card(matrix)
                    card_cols = col_sets_of_card(matrix)
                    if "row_sets" in unique_scope and any(
                        rs in seen_row_sets for rs in card_rows
                    ):
                        continue
                    if "col_sets" in unique_scope and any(
                        cs in seen_col_sets for cs in card_cols
                    ):
                        continue
                    h = matrix_hash(matrix)
                    if h in seen_card_hashes:
                        continue

                    # Commit this card
                    for x in used_in_card:
                        remaining[x] -= 1
                    cards.append(matrix)
                    if "row_sets" in unique_scope:
                        seen_row_sets.update(card_rows)
                    if "col_sets" in unique_scope:
                        seen_col_sets.update(card_cols)
                    seen_card_hashes.add(h)
                    card_built = True
                    break

                # on failure, restore remaining and try new randomization
                remaining = snapshot_remaining.copy()

            if not card_built:
                success = False
                break

        if success and sum(remaining.values()) == 0:
            return cards

    raise RuntimeError("Heuristic MVP failed to construct within attempts")
