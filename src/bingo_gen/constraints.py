"""Constraint checking utilities for card generation."""

from typing import List


def violates_min_distance(card_matrix: List[List[int]], min_distance: int) -> bool:
    """Check if any two numbers on the same card are too close together."""
    numbers = []
    for row in card_matrix:
        numbers.extend(row)

    for i in range(len(numbers)):
        for j in range(i + 1, len(numbers)):
            if abs(numbers[i] - numbers[j]) < min_distance:
                return True
    return False


def can_add_number_to_partial_card(
    partial_matrix: List[List[int]], new_number: int, min_distance: int
) -> bool:
    """Check if a new number can be added to a partial card without violating min_distance."""
    if min_distance <= 0:
        return True

    for row in partial_matrix:
        for existing_number in row:
            if abs(existing_number - new_number) < min_distance:
                return False
    return True


def check_row_internal_distance(row: List[int], min_distance: int) -> bool:
    """Check distances between all pairs in a single row.

    Returns True if all pairs satisfy min_distance, False otherwise.
    """
    if min_distance <= 0:
        return True

    for i in range(len(row)):
        for j in range(i + 1, len(row)):
            if abs(row[i] - row[j]) < min_distance:
                return False
    return True


def check_inter_row_distances(matrix: List[List[int]], min_distance: int) -> bool:
    """Check distances between all pairs across different rows.

    Returns True if all pairs satisfy min_distance, False otherwise.
    """
    if min_distance <= 0:
        return True

    for row1_idx in range(len(matrix)):
        for row2_idx in range(row1_idx + 1, len(matrix)):
            for num1 in matrix[row1_idx]:
                for num2 in matrix[row2_idx]:
                    if abs(num1 - num2) < min_distance:
                        return False
    return True


def check_card_distances(matrix: List[List[int]], min_distance: int) -> tuple[bool, int]:
    """Check both intra-row and inter-row distances.

    Returns (is_valid, total_violations).
    """
    if min_distance <= 0:
        return True, 0

    violations = 0

    # Check intra-row distances
    for row in matrix:
        if not check_row_internal_distance(row, min_distance):
            violations += 1

    # Check inter-row distances
    if not check_inter_row_distances(matrix, min_distance):
        violations += 1

    return violations == 0, violations
