"""Explicit preference and utility functions.

Triggers:
    - PreferenceRule: `PreferenceValidator` class (keyword "validator")
    - PreferenceRule: `validate_state()` (keyword "validate")
    - PreferenceRule: `check_bounds()` (keyword "check")
    - ObservationRule: `get_utility()` (keyword "get", read-only)
"""

from __future__ import annotations

import math


class PreferenceValidator:
    """Defines and validates agent preferences over states."""

    def __init__(
        self,
        preferred_state: list[float],
        tolerance: float = 0.1,
    ) -> None:
        self.preferred_state = preferred_state
        self.tolerance = tolerance

    def get_utility(self, state: list[float]) -> float:
        """Compute utility as negative KL-divergence from preferred state.

        Read-only: no mutation.
        """
        utility = 0.0
        for p, q in zip(self.preferred_state, state):
            if p > 0 and q > 0:
                utility -= p * math.log(p / q)
        return utility

    def validate_state(self, state: list[float]) -> bool:
        """Check whether a state is within tolerance of the preference."""
        if len(state) != len(self.preferred_state):
            return False
        max_diff = max(abs(a - b) for a, b in zip(state, self.preferred_state))
        return max_diff <= self.tolerance

    def check_bounds(self, state: list[float]) -> list[str]:
        """Return a list of constraint violations (empty if all OK)."""
        violations: list[str] = []
        if len(state) != len(self.preferred_state):
            violations.append(f"dimension mismatch: {len(state)} vs {len(self.preferred_state)}")
        if any(s < 0 for s in state):
            violations.append("negative probability detected")
        total = sum(state)
        if abs(total - 1.0) > 1e-6:
            violations.append(f"distribution does not sum to 1: {total:.6f}")
        return violations


def compute_expected_free_energy(
    beliefs: list[float],
    preferences: list[float],
) -> float:
    """Scalar expected free energy (simplified).

    Combines epistemic value (entropy) and pragmatic value (preference alignment).
    """
    entropy = -sum(b * math.log(b + 1e-12) for b in beliefs)
    alignment = sum(b * p for b, p in zip(beliefs, preferences))
    return entropy - alignment


if __name__ == "__main__":
    pref = PreferenceValidator(preferred_state=[0.1, 0.8, 0.1], tolerance=0.2)
    test_state = [0.15, 0.7, 0.15]
    print("utility:", round(pref.get_utility(test_state), 4))
    print("valid:", pref.validate_state(test_state))
    print("violations:", pref.check_bounds(test_state))
    print("EFE:", round(compute_expected_free_energy(test_state, [0.1, 0.8, 0.1]), 4))
