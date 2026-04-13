"""Smoke tests for cogant.translate.review.ReviewManager.

Covers the core review operations (accept / reject / edit / split / merge),
review history tracking, status filtering, summaries, and export.
"""

from __future__ import annotations

import pytest

from cogant.schemas.semantic import ConfidenceTier, MappingKind, SemanticMapping
from cogant.translate.review import ReviewManager


def _make_mapping(
    mid: str,
    label: str = "example",
    score: float = 0.5,
    kind: MappingKind = MappingKind.OBSERVATION,
) -> SemanticMapping:
    return SemanticMapping(
        id=mid,
        kind=kind,
        graph_fragment_node_ids=[f"{mid}_n0", f"{mid}_n1"],
        graph_fragment_edge_ids=[f"{mid}_e0"],
        semantic_label=label,
        description=f"mapping {mid}",
        confidence_score=score,
        confidence_tier=ConfidenceTier.STATIC_ONLY,
    )


# --------------------------- Construction / add -------------------------- #


def test_review_manager_starts_empty():
    mgr = ReviewManager()
    assert mgr.mappings == {}
    assert mgr.review_history == []
    assert mgr.get_review_summary()["total_mappings"] == 0


def test_add_mapping_stores_by_id():
    mgr = ReviewManager()
    m = _make_mapping("m1")
    mgr.add_mapping(m)
    assert mgr.get_mapping_for_review("m1") is m
    assert mgr.get_mapping_for_review("missing") is None


# ------------------------------ accept() ---------------------------------- #


def test_accept_updates_status_tier_and_confidence():
    mgr = ReviewManager()
    m = _make_mapping("m1", score=0.5)
    mgr.add_mapping(m)

    ok = mgr.accept_mapping("m1", reviewer="alice", feedback="looks good")
    assert ok is True
    assert m.status == "accepted"
    assert m.reviewed_by == "alice"
    assert m.reviewed_at is not None
    assert m.review_feedback == "looks good"
    assert m.confidence_tier == ConfidenceTier.HUMAN_REVIEWED
    assert m.confidence_score == pytest.approx(0.65)


def test_accept_missing_mapping_returns_false():
    mgr = ReviewManager()
    assert mgr.accept_mapping("nope", reviewer="alice") is False


def test_accept_already_human_reviewed_no_double_boost():
    """Accepting an already-human-reviewed mapping does not re-boost confidence."""
    mgr = ReviewManager()
    m = _make_mapping("m1", score=0.9)
    m.confidence_tier = ConfidenceTier.HUMAN_REVIEWED
    mgr.add_mapping(m)

    mgr.accept_mapping("m1", reviewer="bob")
    assert m.confidence_score == 0.9  # untouched


# ------------------------------- reject() --------------------------------- #


def test_reject_marks_status_and_zeros_confidence():
    mgr = ReviewManager()
    m = _make_mapping("m1", score=0.8)
    mgr.add_mapping(m)

    ok = mgr.reject_mapping("m1", reviewer="alice", reason="false positive")
    assert ok is True
    assert m.status == "rejected"
    assert m.confidence_score == 0.0
    assert m.review_feedback == "false positive"
    assert m.reviewed_by == "alice"


def test_reject_missing_mapping_returns_false():
    mgr = ReviewManager()
    assert mgr.reject_mapping("nope", reviewer="alice", reason="gone") is False


# -------------------------------- edit() ---------------------------------- #


def test_edit_updates_fields_and_status():
    mgr = ReviewManager()
    m = _make_mapping("m1", label="old label")
    mgr.add_mapping(m)

    ok = mgr.edit_mapping(
        "m1",
        reviewer="carol",
        updates={"semantic_label": "new label", "description": "updated"},
    )
    assert ok is True
    assert m.semantic_label == "new label"
    assert m.description == "updated"
    assert m.status == "edited"
    assert m.reviewed_by == "carol"


def test_edit_ignores_unknown_fields():
    mgr = ReviewManager()
    m = _make_mapping("m1")
    mgr.add_mapping(m)
    ok = mgr.edit_mapping(
        "m1", reviewer="carol", updates={"bogus_field": "nope", "description": "ok"}
    )
    assert ok is True
    assert m.description == "ok"
    assert not hasattr(m, "bogus_field") or getattr(m, "bogus_field", None) != "nope"


def test_edit_missing_mapping_returns_false():
    mgr = ReviewManager()
    assert mgr.edit_mapping("nope", reviewer="x", updates={}) is False


# -------------------------------- split() --------------------------------- #


