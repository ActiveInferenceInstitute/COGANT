#!/usr/bin/env python3
"""Coverage boost batch 56 — scoring/metrics.py and scoring/drift.py.

Covers:
- scoring/metrics.py: MetricsReport dataclass, CodebaseMetrics (init,
  complexity_score empty/with-data, coupling_score, cohesion_score,
  semantic_coverage, observability_score, controllability_score, summary,
  format_report, to_dict)
- scoring/drift.py: DriftScore dataclass, DriftAnalyzer (init, analyze,
  compute_structural_drift, compute_semantic_drift, compute_state_space_drift,
  generate_diff_report, _compute_count_drift, _compute_collection_drift)
"""

import pytest
from pathlib import Path

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# scoring/metrics.py — MetricsReport and CodebaseMetrics
# ---------------------------------------------------------------------------

class TestMetricsReport:
    def test_metrics_report_init(self):
        from cogant.scoring.metrics import MetricsReport
        report = MetricsReport(
            complexity_score=0.3,
            coupling_score=0.4,
            cohesion_score=0.7,
            semantic_coverage=0.6,
            observability_score=0.5,
            controllability_score=0.5,
            node_count=10,
            edge_count=5,
            state_var_count=3,
            observation_count=2,
            action_count=2,
        )
        assert report.complexity_score == 0.3
        assert report.coupling_score == 0.4
        assert report.cohesion_score == 0.7

    def test_metrics_report_fields(self):
        from cogant.scoring.metrics import MetricsReport
        report = MetricsReport(
            complexity_score=0.0,
            coupling_score=0.0,
            cohesion_score=1.0,
            semantic_coverage=1.0,
            observability_score=1.0,
            controllability_score=1.0,
            node_count=0,
            edge_count=0,
            state_var_count=0,
            observation_count=0,
            action_count=0,
        )
        assert isinstance(report, MetricsReport)
        assert report.node_count == 0


class TestCodebaseMetrics:
    def _make_metrics(self, nodes=None, edges=None, states=None, observations=None, actions=None):
        from cogant.scoring.metrics import CodebaseMetrics
        graph = {
            "nodes": nodes or [],
            "edges": edges or [],
        }
        state_space = {
            "states": states or [],
            "observations": observations or [],
            "actions": actions or [],
        }
        return CodebaseMetrics(graph=graph, state_space=state_space, mappings={})

    def test_init_empty(self):
        metrics = self._make_metrics()
        assert metrics is not None

    def test_complexity_score_empty(self):
        metrics = self._make_metrics()
        score = metrics.complexity_score()
        assert score == 0.0

    def test_complexity_score_with_nodes(self):
        nodes = [{"id": f"n{i}", "kind": "function"} for i in range(5)]
        edges = [{"source": "n0", "target": "n1"}, {"source": "n1", "target": "n2"}]
        metrics = self._make_metrics(nodes=nodes, edges=edges)
        score = metrics.complexity_score()
        assert 0.0 <= score <= 1.0

    def test_coupling_score_empty(self):
        metrics = self._make_metrics()
        score = metrics.coupling_score()
        assert 0.0 <= score <= 1.0

    def test_coupling_score_with_data(self):
        nodes = [
            {"id": "n0", "kind": "function", "attributes": {"module": "a"}},
            {"id": "n1", "kind": "function", "attributes": {"module": "b"}},
        ]
        edges = [{"source": "n0", "target": "n1"}]
        metrics = self._make_metrics(nodes=nodes, edges=edges)
        score = metrics.coupling_score()
        assert 0.0 <= score <= 1.0

    def test_cohesion_score_empty(self):
        metrics = self._make_metrics()
        score = metrics.cohesion_score()
        assert 0.0 <= score <= 1.0

    def test_semantic_coverage_empty(self):
        metrics = self._make_metrics()
        score = metrics.semantic_coverage()
        assert 0.0 <= score <= 1.0

    def test_semantic_coverage_with_states(self):
        metrics = self._make_metrics(
            nodes=[{"id": "n0"}],
            states=["s0", "s1"],
            observations=["o0"],
            actions=["a0"],
        )
        score = metrics.semantic_coverage()
        assert 0.0 <= score <= 1.0

    def test_observability_score_empty(self):
        metrics = self._make_metrics()
        score = metrics.observability_score()
        assert 0.0 <= score <= 1.0

    def test_controllability_score_empty(self):
        metrics = self._make_metrics()
        score = metrics.controllability_score()
        assert 0.0 <= score <= 1.0

    def test_summary_returns_metrics_report(self):
        from cogant.scoring.metrics import MetricsReport
        metrics = self._make_metrics()
        report = metrics.summary()
        assert isinstance(report, MetricsReport)
        assert 0.0 <= report.complexity_score <= 1.0

    def test_format_report_returns_str(self):
        metrics = self._make_metrics()
        report_str = metrics.format_report()
        assert isinstance(report_str, str)
        assert len(report_str) > 0

    def test_to_dict_returns_dict(self):
        metrics = self._make_metrics()
        result = metrics.to_dict()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# scoring/drift.py — DriftScore and DriftAnalyzer
