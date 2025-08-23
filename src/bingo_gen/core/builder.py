"""Universal card builder (simplified delegator).

This module keeps the public dataclasses used by the CLI and other callers
but delegates the actual generation to the single remaining implementation
in `bingo_gen.builder.heuristic`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..builder.heuristic import build_cards as heuristic_build_cards


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
class BuildMetrics:
    """Metrics for card generation.

    Only a minimal metrics shape is preserved here; the heuristic implementation
    controls detailed accounting.
    """

    total_time: float
    attempts_per_card: float
    constraint_violations: int
    memory_usage: int = 0


@dataclass
class BuildResult:
    """Result of card generation."""

    cards: List[List[List[int]]]
    metrics: BuildMetrics


class UniversalCardBuilder:
    """Lightweight delegator to the single heuristic builder.

    This keeps the outward-facing API but simplifies internals to avoid
    maintaining multiple builder implementations.
    """

    def __init__(self, strategy: str = "auto"):
        self.strategy = strategy

    def build(self, params: BuildParams) -> BuildResult:
        """Call the heuristic implementation and wrap its result.

        This intentionally does not attempt to emulate the previous multi-strategy
        behavior; it centralizes generation in one place for simplicity.
        """
        unique_scope = list(params.unique_scope or [])

        cards = heuristic_build_cards(
            R=params.R,
            T=params.T,
            m=params.m,
            n=params.n,
            uniformity=params.uniformity,
            rng_engine=params.rng_engine,
            seed=params.seed,
            position_balance=params.position_balance,
            max_attempts=200,
            unique_scope=unique_scope,
        )

        metrics = BuildMetrics(
            total_time=0.0, attempts_per_card=1.0, constraint_violations=0
        )
        return BuildResult(cards=cards, metrics=metrics)
