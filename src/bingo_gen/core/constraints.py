"""Constraint checking for bingo card generation."""

from __future__ import annotations

from typing import List, Optional


class ConstraintChecker:
    """Checks various constraints for bingo cards."""

    def __init__(self, min_distance: int = 0):
        self.min_distance = min_distance

    def verify_row(self, row: List[int], anchors: Optional[List[int]], strict: bool) -> bool:
        """Verify that a row satisfies all constraints."""

        # Check for duplicates within row
        if len(set(row)) != len(row):
            return False

        # Check minimum distance constraints if enabled
        if self.min_distance > 0:
            if not self._verify_row_distances(row):
                return False

            if anchors and not self._verify_vertical_distances(row, anchors):
                return False

        return True

    def _verify_row_distances(self, row: List[int]) -> bool:
        """Verify horizontal distance constraints within a row."""
        for i in range(len(row)):
            for j in range(i + 1, len(row)):
                if abs(row[i] - row[j]) < self.min_distance:
                    return False
        return True

    def _verify_vertical_distances(self, row: List[int], anchors: List[int]) -> bool:
        """Verify vertical distance constraints against anchors."""
        for i, anchor in enumerate(anchors):
            if i < len(row) and abs(row[i] - anchor) < self.min_distance:
                return False
        return True

    def verify_card(self, matrix: List[List[int]]) -> bool:
        """Verify that an entire card satisfies all constraints."""

        # Check each row
        for row in matrix:
            if not self.verify_row(row, None, strict=False):
                return False

        # Check vertical distances between rows
        if self.min_distance > 0:
            for i in range(len(matrix)):
                for j in range(i + 1, len(matrix)):
                    if not self._verify_vertical_distances(matrix[i], matrix[j]):
                        return False

        return True
