"""Wave-20 coverage tests for ``cogant.reverse.idempotency``.

Targets the previously uncovered helpers and report builders:

* ``check_structural_idempotency`` and ``check_semantic_idempotency``
  (entire bodies — lines 328-361 / 380-406).
* ``_role_multiset_from_model`` POLICY-annotation branch (lines 198, 200).
* ``_model_matrices`` D-matrix branch (line 236).
* ``_state_space_matrices`` real-attribute branch (line 253).
* ``_nodes_edges_from_mappings`` ``kind is None`` skip (line 272).
* ``RoundtripResult.summary`` formatter.

Uses real ``ReverseGNNModel`` instances and real ``SemanticMapping``
objects — no mocks.
"""

from __future__ import annotations

from cogant.reverse.idempotency import (
    IdempotencyReport,
    RoundtripResult,
    _model_matrices,
    _nodes_edges_from_mappings,
    _role_multiset_from_mappings,
    _role_multiset_from_model,
    _state_space_matrices,
    check_semantic_idempotency,
    check_structural_idempotency,
)
from cogant.reverse.parser import ReverseGNNModel
from cogant.schemas.semantic import MappingKind, SemanticMapping

# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #


def _mapping(mapping_id: str, kind: MappingKind) -> SemanticMapping:
    return SemanticMapping(id=mapping_id, kind=kind)


# ------------------------------------------------------------------ #
# check_structural_idempotency
# ------------------------------------------------------------------ #


def test_check_structural_idempotency_identical_graphs_idempotent() -> None:
    """Identical role multisets → is_idempotent=True, score=1.0."""
    a = {
        "m1": _mapping("m1", MappingKind.HIDDEN_STATE),
        "m2": _mapping("m2", MappingKind.OBSERVATION),
    }
    b = dict(a)  # same shape
    report = check_structural_idempotency(a, b)
    assert isinstance(report, IdempotencyReport)
    assert report.is_idempotent is True
    assert report.differences == []
    assert report.score == 1.0
    # Forward and reverse role multisets are equal.
    assert report.forward_roles == report.reverse_roles


def test_check_structural_idempotency_different_graphs_not_idempotent() -> None:
    """Differing counts → differences populated, score < 1."""
    a = {"m1": _mapping("m1", MappingKind.HIDDEN_STATE)}
    b = {
        "m2": _mapping("m2", MappingKind.HIDDEN_STATE),
        "m3": _mapping("m3", MappingKind.OBSERVATION),
    }
    report = check_structural_idempotency(a, b)
    assert report.is_idempotent is False
    assert len(report.differences) > 0
    # 1 of 2 roles overlap → 1/2 = 0.5
    assert 0.0 < report.score < 1.0


def test_check_structural_idempotency_both_empty_score_zero() -> None:
    """Two empty graphs → score 0.0 and is_idempotent True (no diffs)."""
    report = check_structural_idempotency({}, {})
    assert report.score == 0.0
    assert report.is_idempotent is True
    assert report.differences == []


def test_check_structural_idempotency_one_empty_one_populated() -> None:
    """Empty + populated → not idempotent, score 0."""
    a: dict = {}
    b = {"m1": _mapping("m1", MappingKind.HIDDEN_STATE)}
    report = check_structural_idempotency(a, b)
    assert report.is_idempotent is False
    assert report.score == 0.0


# ------------------------------------------------------------------ #
# check_semantic_idempotency
# ------------------------------------------------------------------ #


def test_check_semantic_idempotency_identical() -> None:
    a = {
        "m1": _mapping("m1", MappingKind.HIDDEN_STATE),
        "m2": _mapping("m2", MappingKind.OBSERVATION),
        "m3": _mapping("m3", MappingKind.OBSERVATION),
    }
    b = dict(a)
    report = check_semantic_idempotency(a, b)
    assert report.is_idempotent is True
    assert report.score == 1.0


def test_check_semantic_idempotency_differs() -> None:
    a = {
        "m1": _mapping("m1", MappingKind.HIDDEN_STATE),
        "m2": _mapping("m2", MappingKind.OBSERVATION),
    }
    b = {
        "m1": _mapping("m1", MappingKind.HIDDEN_STATE),
        "m2": _mapping("m2", MappingKind.ACTION),
    }
    report = check_semantic_idempotency(a, b)
    assert report.is_idempotent is False
    assert "OBSERVATION" in str(report.differences) or "ACTION" in str(report.differences)
    # 1 of 2 roles overlap → score 1/3 (intersection 1, union 3 because
    # disjoint OBSERVATION + ACTION add to union)
    assert 0.0 < report.score < 1.0


def test_check_semantic_idempotency_both_empty() -> None:
    report = check_semantic_idempotency({}, {})
    assert report.score == 0.0
    assert report.is_idempotent is True


def test_check_semantic_idempotency_one_empty_one_populated() -> None:
    report = check_semantic_idempotency({}, {"m1": _mapping("m1", MappingKind.HIDDEN_STATE)})
    assert report.is_idempotent is False
    assert report.score == 0.0


# ------------------------------------------------------------------ #
# _role_multiset_from_model — POLICY annotation branch
# ------------------------------------------------------------------ #


def test_role_multiset_policy_annotation_added_when_not_already_a_slot() -> None:
    """``G=ExpectedFreeEnergy`` without G in any slot → POLICY tick added."""
    model = ReverseGNNModel(
        hidden_states=["s_f0"],
        annotations={"G": "ExpectedFreeEnergy"},  # maps to POLICY
    )
    roles = _role_multiset_from_model(model)
    assert roles["POLICY"] >= 1
    assert roles["HIDDEN_STATE"] == 1


