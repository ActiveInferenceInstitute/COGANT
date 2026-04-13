"""Tests for cogant.provenance.tracker.

Verifies the ProvenanceTracker implementation — adding evidence records,
retrieving them by target/type/method, computing target confidence,
merging trackers, querying, and serializing via dataclasses.asdict().
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime

import pytest

from cogant.provenance import ProvenanceRecord, ProvenanceTracker


# ------------------------------- Construction ----------------------------- #


def test_empty_tracker_state():
    """A freshly constructed tracker is empty."""
    tracker = ProvenanceTracker()
    assert tracker.get_record_count() == 0
    assert tracker.get_target_count() == 0
    assert tracker.get_records_for_target("missing") == []
    assert tracker.get_record("missing") is None
    assert tracker.compute_target_confidence("missing") == 0.0

    stats = tracker.get_coverage_statistics()
    assert stats["total_records"] == 0
    assert stats["total_targets"] == 0
    assert stats["avg_confidence"] == 0.0
    assert stats["by_target_type"] == {}
    assert stats["by_evidence_type"] == {}
    assert stats["by_method"] == {}


# ----------------------------- add_record path ---------------------------- #


def test_add_record_creates_and_indexes_entry():
    """add_record() returns an ID, stores a ProvenanceRecord, and indexes by target."""
    tracker = ProvenanceTracker()
    rid = tracker.add_record(
        target_id="node_foo",
        target_type="node",
        evidence_type="code_pattern",
        evidence_location="src/module.py:42",
        extraction_method="ast_parser",
        confidence=0.8,
        metadata={"parser": "python"},
    )

    assert rid.startswith("prov_node_foo_")
    assert tracker.get_record_count() == 1
    assert tracker.get_target_count() == 1

    record = tracker.get_record(rid)
    assert isinstance(record, ProvenanceRecord)
    assert record.target_id == "node_foo"
    assert record.target_type == "node"
    assert record.evidence_type == "code_pattern"
    assert record.evidence_location == "src/module.py:42"
    assert record.extraction_method == "ast_parser"
    assert record.confidence == 0.8
    assert record.metadata == {"parser": "python"}
    assert isinstance(record.timestamp, datetime)

    by_target = tracker.get_records_for_target("node_foo")
    assert len(by_target) == 1
    assert by_target[0].id == rid


def test_add_record_clamps_confidence():
    """Confidence outside [0, 1] is clamped."""
    tracker = ProvenanceTracker()
    low = tracker.add_record(
        target_id="n1",
        target_type="node",
        evidence_type="inference",
        evidence_location="-",
        extraction_method="m",
        confidence=-0.5,
    )
    high = tracker.add_record(
        target_id="n2",
        target_type="node",
        evidence_type="inference",
        evidence_location="-",
        extraction_method="m",
        confidence=1.5,
    )
    assert tracker.get_record(low).confidence == 0.0
    assert tracker.get_record(high).confidence == 1.0


def test_add_record_default_metadata_is_empty_dict():
    """Omitted metadata defaults to an empty dict (not shared state)."""
    tracker = ProvenanceTracker()
    rid1 = tracker.add_record("n1", "node", "test", "-", "m")
    rid2 = tracker.add_record("n2", "node", "test", "-", "m")
    r1 = tracker.get_record(rid1)
    r2 = tracker.get_record(rid2)
    assert r1.metadata == {}
    assert r2.metadata == {}
    # Mutating one should not leak into the other.
    r1.metadata["key"] = "value"
    assert r2.metadata == {}


def test_multiple_records_for_same_target():
    """Multiple records for the same target are all retrievable."""
    tracker = ProvenanceTracker()
    tracker.add_record("node_A", "node", "code_pattern", "file.py:1", "m1", 0.6)
    tracker.add_record("node_A", "node", "test", "test.py:3", "m2", 0.9)
    tracker.add_record("node_A", "node", "annotation", "file.py:2", "m3", 0.7)

    records = tracker.get_records_for_target("node_A")
    assert len(records) == 3
    assert tracker.get_target_count() == 1
    assert tracker.get_record_count() == 3


# ------------------------------ Confidence ------------------------------- #


def test_compute_target_confidence_averages_with_diversity_bonus():
    """compute_target_confidence averages evidence confidences and adds diversity."""
    tracker = ProvenanceTracker()
    tracker.add_record("n", "node", "code_pattern", "-", "m", 0.6)
    tracker.add_record("n", "node", "test", "-", "m", 0.8)
    tracker.add_record("n", "node", "annotation", "-", "m", 0.7)

    conf = tracker.compute_target_confidence("n")
    avg = (0.6 + 0.8 + 0.7) / 3
    # Diversity bonus = min(0.1, 3 * 0.02) = 0.06
    assert conf == pytest.approx(min(1.0, avg + 0.06), rel=1e-9)


def test_compute_target_confidence_caps_at_one():
    """Confidence is capped at 1.0 even with large averages and diversity bonus."""
    tracker = ProvenanceTracker()
    for ev in ("a", "b", "c", "d", "e"):
        tracker.add_record("n", "node", ev, "-", "m", 1.0)
    assert tracker.compute_target_confidence("n") == 1.0


# ---------------------------- Querying methods ---------------------------- #


def test_get_records_by_type_and_evidence_and_method():
    """Records can be filtered by target type, evidence type, and method."""
    tracker = ProvenanceTracker()
    tracker.add_record("n1", "node", "code_pattern", "-", "ast", 0.5)
    tracker.add_record("n2", "edge", "code_pattern", "-", "ast", 0.5)
    tracker.add_record("n3", "node", "test", "-", "pytest", 0.9)

    assert len(tracker.get_records_by_type("node")) == 2
    assert len(tracker.get_records_by_type("edge")) == 1
    assert len(tracker.get_records_by_evidence_type("code_pattern")) == 2
    assert len(tracker.get_records_by_evidence_type("test")) == 1
    assert len(tracker.get_records_by_method("ast")) == 2
    assert len(tracker.get_records_by_method("pytest")) == 1


def test_query_records_multi_criteria():
    """query_records supports combining filters and min_confidence threshold."""
    tracker = ProvenanceTracker()
    tracker.add_record("n1", "node", "code_pattern", "-", "ast", 0.9)
    tracker.add_record("n1", "node", "test", "-", "pytest", 0.4)
    tracker.add_record("n2", "node", "code_pattern", "-", "ast", 0.5)

    high_conf_n1 = tracker.query_records(target_id="n1", min_confidence=0.7)
    assert len(high_conf_n1) == 1
    assert high_conf_n1[0].confidence == 0.9

    all_nodes = tracker.query_records(target_type="node")
    assert len(all_nodes) == 3

    code_pattern = tracker.query_records(evidence_type="code_pattern")
    assert len(code_pattern) == 2


# ------------------------------ Statistics -------------------------------- #


def test_coverage_statistics_aggregates():
    """get_coverage_statistics rolls up counts and averages."""
    tracker = ProvenanceTracker()
    tracker.add_record("n1", "node", "code_pattern", "-", "ast", 0.8)
    tracker.add_record("n1", "node", "test", "-", "pytest", 0.6)
    tracker.add_record("e1", "edge", "code_pattern", "-", "ast", 1.0)

    stats = tracker.get_coverage_statistics()
    assert stats["total_records"] == 3
    assert stats["total_targets"] == 2
    assert stats["avg_confidence"] == pytest.approx((0.8 + 0.6 + 1.0) / 3)
    assert stats["by_target_type"] == {"node": 2, "edge": 1}
    assert stats["by_evidence_type"] == {"code_pattern": 2, "test": 1}
    assert stats["by_method"] == {"ast": 2, "pytest": 1}


# ------------------------------ Merge / clear ----------------------------- #


def test_merge_tracker_combines_records():
    """merge_tracker copies records from another tracker without duplicating."""
    t1 = ProvenanceTracker()
    t2 = ProvenanceTracker()

    t1.add_record("a", "node", "code_pattern", "-", "m1", 0.5)
    t2.add_record("b", "node", "test", "-", "m2", 0.9)

    t1.merge_tracker(t2)
    assert t1.get_record_count() == 2
    assert t1.get_target_count() == 2

    # Merging again is idempotent (record IDs match).
    t1.merge_tracker(t2)
    assert t1.get_record_count() == 2


def test_clear_resets_state():
    """clear() empties all records and indices."""
    tracker = ProvenanceTracker()
    tracker.add_record("n", "node", "t", "-", "m", 0.5)
    tracker.clear()
    assert tracker.get_record_count() == 0
    assert tracker.get_target_count() == 0


# ----------------------------- Serialization ------------------------------ #


def test_record_serialization_to_json():
    """ProvenanceRecord dataclass can round-trip through JSON via asdict()."""
    tracker = ProvenanceTracker()
    rid = tracker.add_record(
        target_id="n1",
        target_type="node",
        evidence_type="code_pattern",
        evidence_location="file.py:10",
        extraction_method="ast",
        confidence=0.75,
        metadata={"lang": "python"},
    )
    record = tracker.get_record(rid)
    payload = asdict(record)
    # datetime is not JSON-native; convert manually.
    payload["timestamp"] = payload["timestamp"].isoformat()
    blob = json.dumps(payload)
    parsed = json.loads(blob)
    assert parsed["target_id"] == "n1"
    assert parsed["confidence"] == 0.75
    assert parsed["metadata"] == {"lang": "python"}


def test_all_records_serialize_to_json_array():
    """A whole tracker can be serialized by mapping over records."""
    tracker = ProvenanceTracker()
    tracker.add_record("n1", "node", "code_pattern", "-", "ast", 0.8)
    tracker.add_record("n2", "node", "test", "-", "pytest", 0.6)

    serialized = []
    for rec in tracker.records.values():
        payload = asdict(rec)
        payload["timestamp"] = payload["timestamp"].isoformat()
        serialized.append(payload)

    blob = json.dumps(serialized)
    parsed = json.loads(blob)
    assert len(parsed) == 2
    ids = {entry["target_id"] for entry in parsed}
    assert ids == {"n1", "n2"}
