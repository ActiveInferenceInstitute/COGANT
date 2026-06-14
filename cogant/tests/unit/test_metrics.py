"""Unit tests for :mod:`cogant.reverse.metrics`.

These tests pin down the behaviour of the GNN-to-GNN distance metrics
used by the round-trip idempotency verifier. Every test uses real
numeric data — no mocks, no patches — per the project no-mocks policy.
"""

from __future__ import annotations

import numpy as np
import pytest

from cogant.reverse.metrics import (
    DEFAULT_ISOMORPHISM_THRESHOLD,
    IsomorphismReport,
    compare_graph_structure,
    compare_matrices,
    compare_role_distributions,
    compute_isomorphism_report,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# compare_role_distributions
# ---------------------------------------------------------------------------


def test_identical_roles_score_1() -> None:
    """Identical role multisets must return exactly 1.0."""
    roles = {"HIDDEN_STATE": 3, "OBSERVATION": 2, "ACTION": 1}
    score = compare_role_distributions(roles, dict(roles))
    assert score == pytest.approx(1.0, abs=1e-9)


def test_identical_distributions_different_scales_score_1() -> None:
    """The metric is distributional — scaling both sides by a constant
    must not change the similarity score."""
    a = {"HIDDEN_STATE": 2, "OBSERVATION": 1}
    b = {"HIDDEN_STATE": 20, "OBSERVATION": 10}
    score = compare_role_distributions(a, b)
    assert score == pytest.approx(1.0, abs=1e-9)


def test_disjoint_roles_score_near_0() -> None:
    """Completely disjoint supports → Jensen-Shannon = 1 → score = 0."""
    a = {"HIDDEN_STATE": 1}
    b = {"ACTION": 1}
    score = compare_role_distributions(a, b)
    assert score == pytest.approx(0.0, abs=1e-9)


def test_empty_roles_returns_zero() -> None:
    """Empty distributions must return 0.0 (spec: graceful handling)."""
    assert compare_role_distributions({}, {}) == 0.0
    assert compare_role_distributions({"HIDDEN_STATE": 1}, {}) == 0.0
    assert compare_role_distributions({}, {"HIDDEN_STATE": 1}) == 0.0


def test_partial_overlap_score_between_0_and_1() -> None:
    """A half-overlapping distribution should score strictly between the
    extremes and is symmetric in its arguments."""
    a = {"HIDDEN_STATE": 1, "OBSERVATION": 1}
    b = {"HIDDEN_STATE": 1, "ACTION": 1}
    score_ab = compare_role_distributions(a, b)
    score_ba = compare_role_distributions(b, a)
    assert 0.0 < score_ab < 1.0
    assert score_ab == pytest.approx(score_ba, abs=1e-12)


# ---------------------------------------------------------------------------
# compare_matrices
# ---------------------------------------------------------------------------


def test_identical_matrices_score_1() -> None:
    """Two zero matrices must score 1.0 — identical is identical, even
    when both norms are zero (we guard against the NaN case)."""
    zeros = {
        "A": np.zeros((3, 3)),
        "B": np.zeros((3, 3, 2)),
        "C": np.zeros((3,)),
        "D": np.zeros((3,)),
    }
    score = compare_matrices(zeros, {k: v.copy() for k, v in zeros.items()})
    assert score == pytest.approx(1.0, abs=1e-9)


def test_identical_nonzero_matrices_score_1() -> None:
    """Non-trivial identical matrices must also score 1.0."""
    mats = {
        "A": np.array([[0.9, 0.1], [0.2, 0.8]]),
        "B": np.array([[[1.0, 0.0], [0.0, 1.0]], [[0.5, 0.5], [0.5, 0.5]]]),
        "C": np.array([1.0, -1.0]),
        "D": np.array([0.5, 0.5]),
    }
    score = compare_matrices(mats, {k: v.copy() for k, v in mats.items()})
    assert score == pytest.approx(1.0, abs=1e-9)


def test_frobenius_distance_symmetric() -> None:
    """Swapping the two argument dicts must produce the same score."""
    a = {"A": np.array([[1.0, 0.0], [0.0, 1.0]])}
    b = {"A": np.array([[0.3, 0.7], [0.6, 0.4]])}
    ab = compare_matrices(a, b)
    ba = compare_matrices(b, a)
    assert ab == pytest.approx(ba, abs=1e-12)
    assert 0.0 < ab < 1.0


def test_empty_matrices_return_neutral_score() -> None:
    """No shared matrix slots → neutral 0.5 per the spec."""
    assert compare_matrices({}, {}) == 0.5
    assert compare_matrices({"A": np.eye(2)}, {}) == 0.5


def test_matrices_accept_python_lists() -> None:
    """The spec explicitly allows lists as well as numpy arrays."""
    a = {"A": [[1.0, 0.0], [0.0, 1.0]]}
    b = {"A": [[1.0, 0.0], [0.0, 1.0]]}
    assert compare_matrices(a, b) == pytest.approx(1.0, abs=1e-9)


def test_matrices_tolerate_shape_mismatch() -> None:
    """Mismatched shapes are zero-padded, so the comparison is defined
    and returns a value strictly in [0, 1]."""
    a = {"A": np.eye(2)}
    b = {"A": np.eye(3)}
    score = compare_matrices(a, b)
    assert 0.0 <= score <= 1.0
    assert score < 1.0  # They are not identical.


# ---------------------------------------------------------------------------
# compare_graph_structure
# ---------------------------------------------------------------------------


def test_identical_graphs_score_1() -> None:
    """Two graphs with the same role multiset must score 1.0."""
    nodes_a = [{"role": "HIDDEN_STATE"}, {"role": "OBSERVATION"}]
    edges_a = [{"source_role": "HIDDEN_STATE", "target_role": "OBSERVATION"}]
    score = compare_graph_structure(nodes_a, edges_a, list(nodes_a), list(edges_a))
    assert score == pytest.approx(1.0, abs=1e-9)


def test_both_empty_graphs_score_1() -> None:
    """Two empty graphs are vacuously identical."""
    assert compare_graph_structure([], [], [], []) == pytest.approx(1.0, abs=1e-9)


def test_one_empty_one_nonempty_graph_scores_0() -> None:
    """One side empty → fully different."""
    score = compare_graph_structure([], [], [{"role": "HIDDEN_STATE"}], [])
    assert score == pytest.approx(0.0, abs=1e-9)


def test_disjoint_node_roles_score_low() -> None:
    """Nodes with entirely disjoint role labels → score 0."""
    a = [{"role": "HIDDEN_STATE"}]
    b = [{"role": "ACTION"}]
    score = compare_graph_structure(a, [], b, [])
    assert score == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# compute_isomorphism_report
# ---------------------------------------------------------------------------


def _identical_package() -> dict:
    return {
        "roles": {"HIDDEN_STATE": 2, "OBSERVATION": 1},
        "matrices": {
            "A": np.array([[0.9, 0.1], [0.2, 0.8]]),
            "B": np.eye(2),
            "C": np.array([1.0, -1.0]),
            "D": np.array([0.5, 0.5]),
        },
        "nodes": [
            {"role": "HIDDEN_STATE"},
            {"role": "HIDDEN_STATE"},
            {"role": "OBSERVATION"},
        ],
        "edges": [{"source_role": "HIDDEN_STATE", "target_role": "OBSERVATION"}],
    }


def test_isomorphism_report_fields() -> None:
    """The report must expose all documented fields in the right ranges
    and the structurally_isomorphic flag must agree with the threshold."""
    pkg_a = _identical_package()
    pkg_b = _identical_package()
    report = compute_isomorphism_report(pkg_a, pkg_b)

    assert isinstance(report, IsomorphismReport)
    assert 0.0 <= report.total_score <= 1.0
    assert 0.0 <= report.role_score <= 1.0
    assert 0.0 <= report.matrix_score <= 1.0
    assert 0.0 <= report.structural_score <= 1.0
    assert report.total_score == pytest.approx(1.0, abs=1e-9)
    assert report.structurally_isomorphic is True
    assert (report.total_score >= DEFAULT_ISOMORPHISM_THRESHOLD) == report.structurally_isomorphic
    assert "role_score" in report.breakdown
    assert "matrix_score" in report.breakdown
    assert "structural_score" in report.breakdown
    assert report.breakdown["threshold"] == DEFAULT_ISOMORPHISM_THRESHOLD


def test_isomorphism_report_drift_flag_flips_with_threshold() -> None:
    """Raising the threshold above total_score must flip structurally_isomorphic."""
    pkg_a = _identical_package()
    pkg_b = _identical_package()
    # Force a strict diff by corrupting one matrix.
    pkg_b["matrices"]["A"] = np.array([[0.0, 1.0], [1.0, 0.0]])
    pkg_b["roles"]["ACTION"] = 3

    loose = compute_isomorphism_report(pkg_a, pkg_b, threshold=0.0)
    tight = compute_isomorphism_report(pkg_a, pkg_b, threshold=0.99)

    assert loose.structurally_isomorphic is True
    assert tight.structurally_isomorphic is False
    assert 0.0 <= loose.total_score <= 1.0


def test_isomorphism_report_summary_string() -> None:
    """The summary() helper must produce a short, non-empty string that
    includes all four numeric axes."""
    pkg_a = _identical_package()
    report = compute_isomorphism_report(pkg_a, pkg_a)
    line = report.summary()
    assert isinstance(line, str)
    assert "total=" in line
    assert "role=" in line
    assert "matrix=" in line
    assert "struct=" in line
    assert line.startswith("[")


def test_isomorphism_report_missing_keys_are_safe() -> None:
    """Packages that omit optional keys must not raise; the per-axis
    scores fall back to their documented neutral values."""
    report = compute_isomorphism_report({}, {})
    assert isinstance(report, IsomorphismReport)
    assert report.role_score == 0.0  # empty roles → neutral-low
    assert report.matrix_score == 0.5  # no shared matrices → neutral
    assert report.structural_score == 1.0  # both graphs empty → identical
    assert 0.0 <= report.total_score <= 1.0


def test_weighted_total_formula() -> None:
    """The total score must respect the documented weighting
    ``0.4*role + 0.4*matrix + 0.2*structural``."""
    report = compute_isomorphism_report(
        {"roles": {}, "matrices": {}, "nodes": [], "edges": []},
        {"roles": {}, "matrices": {}, "nodes": [], "edges": []},
    )
    expected = 0.4 * report.role_score + 0.4 * report.matrix_score + 0.2 * report.structural_score
    assert report.total_score == pytest.approx(expected, abs=1e-12)
