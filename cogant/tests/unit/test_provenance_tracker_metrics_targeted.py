#!/usr/bin/env python3
"""Targeted branch tests — provenance/tracker.py and metrics.py.

Covers:
- provenance/tracker.py: ProvenanceRecord, ProvenanceTracker (add_record,
  get_records_for_target, get_record, compute_target_confidence,
  get_records_by_type, get_records_by_evidence_type, get_records_by_method,
  get_coverage_statistics, query_records, merge_tracker, clear,
  get_record_count, get_target_count)
- metrics.py: load, version, test_count, coverage, mypy_errors, isomorphic_count,
  total_targets, mean_epsilon, epsilon_for, bibliography_entries
"""

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# provenance/tracker.py — ProvenanceTracker
# ---------------------------------------------------------------------------


class TestProvenanceTracker:
    def _make_tracker(self):
        from cogant.provenance.tracker import ProvenanceTracker

        return ProvenanceTracker()

    def _add_sample_record(self, tracker):
        return tracker.add_record(
            target_id="node_001",
            target_type="node",
            evidence_type="code_pattern",
            evidence_location="src/module.py:42",
            extraction_method="ast_visitor",
            confidence=0.85,
        )

    def test_init_empty(self):
        tracker = self._make_tracker()
        assert tracker.get_record_count() == 0
        assert tracker.get_target_count() == 0

    def test_add_record_returns_id(self):
        tracker = self._make_tracker()
        record_id = self._add_sample_record(tracker)
        assert isinstance(record_id, str)
        assert len(record_id) > 0

    def test_add_record_increments_count(self):
        tracker = self._make_tracker()
        self._add_sample_record(tracker)
        assert tracker.get_record_count() == 1
        assert tracker.get_target_count() == 1

    def test_add_multiple_records_same_target(self):
        tracker = self._make_tracker()
        tracker.add_record("t1", "node", "code_pattern", "a.py:1", "method_a", 0.9)
        tracker.add_record("t1", "node", "test", "test_a.py:1", "method_b", 0.7)
        assert tracker.get_record_count() == 2
        assert tracker.get_target_count() == 1  # Same target

    def test_get_records_for_target(self):
        from cogant.provenance.tracker import ProvenanceRecord

        tracker = self._make_tracker()
        self._add_sample_record(tracker)
        records = tracker.get_records_for_target("node_001")
        assert len(records) == 1
        assert isinstance(records[0], ProvenanceRecord)

    def test_get_records_for_nonexistent_target(self):
        tracker = self._make_tracker()
        records = tracker.get_records_for_target("nonexistent")
        assert records == []

    def test_get_record_by_id(self):
        from cogant.provenance.tracker import ProvenanceRecord

        tracker = self._make_tracker()
        record_id = self._add_sample_record(tracker)
        record = tracker.get_record(record_id)
        assert record is not None
        assert isinstance(record, ProvenanceRecord)
        assert record.id == record_id

    def test_get_record_nonexistent(self):
        tracker = self._make_tracker()
        result = tracker.get_record("no_such_id")
        assert result is None

    def test_compute_target_confidence_no_records(self):
        tracker = self._make_tracker()
        conf = tracker.compute_target_confidence("nonexistent")
        assert conf == 0.0

    def test_compute_target_confidence_with_records(self):
        tracker = self._make_tracker()
        tracker.add_record("t1", "node", "code_pattern", "f.py:1", "method", 0.8)
        tracker.add_record("t1", "node", "test", "f.py:2", "method", 0.6)
        conf = tracker.compute_target_confidence("t1")
        assert 0.0 <= conf <= 1.0

    def test_get_records_by_type(self):
        tracker = self._make_tracker()
        tracker.add_record("t1", "node", "code_pattern", "f.py:1", "m", 0.9)
        tracker.add_record("t2", "edge", "code_pattern", "f.py:2", "m", 0.9)
        nodes = tracker.get_records_by_type("node")
        assert len(nodes) == 1

    def test_get_records_by_evidence_type(self):
        tracker = self._make_tracker()
        tracker.add_record("t1", "node", "code_pattern", "f.py:1", "m", 0.9)
        tracker.add_record("t2", "node", "test", "f.py:2", "m", 0.7)
        code_records = tracker.get_records_by_evidence_type("code_pattern")
        assert len(code_records) == 1

    def test_get_records_by_method(self):
        tracker = self._make_tracker()
        tracker.add_record("t1", "node", "code_pattern", "f.py:1", "ast_visitor", 0.9)
        tracker.add_record("t2", "node", "code_pattern", "f.py:2", "other_method", 0.7)
        ast_records = tracker.get_records_by_method("ast_visitor")
        assert len(ast_records) == 1

    def test_get_coverage_statistics_empty(self):
        tracker = self._make_tracker()
        stats = tracker.get_coverage_statistics()
        assert isinstance(stats, dict)

    def test_get_coverage_statistics_with_records(self):
        tracker = self._make_tracker()
        tracker.add_record("t1", "node", "code_pattern", "f.py:1", "m", 0.9)
        stats = tracker.get_coverage_statistics()
        assert isinstance(stats, dict)
        assert len(stats) > 0

    def test_query_records_empty(self):
        tracker = self._make_tracker()
        results = tracker.query_records()
        assert isinstance(results, list)

    def test_query_records_with_filter(self):
        tracker = self._make_tracker()
        tracker.add_record("t1", "node", "code_pattern", "f.py:1", "m", 0.9)
        tracker.add_record("t2", "edge", "test", "f.py:2", "m", 0.5)
        results = tracker.query_records(target_type="node")
        assert len(results) == 1

    def test_merge_tracker(self):
        tracker_a = self._make_tracker()
        tracker_b = self._make_tracker()
        tracker_a.add_record("t1", "node", "code_pattern", "f.py:1", "m", 0.9)
        tracker_b.add_record("t2", "node", "code_pattern", "f.py:2", "m", 0.8)
        tracker_a.merge_tracker(tracker_b)
        assert tracker_a.get_record_count() == 2

    def test_clear(self):
        tracker = self._make_tracker()
        self._add_sample_record(tracker)
        assert tracker.get_record_count() == 1
        tracker.clear()
        assert tracker.get_record_count() == 0

    def test_confidence_clamped_to_range(self):
        tracker = self._make_tracker()
        tracker.add_record("t1", "node", "cp", "f.py:1", "m", confidence=1.5)
        record = tracker.get_records_for_target("t1")[0]
        assert record.confidence <= 1.0


