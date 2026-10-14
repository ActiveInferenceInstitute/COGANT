"""Merging provenance trackers must not drop evidence on record-id collisions.

Record ids are ``prov_<target>_<n>`` with ``n`` the tracker's record count,
so two independent trackers both mint ``prov_node_1_0`` for their first
record on ``node_1``. ``merge_tracker`` used to skip any incoming record
whose id already existed, silently discarding the other tracker's evidence
and skewing ``compute_target_confidence`` and the coverage statistics.
"""

from __future__ import annotations

import pytest

from cogant.provenance.tracker import ProvenanceTracker

pytestmark = pytest.mark.unit


def _static_tracker() -> ProvenanceTracker:
    tracker = ProvenanceTracker()
    tracker.add_record("node_1", "node", "code_pattern", "a.py:1", "static", confidence=0.6)
    return tracker


def _dynamic_tracker() -> ProvenanceTracker:
    tracker = ProvenanceTracker()
    tracker.add_record("node_1", "node", "test", "test_a.py:3", "coverage", confidence=0.9)
    tracker.add_record("node_2", "node", "test", "test_a.py:9", "coverage", confidence=0.8)
    return tracker


def test_merge_keeps_evidence_whose_id_collides() -> None:
    merged = _static_tracker()
    other = _dynamic_tracker()

    merged.merge_tracker(other)

    assert merged.get_record_count() == 3
    node_1 = merged.get_records_for_target("node_1")
    assert sorted(r.evidence_type for r in node_1) == ["code_pattern", "test"]
    assert all(merged.get_record(r.id) is r for r in node_1)
    assert len({r.id for r in merged.records.values()}) == 3
    assert merged.compute_target_confidence("node_1") == pytest.approx((0.6 + 0.9) / 2 + 0.04)
    # The source tracker is left untouched.
    assert [r.id for r in other.get_records_for_target("node_1")] == ["prov_node_1_0"]


def test_merging_the_same_tracker_twice_is_idempotent() -> None:
    merged = _static_tracker()
    other = _dynamic_tracker()

    merged.merge_tracker(other)
    merged.merge_tracker(other)

    assert merged.get_record_count() == 3
    assert len(merged.get_records_for_target("node_1")) == 2


def test_records_added_after_a_merge_get_fresh_ids() -> None:
    merged = _static_tracker()
    merged.merge_tracker(_dynamic_tracker())

    new_id = merged.add_record("node_1", "node", "annotation", "a.py:2", "docs")

    assert merged.get_record_count() == 4
    assert len(merged.get_records_for_target("node_1")) == 3
    assert merged.get_record(new_id) is not None
    assert merged.get_record(new_id).evidence_type == "annotation"
