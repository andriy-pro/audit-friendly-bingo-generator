"""Row optimization for bingo card generation."""

from __future__ import annotations

from typing import List, Optional


class RowOptimizer:
    """Optimizes row ordering to minimize penalties."""

    def __init__(self, max_attempts: int = 20):
        self.max_attempts = max_attempts

    def optimize(self, row: List[int], anchors: Optional[List[int]], rng) -> List[int]:
        """Optimize row order to minimize penalties."""

        if not anchors:
            # No anchors, just optimize horizontal spread
            return self._optimize_horizontal(row, rng)

        # Optimize both horizontal and vertical spread
        return self._optimize_combined(row, anchors, rng)

    def _optimize_horizontal(self, row: List[int], rng) -> List[int]:
        """Optimize horizontal spread only."""
        best = row[:]
        best_score = self._calculate_horizontal_penalty(best)

        for _ in range(self.max_attempts):
            candidate = row[:]
            rng.shuffle(candidate)

            score = self._calculate_horizontal_penalty(candidate)
            if score < best_score:
                best_score = score
                best = candidate[:]

                if best_score == 0:  # Perfect score
                    break

        return best

    def _optimize_combined(self, row: List[int], anchors: List[int], rng) -> List[int]:
        """Optimize both horizontal and vertical spread."""
        best = row[:]
        best_score = self._calculate_combined_penalty(best, anchors)

        for _ in range(self.max_attempts):
            candidate = row[:]
            rng.shuffle(candidate)

            score = self._calculate_combined_penalty(candidate, anchors)
            if score < best_score:
                best_score = score
                best = candidate[:]

                if best_score == 0:  # Perfect score
                    break

        return best

    def _calculate_horizontal_penalty(self, row: List[int]) -> int:
        """Calculate horizontal spread penalty."""
        penalty = 0
        for i in range(len(row) - 1):
            diff = abs(row[i] - row[i + 1])
            if diff == 1:
                penalty += 2  # Medium penalty for adjacent
            elif diff == 2:
                penalty += 1  # Light penalty for close
        return penalty

    def _calculate_combined_penalty(self, row: List[int], anchors: List[int]) -> int:
        """Calculate combined horizontal and vertical penalty."""
        horizontal = self._calculate_horizontal_penalty(row)
        vertical = self._calculate_vertical_penalty(row, anchors)
        return horizontal + vertical

    def _calculate_vertical_penalty(self, row: List[int], anchors: List[int]) -> int:
        """Calculate vertical spread penalty against anchors."""
        penalty = 0
        for i, anchor in enumerate(anchors):
            if i < len(row):
                diff = abs(row[i] - anchor)
                if diff == 1:
                    penalty += 1  # Light penalty for vertical adjacency
        return penalty
