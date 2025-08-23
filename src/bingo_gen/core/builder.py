"""Universal card builder with configurable strategies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Set, Tuple

from ..layout import build_global_frequencies
from ..rng import create_rng, derive_parallel_seed
from ..uniqueness import col_sets_of_card, matrix_hash, row_sets_of_card
from .constraints import ConstraintChecker
from .optimizer import RowOptimizer


@dataclass
class BuildParams:
    """Parameters for card generation."""

    R: int
    T: int
    m: int
    n: int
    uniformity: str
    unique_scope: List[str]
    seed: int
    rng_engine: str = "py_random"
    position_balance: bool = False
    strategy: str = "auto"


@dataclass
class BuildResult:
    """Result of card generation."""

    cards: List[List[List[int]]]
    metrics: BuildMetrics


@dataclass
class BuildMetrics:
    """Metrics for card generation."""

    total_time: float
    attempts_per_card: float
    constraint_violations: int
    memory_usage: int = 0


class UniversalCardBuilder:
    """Universal card builder with multiple strategies."""

    def __init__(self, strategy: str = "auto"):
        self.strategy = strategy
        self.constraint_checker = ConstraintChecker()
        self.row_optimizer = RowOptimizer()

    def build(self, params: BuildParams) -> BuildResult:
        """Build cards using the specified strategy."""
        if self.strategy == "auto":
            return self._build_adaptive(params)
        elif self.strategy == "fast":
            return self._build_fast(params)
        elif self.strategy == "optimal":
            return self._build_optimal(params)
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")

    def _build_adaptive(self, params: BuildParams) -> BuildResult:
        """Adaptive strategy: try fast first, fallback to optimal."""
        try:
            return self._build_fast(params)
        except RuntimeError:
            # Fallback to optimal if fast fails
            return self._build_optimal(params)

    def _build_fast(self, params: BuildParams) -> BuildResult:
        """Fast strategy: minimal attempts, basic constraints."""
        return self._build_cards(
            params, max_attempts=20, max_row_attempts=10, strict_constraints=False
        )

    def _build_optimal(self, params: BuildParams) -> BuildResult:
        """Optimal strategy: more attempts, strict constraints."""
        return self._build_cards(
            params, max_attempts=100, max_row_attempts=50, strict_constraints=True
        )

    def _build_cards(
        self,
        params: BuildParams,
        max_attempts: int,
        max_row_attempts: int,
        strict_constraints: bool,
    ) -> BuildResult:
        """Core building logic with configurable parameters."""

        if params.R < params.m * params.n:
            raise ValueError("R must be >= m*n to avoid duplicates within a card")

        # Build global frequency layout
        target_freqs = build_global_frequencies(
            R=params.R,
            T=params.T,
            m=params.m,
            n=params.n,
            mode=params.uniformity,
            position_balance=params.position_balance,
        )

        for attempt in range(max_attempts):
            attempt_seed = derive_parallel_seed(params.seed, attempt, "universal_builder")
            rng = create_rng(params.rng_engine, attempt_seed)
            remaining = dict(target_freqs)
            cards: List[List[List[int]]] = []

            # Track seen combinations for uniqueness
            seen_row_sets: Set[Tuple[int, ...]] = set()
            seen_col_sets: Set[Tuple[int, ...]] = set()
            seen_card_hashes: Set[str] = set()

            success = True
            for _t in range(params.T):
                card = self._build_single_card(
                    params,
                    remaining,
                    seen_row_sets,
                    seen_col_sets,
                    seen_card_hashes,
                    rng,
                    max_row_attempts,
                    strict_constraints,
                )

                if card is None:
                    success = False
                    break

                cards.append(card)

                # Update remaining frequencies and seen sets
                for row in card:
                    for num in row:
                        remaining[num] -= 1

                # Update uniqueness tracking
                card_rows = row_sets_of_card(card)
                card_cols = col_sets_of_card(card)
                if "row_sets" in params.unique_scope:
                    seen_row_sets.update(card_rows)
                if "col_sets" in params.unique_scope:
                    seen_col_sets.update(card_cols)
                seen_card_hashes.add(matrix_hash(card))

            if success and sum(remaining.values()) == 0:
                # Success! Calculate metrics
                metrics = BuildMetrics(
                    total_time=0.0,  # Will be set by caller
                    attempts_per_card=attempt + 1,
                    constraint_violations=0,
                    memory_usage=0,
                )
                return BuildResult(cards=cards, metrics=metrics)

        raise RuntimeError(f"Failed to build cards within {max_attempts} attempts")

    def _build_single_card(
        self,
        params: BuildParams,
        remaining: dict[int, int],
        seen_row_sets: Set[Tuple[int, ...]],
        seen_col_sets: Set[Tuple[int, ...]],
        seen_card_hashes: Set[str],
        rng,
        max_row_attempts: int,
        strict_constraints: bool,
    ) -> Optional[List[List[int]]]:
        """Build a single card with the given constraints."""

        for card_attempt in range(max_row_attempts):
            matrix: List[List[int]] = []
            used_in_card: Set[int] = set()
            candidates = [x for x in range(1, params.R + 1) if remaining[x] > 0]

            # Smart candidate selection: prefer less used numbers
            rng.shuffle(candidates)
            candidates.sort(key=lambda x: (remaining[x], x))

            # Build rows sequentially
            for r_idx in range(params.m):
                pool = [x for x in candidates if x not in used_in_card]
                if len(pool) < params.n:
                    return None

                # Get anchors from previous row for vertical optimization
                anchors = None if r_idx == 0 else matrix[0]

                row = self._choose_row(
                    pool, anchors, seen_row_sets, rng, max_row_attempts, strict_constraints
                )

                if row is None:
                    return None

                matrix.append(row)
                used_in_card.update(row)

            # Verify card constraints
            if self._verify_card_constraints(
                matrix, seen_row_sets, seen_col_sets, seen_card_hashes, params.unique_scope
            ):
                return matrix

        return None

    def _choose_row(
        self,
        pool: List[int],
        anchors: Optional[List[int]],
        seen_row_sets: Set[Tuple[int, ...]],
        rng,
        max_attempts: int,
        strict_constraints: bool,
    ) -> Optional[List[int]]:
        """Choose a row that satisfies all constraints."""

        for _ in range(max_attempts):
            # Sample candidates
            if len(pool) < 4:  # Fixed size for now
                continue

            cand = rng.sample(pool, 4)
            if len(set(cand)) != len(cand):
                continue

            # Check global uniqueness
            if tuple(sorted(cand)) in seen_row_sets:
                continue

            # Optimize row order
            optimized = self.row_optimizer.optimize(cand, anchors, rng)

            # Verify constraints
            if self.constraint_checker.verify_row(optimized, anchors, strict_constraints):
                return optimized

        return None

    def _verify_card_constraints(
        self,
        matrix: List[List[int]],
        seen_row_sets: Set[Tuple[int, ...]],
        seen_col_sets: Set[Tuple[int, ...]],
        seen_card_hashes: Set[str],
        unique_scope: List[str],
    ) -> bool:
        """Verify that a card satisfies all constraints."""

        # Check uniqueness
        card_rows = row_sets_of_card(matrix)
        card_cols = col_sets_of_card(matrix)

        if "row_sets" in unique_scope and any(rs in seen_row_sets for rs in card_rows):
            return False

        if "col_sets" in unique_scope and any(cs in seen_col_sets for cs in card_cols):
            return False

        # Check card hash uniqueness
        card_hash = matrix_hash(matrix)
        if card_hash in seen_card_hashes:
            return False

        return True
