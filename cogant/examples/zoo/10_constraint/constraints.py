"""Validation and constraint checking for Active Inference models.

Triggers:
    - PreferenceRule: `ModelChecker` class (keyword "checker")
    - PreferenceRule: `validate_distribution()` (keyword "validate")
    - PreferenceRule: `check_transition_matrix()` (keyword "check")
    - PreferenceRule: `assert_positive()` (prefix "assert_")
    - ObservationRule: `get_violations()` (keyword "get", read-only)
"""

from __future__ import annotations


class ModelChecker:
    """Validates structural constraints on Active Inference model components."""

    def __init__(self, tolerance: float = 1e-6) -> None:
        self.tolerance = tolerance
        self._violations: list[str] = []

    def validate_distribution(self, dist: list[float], name: str = "dist") -> bool:
        """Check that a distribution sums to 1 and has no negative entries."""
        self._violations.clear()

        if not dist:
            self._violations.append(f"{name}: empty distribution")
            return False

        if any(v < -self.tolerance for v in dist):
            self._violations.append(f"{name}: negative values found")

        total = sum(dist)
        if abs(total - 1.0) > self.tolerance:
            self._violations.append(f"{name}: sums to {total}, not 1.0")

        return len(self._violations) == 0

    def check_transition_matrix(
        self,
        matrix: list[list[float]],
        name: str = "B",
    ) -> bool:
        """Check that each column of a transition matrix sums to 1."""
        self._violations.clear()

        if not matrix or not matrix[0]:
            self._violations.append(f"{name}: empty matrix")
            return False

        num_rows = len(matrix)
        num_cols = len(matrix[0])

        for col in range(num_cols):
            col_sum = sum(matrix[row][col] for row in range(num_rows))
            if abs(col_sum - 1.0) > self.tolerance:
                self._violations.append(f"{name}: column {col} sums to {col_sum}")

        return len(self._violations) == 0

    def get_violations(self) -> list[str]:
        """Return the list of constraint violations from the last check."""
        return list(self._violations)


def assert_positive(values: list[float], label: str = "values") -> None:
    """Assert that all values are non-negative."""
    for i, v in enumerate(values):
        if v < 0:
            raise ValueError(f"{label}[{i}] = {v} is negative")


def check_dimensionality(
    matrix: list[list[float]],
    expected_rows: int,
    expected_cols: int,
) -> bool:
    """Verify matrix dimensions match expectations."""
    if len(matrix) != expected_rows:
        return False
    return all(len(row) == expected_cols for row in matrix)


if __name__ == "__main__":
    checker = ModelChecker()
    print("valid dist:", checker.validate_distribution([0.3, 0.5, 0.2]))
    print("invalid dist:", checker.validate_distribution([0.3, 0.5, 0.3]))
    print("violations:", checker.get_violations())

    B = [[0.9, 0.1], [0.1, 0.9]]
    print("valid B:", checker.check_transition_matrix(B))

    assert_positive([0.1, 0.2, 0.7])
    print("positive assertion passed")
