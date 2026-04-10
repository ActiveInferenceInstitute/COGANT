"""Tests for cogant.metrics public API.

Verifies that the metrics module loads METRICS.yaml and exposes
correct types and values for all public accessor functions.
"""
from __future__ import annotations

import cogant.metrics as m


def test_load_returns_dict() -> None:
    data = m.load()
    assert isinstance(data, dict)
    assert "schema_version" in data
    assert "testing" in data
    assert "evaluation" in data


def test_version_returns_string() -> None:
    v = m.version()
    assert isinstance(v, str)
    assert len(v) > 0
    # Should be a semver-style string
    parts = v.split(".")
    assert len(parts) >= 2


def test_test_count_returns_positive_int() -> None:
    count = m.test_count()
    assert isinstance(count, int)
    assert count > 0


def test_coverage_returns_float_in_range() -> None:
    cov = m.coverage()
    assert isinstance(cov, float)
    assert 0.0 <= cov <= 100.0


def test_mypy_errors_returns_non_negative_int() -> None:
    errors = m.mypy_errors()
    assert isinstance(errors, int)
    assert errors >= 0


def test_isomorphic_count_is_positive() -> None:
    count = m.isomorphic_count()
    assert isinstance(count, int)
    assert count > 0


def test_total_targets_is_23() -> None:
    """Dataset has 23 known targets."""
    assert m.total_targets() == 23


def test_isomorphic_count_leq_total() -> None:
    assert m.isomorphic_count() <= m.total_targets()


def test_mean_epsilon_in_range() -> None:
    eps = m.mean_epsilon()
    assert isinstance(eps, float)
    assert 0.0 <= eps <= 1.0


def test_epsilon_for_known_isomorphic_target_returns_1() -> None:
    """01_simple_state has epsilon == 1.0 (ISOMORPHIC tier)."""
    result = m.epsilon_for("01_simple_state")
    assert result is not None
    assert result == 1.0


def test_epsilon_for_unknown_target_returns_none() -> None:
    result = m.epsilon_for("nonexistent_repo_xyz")
    assert result is None


def test_epsilon_for_divergent_target_below_threshold() -> None:
    """requests is DIVERGENT with epsilon < 0.5."""
    result = m.epsilon_for("requests")
    assert result is not None
    assert result < 0.5


def test_bibliography_entries_is_positive() -> None:
    count = m.bibliography_entries()
    assert isinstance(count, int)
    assert count > 0