def test_role_multiset_policy_annotation_skipped_when_var_in_existing_slot() -> None:
    """If the annotated variable already lives in a slot, no extra POLICY tick."""
    model = ReverseGNNModel(
        hidden_states=["G"],  # variable already accounted for
        annotations={"G": "ExpectedFreeEnergy"},
    )
    roles = _role_multiset_from_model(model)
    # POLICY entry should not be incremented because G is in hidden_states.
    assert roles.get("POLICY", 0) == 0


def test_role_multiset_non_policy_annotation_ignored() -> None:
    """Annotations that don't map to POLICY are dropped from the late branch."""
    model = ReverseGNNModel(
        observations=["o_m0"],
        annotations={"o_m0": "Observation"},  # maps to OBSERVATION, not POLICY
    )
    roles = _role_multiset_from_model(model)
    assert roles["OBSERVATION"] == 1
    assert roles.get("POLICY", 0) == 0


def test_role_multiset_policy_already_in_policies_skipped() -> None:
    """If the annotated variable is in ``policies``, the late POLICY branch
    is skipped (the early ``policies`` count already captured it)."""
    model = ReverseGNNModel(
        policies=["G"],
        annotations={"G": "ExpectedFreeEnergy"},
    )
    roles = _role_multiset_from_model(model)
    # Exactly one POLICY (from len(policies)), not double-counted.
    assert roles["POLICY"] == 1


# ------------------------------------------------------------------ #
# _model_matrices — A/B/C/D presence/absence
# ------------------------------------------------------------------ #


def test_model_matrices_only_includes_non_empty() -> None:
    model = ReverseGNNModel(
        A=[[0.5, 0.5]],
        B=[],
        C=[1.0, 2.0],
        D=[0.5, 0.5],
    )
    out = _model_matrices(model)
    assert "A" in out
    assert "B" not in out  # empty list is falsy
    assert "C" in out
    assert "D" in out


def test_model_matrices_all_empty() -> None:
    model = ReverseGNNModel()
    assert _model_matrices(model) == {}


# ------------------------------------------------------------------ #
# _state_space_matrices — both branches
# ------------------------------------------------------------------ #


def test_state_space_matrices_none_returns_empty() -> None:
    assert _state_space_matrices(None) == {}


def test_state_space_matrices_with_attributes() -> None:
    """Object exposing A/B/C/D attributes → those keys appear in result."""

    class _SS:
        def __init__(self) -> None:
            self.A = [[1.0]]
            self.B = None  # missing slot is filtered
            self.C = [0.5]
            # D not defined at all
            self.E = "irrelevant"  # not in keys whitelist

    out = _state_space_matrices(_SS())
    assert "A" in out
    assert "C" in out
    assert "B" not in out
    assert "D" not in out
    assert "E" not in out


# ------------------------------------------------------------------ #
# _nodes_edges_from_mappings — kind=None skip + iterable form
# ------------------------------------------------------------------ #


def test_nodes_edges_from_mappings_none_returns_empty() -> None:
    nodes, edges = _nodes_edges_from_mappings(None)
    assert nodes == []
    assert edges == []


def test_nodes_edges_from_mappings_skips_kindless_entries() -> None:
    class _Bad:
        kind = None  # falsy → skipped

    good = _mapping("g1", MappingKind.HIDDEN_STATE)
    nodes, _ = _nodes_edges_from_mappings({"a": _Bad(), "b": good})
    # Only the good mapping should produce a node.
    assert len(nodes) == 1
    assert nodes[0]["role"] == "HIDDEN_STATE"


def test_nodes_edges_from_mappings_iterable_form() -> None:
    """Non-dict iterables also work (the branch via list(mappings))."""
    seq = [_mapping("m1", MappingKind.OBSERVATION)]
    nodes, _ = _nodes_edges_from_mappings(seq)
    assert nodes == [{"role": "OBSERVATION"}]


# ------------------------------------------------------------------ #
# _role_multiset_from_mappings — None and iterable forms
# ------------------------------------------------------------------ #


def test_role_multiset_from_mappings_none() -> None:
    roles = _role_multiset_from_mappings(None)
    assert roles == {}


def test_role_multiset_from_mappings_iterable() -> None:
    seq = [
        _mapping("m1", MappingKind.HIDDEN_STATE),
        _mapping("m2", MappingKind.HIDDEN_STATE),
        _mapping("m3", MappingKind.OBSERVATION),
    ]
    roles = _role_multiset_from_mappings(seq)
    assert roles["HIDDEN_STATE"] == 2
    assert roles["OBSERVATION"] == 1


# ------------------------------------------------------------------ #
# RoundtripResult.summary
# ------------------------------------------------------------------ #


def test_roundtrip_result_summary_iso_status() -> None:
    res = RoundtripResult(
        is_isomorphic=True,
        role_match_score=0.9,
        matrix_score=0.5,
        structural_score=0.7,
        original_roles={"HIDDEN_STATE": 1},
        synthesized_roles={"HIDDEN_STATE": 1},
    )
    summary = res.summary()
    assert "ISO" in summary
    assert "role_match=" in summary
    assert "90.00%" in summary
    assert "matrix=0.50" in summary
    assert "struct=0.70" in summary


def test_roundtrip_result_summary_drift_status() -> None:
    res = RoundtripResult(
        is_isomorphic=False,
        role_match_score=0.1,
    )
    summary = res.summary()
    assert "DRIFT" in summary


# ------------------------------------------------------------------ #
# IdempotencyReport defaults
# ------------------------------------------------------------------ #


def test_idempotency_report_defaults() -> None:
    rep = IdempotencyReport()
    assert rep.is_idempotent is False
    assert rep.forward_roles == {}
    assert rep.reverse_roles == {}
    assert rep.differences == []
    assert rep.score == 0.0
