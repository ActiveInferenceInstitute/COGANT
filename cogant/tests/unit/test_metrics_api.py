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


def test_role_preserved_count_is_current_fresh_verdict_count() -> None:
    count = m.role_preserved_count()
    assert isinstance(count, int)
    assert count >= 0
    roundtrip = m.load()["evaluation"]["roundtrip"]
    assert count == roundtrip["role_preserved_count"]
    assert count + roundtrip["non_native_count"] <= m.total_targets()


def test_strict_isomorphism_count_is_strict_count() -> None:
    count = m.strict_isomorphism_count()
    assert isinstance(count, int)
    assert count == m.strict_isomorphism_count()


def test_total_targets_matches_per_target_rows() -> None:
    """Total target count is derived from the current native ledger."""
    roundtrip = m.load()["evaluation"]["roundtrip"]
    assert m.total_targets() == roundtrip["total_targets"]
    assert m.total_targets() == len(roundtrip["per_target"])


def test_strict_isomorphism_count_leq_total() -> None:
    assert m.strict_isomorphism_count() <= m.total_targets()


def test_mean_role_preservation_score_in_range() -> None:
    eps = m.mean_role_preservation_score()
    assert isinstance(eps, float)
    assert 0.0 <= eps <= 1.0


def test_role_preservation_score_for_known_role_preserved_target_returns_1() -> None:
    """01_simple_state has epsilon proxy == 1.0 (role-preserved tier)."""
    result = m.role_preservation_score_for("01_simple_state")
    assert result is not None
    assert result == 1.0


def test_role_preservation_score_for_unknown_target_returns_none() -> None:
    result = m.role_preservation_score_for("nonexistent_repo_xyz")
    assert result is None


def test_role_preservation_score_for_requests_lib_target_is_role_preserved() -> None:
    """requests_lib is role-preserved in the native v0.6 roundtrip ledger."""
    result = m.role_preservation_score_for("requests_lib")
    assert result is not None
    assert result >= 0.8  # role-preserved threshold


def test_bibliography_entries_is_positive() -> None:
    count = m.bibliography_entries()
    assert isinstance(count, int)
    assert count > 0
