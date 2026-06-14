"""Extended behavioral tests for cogant.reverse.metrics — IsomorphismReport,
compare_role_distributions, compare_matrices, compare_graph_structure,
compute_isomorphism_report.

Covers: summary DRIFT/ISO labels, role symmetry invariant, matrices with
extra keys, graph structure with edges only, per-matrix breakdown,
threshold=1.0 edge case, scalar matrix coercion, and large role distributions.
"""

from __future__ import annotations

import numpy as np
import pytest

from cogant.reverse.metrics import (
    DEFAULT_ISOMORPHISM_THRESHOLD,
    MATRIX_KEYS,
    IsomorphismReport,
    compare_graph_structure,
    compare_matrices,
    compare_role_distributions,
    compute_isomorphism_report,
)

# ---------------------------------------------------------------------------
# IsomorphismReport
# ---------------------------------------------------------------------------


def test_report_summary_drift_label() -> None:
    """Summary says DRIFT when structurally_isomorphic is False."""
    report = IsomorphismReport(
        total_score=0.3,
        role_score=0.2,
        matrix_score=0.4,
        structural_score=0.3,
        structurally_isomorphic=False,
    )
    s = report.summary()
    assert s.startswith("[DRIFT]")


def test_report_summary_iso_label() -> None:
    """Summary says ISO when structurally_isomorphic is True."""
    report = IsomorphismReport(
        total_score=0.9,
        role_score=0.95,
        matrix_score=0.85,
        structural_score=0.9,
        structurally_isomorphic=True,
    )
    s = report.summary()
    assert s.startswith("[ISO]")


def test_report_default_values() -> None:
    """Default IsomorphismReport has all zeros and structurally_isomorphic False."""
    report = IsomorphismReport()
    assert report.total_score == 0.0
    assert report.structurally_isomorphic is False
    assert report.breakdown == {}


# ---------------------------------------------------------------------------
# compare_role_distributions extended
# ---------------------------------------------------------------------------


def test_roles_large_distribution() -> None:
    """Large distributions with many roles compute correctly."""
    roles_a = {f"ROLE_{i}": float(i + 1) for i in range(20)}
    roles_b = dict(roles_a)  # identical
    score = compare_role_distributions(roles_a, roles_b)
    assert score == pytest.approx(1.0, abs=1e-9)


def test_roles_single_element_identical() -> None:
    """Single-role distributions that are identical score 1.0."""
    assert compare_role_distributions({"X": 5}, {"X": 10}) == pytest.approx(1.0, abs=1e-9)


def test_roles_heavily_skewed() -> None:
    """Heavily skewed distributions score between 0 and 1."""
    a = {"HIDDEN_STATE": 100, "OBSERVATION": 1}
    b = {"HIDDEN_STATE": 1, "OBSERVATION": 100}
    score = compare_role_distributions(a, b)
    assert 0.0 < score < 1.0


# ---------------------------------------------------------------------------
# compare_matrices extended
# ---------------------------------------------------------------------------


def test_matrices_extra_keys_included() -> None:
    """Extra keys beyond A/B/C/D are included in comparison."""
    a = {"A": np.eye(2), "E": np.array([[1.0, 0.0], [0.0, 1.0]])}
    b = {"A": np.eye(2), "E": np.array([[1.0, 0.0], [0.0, 1.0]])}
    score = compare_matrices(a, b)
    assert score == pytest.approx(1.0, abs=1e-9)


def test_matrices_one_side_only_key_ignored() -> None:
    """A key present on only one side is skipped (not penalized in matrix score)."""
    a = {"A": np.eye(2), "B": np.eye(3)}
    b = {"A": np.eye(2)}
    score = compare_matrices(a, b)
    # Only A is compared; B is ignored because it's only on one side
    assert score == pytest.approx(1.0, abs=1e-9)


def test_matrices_scalar_values() -> None:
    """Scalar values are coerced to 1x1 matrices."""
    a = {"C": np.array(1.0)}
    b = {"C": np.array(1.0)}
    score = compare_matrices(a, b)
    assert score == pytest.approx(1.0, abs=1e-9)


def test_matrices_1d_values() -> None:
    """1D arrays are reshaped to column vectors for Frobenius comparison."""
    a = {"D": np.array([0.5, 0.5])}
    b = {"D": np.array([0.5, 0.5])}
    score = compare_matrices(a, b)
    assert score == pytest.approx(1.0, abs=1e-9)