# ---------------------------------------------------------------------------
# metrics.py — module-level metrics functions
# ---------------------------------------------------------------------------


class TestMetricsModule:
    def test_load_returns_dict(self):
        from cogant import metrics

        result = metrics.load()
        assert isinstance(result, dict)

    def test_version_returns_str(self):
        from cogant import metrics

        v = metrics.version()
        assert isinstance(v, str)

    def test_test_count_returns_int(self):
        from cogant import metrics

        count = metrics.test_count()
        assert isinstance(count, int)
        assert count >= 0

    def test_coverage_returns_float(self):
        from cogant import metrics

        cov = metrics.coverage()
        assert isinstance(cov, float)
        assert cov >= 0.0

    def test_mypy_errors_returns_int(self):
        from cogant import metrics

        errs = metrics.mypy_errors()
        assert isinstance(errs, int)

    def test_isomorphic_count_returns_int(self):
        from cogant import metrics

        count = metrics.isomorphic_count()
        assert isinstance(count, int)

    def test_total_targets_returns_int(self):
        from cogant import metrics

        total = metrics.total_targets()
        assert isinstance(total, int)

    def test_mean_epsilon_returns_float(self):
        from cogant import metrics

        eps = metrics.mean_epsilon()
        assert isinstance(eps, float)

    def test_epsilon_for_known(self):
        from cogant import metrics

        # epsilon_for returns float or None for unknown
        result = metrics.epsilon_for("some_target")
        assert result is None or isinstance(result, float)

    def test_bibliography_entries_returns_int(self):
        from cogant import metrics

        count = metrics.bibliography_entries()
        assert isinstance(count, int)