def test_split_creates_new_mappings_and_marks_original():
    mgr = ReviewManager()
    m = _make_mapping("m1")
    mgr.add_mapping(m)

    new_ids = mgr.split_mapping(
        "m1",
        reviewer="dave",
        split_definitions=[
            {"label": "part_a", "node_ids": ["m1_n0"]},
            {"label": "part_b", "node_ids": ["m1_n1"]},
        ],
    )
    assert len(new_ids) == 2
    assert m.status == "split"
    for nid in new_ids:
        child = mgr.get_mapping_for_review(nid)
        assert child is not None
        assert child.confidence_tier == ConfidenceTier.HUMAN_REVIEWED
        assert child.reviewed_by == "dave"


def test_split_missing_mapping_returns_empty():
    mgr = ReviewManager()
    assert mgr.split_mapping("nope", reviewer="dave", split_definitions=[]) == []


# ------------------------------- merge() ---------------------------------- #


def test_merge_combines_mappings_and_marks_originals():
    mgr = ReviewManager()
    m1 = _make_mapping("mapping1")
    m2 = _make_mapping("mapping2")
    mgr.add_mapping(m1)
    mgr.add_mapping(m2)

    merged_id = mgr.merge_mappings(
        ["mapping1", "mapping2"],
        reviewer="eve",
        merged_definition={
            "kind": MappingKind.HIDDEN_STATE,
            "label": "combined",
            "description": "merged two",
        },
    )
    assert merged_id is not None
    merged = mgr.get_mapping_for_review(merged_id)
    assert merged is not None
    assert merged.semantic_label == "combined"
    assert merged.confidence_tier == ConfidenceTier.HUMAN_REVIEWED
    assert set(merged.graph_fragment_node_ids) == {
        "mapping1_n0",
        "mapping1_n1",
        "mapping2_n0",
        "mapping2_n1",
    }
    assert m1.status == "merged"
    assert m2.status == "merged"


def test_merge_returns_none_if_any_missing():
    mgr = ReviewManager()
    mgr.add_mapping(_make_mapping("m1"))
    assert (
        mgr.merge_mappings(
            ["m1", "missing"],
            reviewer="eve",
            merged_definition={},
        )
        is None
    )


# --------------------------- history / summary ---------------------------- #


def test_review_history_tracked_across_operations():
    mgr = ReviewManager()
    mgr.add_mapping(_make_mapping("m1"))
    mgr.add_mapping(_make_mapping("m2"))
    mgr.add_mapping(_make_mapping("m3"))

    mgr.accept_mapping("m1", reviewer="alice")
    mgr.reject_mapping("m2", reviewer="alice", reason="bad")
    mgr.edit_mapping("m3", reviewer="alice", updates={"description": "new"})

    history = mgr.get_review_history()
    assert [event["action"] for event in history] == ["accept", "reject", "edit"]
    assert all(event["reviewer"] == "alice" for event in history)
    # get_review_history() returns a copy — mutating it should not affect internal state.
    history.clear()
    assert len(mgr.get_review_history()) == 3


def test_get_mappings_by_status_and_unreviewed():
    mgr = ReviewManager()
    for i in range(3):
        mgr.add_mapping(_make_mapping(f"m{i}"))
    mgr.accept_mapping("m0", reviewer="x")
    mgr.reject_mapping("m1", reviewer="x", reason="r")

    accepted = mgr.get_mappings_by_status("accepted")
    rejected = mgr.get_mappings_by_status("rejected")
    unreviewed = mgr.get_unreviewed_mappings()
    assert len(accepted) == 1
    assert len(rejected) == 1
    assert len(unreviewed) == 1
    assert unreviewed[0].id == "m2"


def test_review_summary_reports_counts():
    mgr = ReviewManager()
    mgr.add_mapping(_make_mapping("m1"))
    mgr.add_mapping(_make_mapping("m2"))
    mgr.accept_mapping("m1", reviewer="x")

    summary = mgr.get_review_summary()
    assert summary["total_mappings"] == 2
    assert summary["by_status"]["accepted"] == 1
    assert summary["by_status"]["auto_proposed"] == 1
    assert summary["unreviewed_count"] == 1
    assert summary["total_review_actions"] == 1


# -------------------------------- export ---------------------------------- #


def test_export_reviewed_mappings_filters_by_status():
    mgr = ReviewManager()
    for i in range(4):
        mgr.add_mapping(_make_mapping(f"m{i}"))
    mgr.accept_mapping("m0", reviewer="x")
    mgr.reject_mapping("m1", reviewer="x", reason="r")
    mgr.edit_mapping("m2", reviewer="x", updates={"description": "d"})
    # m3 untouched.

    exported = mgr.export_reviewed_mappings()
    exported_ids = {m.id for m in exported}
    assert "m0" in exported_ids  # accepted
    assert "m2" in exported_ids  # edited
    assert "m1" not in exported_ids  # rejected
    assert "m3" not in exported_ids  # auto_proposed