def test_matrices_none_value_skipped() -> None:
    """None values in matrix dict are skipped gracefully."""
    a = {"A": None, "B": np.eye(2)}
    b = {"A": np.eye(2), "B": np.eye(2)}
    # A is None on one side => skipped; only B compared
    score = compare_matrices(a, b)
    assert score == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# compare_graph_structure extended
# ---------------------------------------------------------------------------


def test_graph_with_edges_only() -> None:
    """Graphs with edges but no distinguishing node roles."""
    nodes_a = [{"role": "X"}, {"role": "X"}]
    nodes_b = [{"role": "X"}, {"role": "X"}]
    edges_a = [{"source_role": "X", "target_role": "X"}]
    edges_b = [{"source_role": "X", "target_role": "X"}]
    score = compare_graph_structure(nodes_a, edges_a, nodes_b, edges_b)
    assert score == pytest.approx(1.0, abs=1e-9)


def test_graph_attribute_fallback() -> None:
    """Nodes with 'kind' attribute (not 'role') are handled."""

    class MockNode:
        def __init__(self, kind: str):
            self.kind = kind

    nodes_a = [MockNode("HIDDEN_STATE"), MockNode("OBSERVATION")]
    nodes_b = [MockNode("HIDDEN_STATE"), MockNode("OBSERVATION")]
    score = compare_graph_structure(nodes_a, [], nodes_b, [])
    assert score == pytest.approx(1.0, abs=1e-9)


def test_graph_different_edge_counts() -> None:
    """Different numbers of edges lowers the structural score."""
    nodes = [{"role": "A"}, {"role": "B"}]
    edges_a = [{"source_role": "A", "target_role": "B"}]
    edges_b = [
        {"source_role": "A", "target_role": "B"},
        {"source_role": "B", "target_role": "A"},
    ]
    score = compare_graph_structure(nodes, edges_a, nodes, edges_b)
    assert 0.0 < score < 1.0


# ---------------------------------------------------------------------------
# compute_isomorphism_report extended
# ---------------------------------------------------------------------------


def test_report_threshold_1_requires_perfect_match() -> None:
    """With threshold=1.0, only perfectly identical packages are isomorphic."""
    pkg = {
        "roles": {"H": 2, "O": 1},
        "matrices": {"A": np.eye(2), "D": np.array([0.5, 0.5])},
        "nodes": [{"role": "H"}, {"role": "H"}, {"role": "O"}],
        "edges": [],
    }
    report = compute_isomorphism_report(pkg, pkg, threshold=1.0)
    assert report.structurally_isomorphic is True
    assert report.total_score == pytest.approx(1.0, abs=1e-9)


def test_report_breakdown_has_per_matrix_detail() -> None:
    """Breakdown includes per_matrix_frobenius when matrices exist."""
    pkg = {
        "roles": {"H": 1},
        "matrices": {"A": np.eye(2), "D": np.array([0.5, 0.5])},
        "nodes": [{"role": "H"}],
        "edges": [],
    }
    report = compute_isomorphism_report(pkg, pkg)
    assert "per_matrix_frobenius" in report.breakdown
    # All raw distances should be 0 for identical matrices
    for _key, val in report.breakdown["per_matrix_frobenius"].items():
        assert val == pytest.approx(0.0, abs=1e-9)


def test_report_breakdown_counts() -> None:
    """Breakdown includes correct node/edge counts."""
    pkg_a = {
        "nodes": [{"role": "A"}, {"role": "B"}],
        "edges": [{"source_role": "A", "target_role": "B"}],
    }
    pkg_b = {
        "nodes": [{"role": "A"}],
        "edges": [],
    }
    report = compute_isomorphism_report(pkg_a, pkg_b)
    assert report.breakdown["n_nodes_a"] == 2
    assert report.breakdown["n_nodes_b"] == 1
    assert report.breakdown["n_edges_a"] == 1
    assert report.breakdown["n_edges_b"] == 0


def test_matrix_keys_constant() -> None:
    """MATRIX_KEYS is exactly (A, B, C, D)."""
    assert MATRIX_KEYS == ("A", "B", "C", "D")


def test_default_threshold_value() -> None:
    """DEFAULT_ISOMORPHISM_THRESHOLD is 0.7."""
    assert DEFAULT_ISOMORPHISM_THRESHOLD == 0.7
