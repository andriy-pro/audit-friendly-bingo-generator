from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from .uniqueness import row_sets_of_card, col_sets_of_card, matrix_hash


@dataclass
class UniquenessReport:
    row_sets_checked: bool
    col_sets_checked: bool
    row_set_collisions: int
    col_set_collisions: int


def compute_frequencies(cards: Sequence[Sequence[Sequence[int]]], R: int) -> Dict[int, int]:
    counts: Counter[int] = Counter()
    for card in cards:
        for row in card:
            counts.update(row)
    # ensure all numbers present with 0
    for x in range(1, R + 1):
        counts.setdefault(x, 0)
    return dict(counts)


def compute_position_frequencies(
    cards: Sequence[Sequence[Sequence[int]]], R: int
) -> Dict[str, Dict[int, int]]:
    pos_counts: Dict[Tuple[int, int], Counter] = defaultdict(Counter)
    if not cards:
        return {}
    m = len(cards[0])
    n = len(cards[0][0]) if m > 0 else 0
    for card in cards:
        for i in range(m):
            for j in range(n):
                pos_counts[(i, j)][card[i][j]] += 1
    out: Dict[str, Dict[int, int]] = {}
    for (i, j), cn in pos_counts.items():
        bucket = {x: cn.get(x, 0) for x in range(1, R + 1)}
        out[f"({i},{j})"] = bucket
    return out


def count_set_collisions(
    cards: Sequence[Sequence[Sequence[int]]], scope: List[str]
) -> UniquenessReport:
    rows_seen: Counter = Counter()
    cols_seen: Counter = Counter()
    check_rows = "row_sets" in scope
    check_cols = "col_sets" in scope
    for card in cards:
        if check_rows:
            for rs in row_sets_of_card(card):
                rows_seen[rs] += 1
        if check_cols:
            for cs in col_sets_of_card(card):
                cols_seen[cs] += 1
    row_collisions = sum(c - 1 for c in rows_seen.values() if c > 1)
    col_collisions = sum(c - 1 for c in cols_seen.values() if c > 1)
    return UniquenessReport(
        row_sets_checked=check_rows,
        col_sets_checked=check_cols,
        row_set_collisions=row_collisions,
        col_set_collisions=col_collisions,
    )


def check_no_duplicates_within_cards(cards: Sequence[Sequence[Sequence[int]]]) -> bool:
    for card in cards:
        seen = set()
        for row in card:
            for x in row:
                if x in seen:
                    return False
                seen.add(x)
    return True


def check_no_identical_cards(cards: Sequence[Sequence[Sequence[int]]]) -> bool:
    seen = set()
    for card in cards:
        h = matrix_hash(card)
        if h in seen:
            return False
        seen.add(h)
    return True


def chi2_wilson_hilferty_pvalue(stat: float, df: int) -> float:
    if df <= 0:
        return 1.0
    # Wilson–Hilferty approximation: transform chi-square to normal
    t = (stat / df) ** (1.0 / 3.0)
    mu = 1.0 - 2.0 / (9.0 * df)
    sigma = math.sqrt(2.0 / (9.0 * df))
    z = (t - mu) / sigma

    # Survival function ~ 1 - Phi(z)
    # Approximate Phi via error function
    def phi(val: float) -> float:
        return 0.5 * (1.0 + math.erf(val / math.sqrt(2.0)))

    p_right = 1.0 - phi(z)
    return max(0.0, min(1.0, p_right))


def uniformity_tests(
    freqs: Dict[int, int], R: int, mode: str, alpha: float = 0.05
) -> Dict[str, object]:
    P = sum(freqs.values())
    if P == 0 or R == 0:
        return {"mode": mode, "max_minus_min": 0, "chi2": {"stat": 0.0, "df": 0, "p_value": 1.0}}
    expected = P / R
    stat = 0.0
    for x in range(1, R + 1):
        stat += (freqs.get(x, 0) - expected) ** 2 / (expected if expected > 0 else 1)
    df = max(R - 1, 1)
    p = chi2_wilson_hilferty_pvalue(stat, df)
    return {
        "mode": mode,
        "max_minus_min": max(freqs.values()) - min(freqs.values()),
        "chi2": {"stat": round(stat, 6), "df": df, "p_value": round(p, 6)},
        "alpha": alpha,
        "engine": "wilson_hilferty",
    }


def verify(
    cards: Sequence[Sequence[Sequence[int]]], *, R: int, m: int, n: int, unique_scope: List[str]
) -> Dict[str, object]:
    freqs = compute_frequencies(cards, R)
    pos_freqs = compute_position_frequencies(cards, R)
    uniq = count_set_collisions(cards, unique_scope)
    ok_no_dupes = check_no_duplicates_within_cards(cards)
    ok_no_identicals = check_no_identical_cards(cards)
    tests = {
        "global": uniformity_tests(freqs, R, mode="near"),  # mode label informational
    }
    return {
        "frequencies": freqs,
        "position_frequencies": pos_freqs,
        "uniqueness": {
            "row_sets_checked": uniq.row_sets_checked,
            "col_sets_checked": uniq.col_sets_checked,
            "row_set_collisions": uniq.row_set_collisions,
            "col_set_collisions": uniq.col_set_collisions,
            "set_representation": "sorted_tuple",
        },
        "uniformity": {
            "mode": "near",
            "max_minus_min": max(freqs.values()) - min(freqs.values()),
        },
        "tests": tests,
        "ok_no_duplicates_within_cards": ok_no_dupes,
        "ok_no_identical_cards": ok_no_identicals,
    }