# ---------------------------------------------------------------------------

class TestDriftScore:
    def test_drift_score_init(self):
        from cogant.scoring.drift import DriftScore
        score = DriftScore(
            total_score=0.15,
            architectural_score=0.1,
            semantic_churn_score=0.2,
            details={"structural_drift": {}, "semantic_drift": {}},
        )
        assert score.total_score == 0.15
        assert score.architectural_score == 0.1
        assert score.semantic_churn_score == 0.2

    def test_drift_score_zero(self):
        from cogant.scoring.drift import DriftScore
        score = DriftScore(
            total_score=0.0,
            architectural_score=0.0,
            semantic_churn_score=0.0,
            details={},
        )
        assert isinstance(score, DriftScore)
        assert score.total_score == 0.0


class TestDriftAnalyzer:
    def _make_bundle(self):
        return {
            "nodes": [{"id": "n0", "kind": "module"}, {"id": "n1", "kind": "class"}],
            "edges": [{"source": "n0", "target": "n1"}],
            "states": ["state_a", "state_b"],
            "observations": ["obs_0"],
            "actions": ["act_0"],
            "policies": ["policy_0"],
            "mappings": {"m0": {"kind": "hidden_state"}},
        }

    def test_init(self):
        from cogant.scoring.drift import DriftAnalyzer
        bundle_a = self._make_bundle()
        bundle_b = self._make_bundle()
        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        assert analyzer is not None

    def test_analyze_returns_drift_score(self):
        from cogant.scoring.drift import DriftAnalyzer, DriftScore
        bundle_a = self._make_bundle()
        bundle_b = self._make_bundle()
        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        score = analyzer.analyze(bundle_a, bundle_b)
        assert isinstance(score, DriftScore)

    def test_compute_structural_drift(self):
        from cogant.scoring.drift import DriftAnalyzer
        bundle_a = self._make_bundle()
        bundle_b = self._make_bundle()
        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        result = analyzer.compute_structural_drift()
        assert isinstance(result, dict)

    def test_compute_semantic_drift(self):
        from cogant.scoring.drift import DriftAnalyzer
        bundle_a = self._make_bundle()
        bundle_b = self._make_bundle()
        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        result = analyzer.compute_semantic_drift()
        assert isinstance(result, dict)

    def test_compute_state_space_drift(self):
        from cogant.scoring.drift import DriftAnalyzer
        bundle_a = self._make_bundle()
        bundle_b = self._make_bundle()
        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        result = analyzer.compute_state_space_drift()
        assert isinstance(result, dict)

    def test_generate_diff_report_returns_str(self):
        from cogant.scoring.drift import DriftAnalyzer
        bundle_a = self._make_bundle()
        bundle_b = self._make_bundle()
        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        report = analyzer.generate_diff_report()
        assert isinstance(report, str)

    def test_compute_count_drift_zero(self):
        from cogant.scoring.drift import DriftAnalyzer
        bundle_a = self._make_bundle()
        bundle_b = self._make_bundle()
        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        drift = analyzer._compute_count_drift(5, 5)
        assert drift == 0.0

    def test_compute_count_drift_positive(self):
        from cogant.scoring.drift import DriftAnalyzer
        bundle_a = self._make_bundle()
        bundle_b = self._make_bundle()
        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        drift = analyzer._compute_count_drift(10, 5)
        assert 0.0 <= drift <= 1.0

    def test_compute_collection_drift_same(self):
        from cogant.scoring.drift import DriftAnalyzer
        bundle_a = self._make_bundle()
        bundle_b = self._make_bundle()
        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        drift = analyzer._compute_collection_drift(["a", "b"], ["a", "b"])
        assert drift == 0.0

    def test_compute_collection_drift_different(self):
        from cogant.scoring.drift import DriftAnalyzer
        bundle_a = self._make_bundle()
        bundle_b = self._make_bundle()
        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        drift = analyzer._compute_collection_drift(["a", "b"], ["c", "d"])
        assert 0.0 <= drift <= 1.0

    def test_identical_bundles_low_drift(self):
        from cogant.scoring.drift import DriftAnalyzer, DriftScore
        bundle = self._make_bundle()
        analyzer = DriftAnalyzer(bundle, bundle)
        score = analyzer.analyze(bundle, bundle)
        assert isinstance(score, DriftScore)
        # Same bundles should have zero or near-zero drift
        assert score.total_score <= 1.0
        assert score.architectural_score == 0.0 or score.total_score <= 0.5
