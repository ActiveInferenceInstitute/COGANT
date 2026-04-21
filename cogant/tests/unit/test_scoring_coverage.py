"""Additional coverage tests for cogant.scoring.drift and cogant.scoring.metrics.

These tests exercise code paths not already covered by
``test_drift_analysis.py``:

- Legacy bundle-extraction fallbacks (``stage_results.graph`` etc.)
- All legacy private ``_count_*`` / ``_compute_*`` helpers that accept
  two bundles as arguments.
- ``DriftAnalyzer.analyze`` and ``report`` legacy entry points.
- ``generate_diff_report`` / ``generate_diff_mermaid`` full formatting.
- ``to_dict`` serialization.
- ``CodebaseMetrics.format_report`` full markdown formatting.
- Edge cases in complexity, coupling, cohesion, semantic_coverage,
  observability, and controllability scores (empty / single-module
  / zero-edge graphs).

All tests construct the input dicts directly and use the real
``DriftAnalyzer`` / ``CodebaseMetrics`` classes — no mocks.
"""

from __future__ import annotations

import pytest

from cogant.scoring.drift import DriftAnalyzer, DriftScore
from cogant.scoring.metrics import CodebaseMetrics, MetricsReport

# --------------------------------------------------------------------- helpers


def make_bundle(
    node_ids=(),
    edges=(),
    states=(),
    observations=(),
    actions=(),
    policies=(),
    mappings=None,
    legacy=False,
):
    """Build a minimal bundle dict.

    When ``legacy=True`` the graph/state_space are nested under
    ``stage_results`` to exercise the legacy fallback helpers.
    """
    graph = {
        "nodes": [{"id": nid, "kind": "function", "attributes": {}} for nid in node_ids],
        "edges": [{"source": src, "target": tgt, "kind": "CALLS"} for src, tgt in edges],
    }
    state_space = {
        "states": [{"var_id": s} for s in states],
        "observations": [{"modality_id": o, "observes_state_vars": []} for o in observations],
        "actions": [{"action_id": a, "affects_state_vars": []} for a in actions],
        "policies": [{"policy_id": p} for p in policies],
    }
    mappings = mappings or {}
    if legacy:
        return {"stage_results": {"graph": graph, "statespace": state_space}, "mappings": mappings}
    return {"graph": graph, "state_space": state_space, "mappings": mappings}


# ============================================================== DriftAnalyzer


class TestDriftAnalyzerLegacyExtraction:
    """Exercise the stage_results.graph / stage_results.statespace fallback."""

    def test_extracts_graph_from_stage_results(self):
        a = make_bundle(node_ids=("n1", "n2"), edges=(("n1", "n2"),), legacy=True)
        b = make_bundle(
            node_ids=("n1", "n2", "n3"),
            edges=(("n1", "n2"), ("n2", "n3")),
            legacy=True,
        )
        analyzer = DriftAnalyzer(a, b)
        assert len(analyzer.graph_a.get("nodes", [])) == 2
        assert len(analyzer.graph_b.get("nodes", [])) == 3
        assert len(analyzer.ss_a.get("states", [])) == 0

    def test_extract_graph_from_non_dict_bundle(self):
        analyzer = DriftAnalyzer("not a dict", None)  # type: ignore[arg-type]
        assert analyzer.graph_a == {}
        assert analyzer.graph_b == {}
        assert analyzer.ss_a == {}
        assert analyzer.ss_b == {}

    def test_extract_statespace_from_non_dict_bundle(self):
        analyzer = DriftAnalyzer(123, 45.6)  # type: ignore[arg-type]
        assert analyzer.mappings_a == {}
        assert analyzer.mappings_b == {}

    def test_extract_graph_with_empty_stage_results(self):
        a = {"stage_results": "not a dict"}
        analyzer = DriftAnalyzer(a, a)
        assert analyzer.graph_a == {}


class TestDriftAnalyzerLegacyHelpers:
    """Exercise the two-argument ``_count_*`` / ``_compute_*`` helpers."""

    def test_legacy_count_added_nodes(self):
        a = make_bundle(node_ids=("n1",), legacy=True)
        b = make_bundle(node_ids=("n1", "n2", "n3"), legacy=True)
        analyzer = DriftAnalyzer(a, b)

        assert analyzer._count_added_nodes(a, b) == 2

    def test_legacy_count_removed_nodes(self):
        a = make_bundle(node_ids=("n1", "n2", "n3"), legacy=True)
        b = make_bundle(node_ids=("n1",), legacy=True)
        analyzer = DriftAnalyzer(a, b)

        assert analyzer._count_removed_nodes(a, b) == 2

    def test_legacy_count_edge_changes(self):
        a = make_bundle(node_ids=("n1", "n2"), edges=(("n1", "n2"),), legacy=True)
        b = make_bundle(
            node_ids=("n1", "n2", "n3"),
            edges=(("n1", "n2"), ("n2", "n3"), ("n1", "n3")),
            legacy=True,
        )
        analyzer = DriftAnalyzer(a, b)
        assert analyzer._count_edge_changes(a, b) == 2

    def test_legacy_count_added_states(self):
        a = make_bundle(states=("s1",), legacy=True)
        b = make_bundle(states=("s1", "s2", "s3"), legacy=True)
        analyzer = DriftAnalyzer(a, b)
        assert analyzer._count_added_states(a, b) == 2
        # Reverse => 0 (not negative)
        assert analyzer._count_added_states(b, a) == 0

    def test_legacy_count_removed_states(self):
        a = make_bundle(states=("s1", "s2", "s3"), legacy=True)
        b = make_bundle(states=("s1",), legacy=True)
        analyzer = DriftAnalyzer(a, b)
        assert analyzer._count_removed_states(a, b) == 2
        assert analyzer._count_removed_states(b, a) == 0

    def test_legacy_count_observation_changes(self):
        a = make_bundle(observations=("o1",), legacy=True)
        b = make_bundle(observations=("o1", "o2"), legacy=True)
        analyzer = DriftAnalyzer(a, b)
        assert analyzer._count_observation_changes(a, b) == 1

    def test_legacy_count_action_changes(self):
        a = make_bundle(actions=("a1", "a2"), legacy=True)
        b = make_bundle(actions=("a1",), legacy=True)
        analyzer = DriftAnalyzer(a, b)
        assert analyzer._count_action_changes(a, b) == 1

    def test_legacy_count_policy_changes(self):
        a = make_bundle(policies=("p1",), legacy=True)
        b = make_bundle(policies=("p1", "p2", "p3"), legacy=True)
        analyzer = DriftAnalyzer(a, b)
        assert analyzer._count_policy_changes(a, b) == 2

    def test_legacy_compute_architectural_drift(self):
        a = make_bundle(node_ids=("n1", "n2"), edges=(("n1", "n2"),), legacy=True)
        b = make_bundle(
            node_ids=("n1", "n2", "n3", "n4"),
            edges=(("n1", "n2"), ("n2", "n3"), ("n3", "n4")),
            legacy=True,
        )
        analyzer = DriftAnalyzer(a, b)
        drift = analyzer._compute_architectural_drift(a, b)
        assert 0.0 < drift <= 1.0

    def test_legacy_compute_architectural_drift_from_empty_baseline(self):
        a = make_bundle(legacy=True)
        b = make_bundle(node_ids=("n1", "n2"), edges=(("n1", "n2"),), legacy=True)
        analyzer = DriftAnalyzer(a, b)
        drift = analyzer._compute_architectural_drift(a, b)
        # Both nodes_a and edges_a are 0 so node_drift=0.5 and edge_drift=0.5
        assert drift == 0.5

    def test_legacy_compute_architectural_drift_identical_empty(self):
        a = make_bundle(legacy=True)
        analyzer = DriftAnalyzer(a, a)
        drift = analyzer._compute_architectural_drift(a, a)
        assert drift == 0.0

    def test_legacy_compute_semantic_churn(self):
        a = make_bundle(states=("s1",), observations=("o1",), actions=("a1",), legacy=True)
        b = make_bundle(
            states=("s1", "s2"),
            observations=("o1", "o2"),
            actions=("a1", "a2", "a3"),
            legacy=True,
        )
        analyzer = DriftAnalyzer(a, b)
        churn = analyzer._compute_semantic_churn(a, b)
        assert 0.0 < churn <= 1.0

    def test_compute_collection_drift_both_empty(self):
        analyzer = DriftAnalyzer({}, {})
        assert analyzer._compute_collection_drift([], []) == 0.0

    def test_compute_collection_drift_baseline_empty(self):
        analyzer = DriftAnalyzer({}, {})
        assert analyzer._compute_collection_drift([], [1, 2, 3]) == 0.5

    def test_compute_collection_drift_current_empty(self):
        analyzer = DriftAnalyzer({}, {})
        assert analyzer._compute_collection_drift([1, 2, 3], []) == 0.5

    def test_compute_collection_drift_size_change(self):
        analyzer = DriftAnalyzer({}, {})
        drift = analyzer._compute_collection_drift([1, 2], [1, 2, 3, 4])
        assert drift == pytest.approx(0.5)

    def test_compute_count_drift_current_zero(self):
        analyzer = DriftAnalyzer({}, {})
        assert analyzer._compute_count_drift(5, 0) == 0.5


class TestDriftAnalyzerAnalyzeAndReports:
    """Exercise ``analyze``, ``report``, ``generate_diff_*``, ``to_dict``."""

    def test_analyze_legacy_entry_point(self):
        a = make_bundle(node_ids=("n1",), edges=())
        b = make_bundle(node_ids=("n1", "n2"), edges=(("n1", "n2"),))
        analyzer = DriftAnalyzer({}, {})

        drift = analyzer.analyze(a, b)
        assert isinstance(drift, DriftScore)
        assert drift.architectural_score > 0.0

    def test_report_legacy_method(self):
        bundle = make_bundle(node_ids=("n1", "n2"), edges=(("n1", "n2"),))
        analyzer = DriftAnalyzer(bundle, bundle)
        drift = analyzer._compute_drift_score()

        report = analyzer.report(drift)
        assert "Architectural Drift Report" in report
        assert "Overall Drift Score" in report

    def test_generate_diff_report_contains_sections(self):
        a = make_bundle(
            node_ids=("n1", "n2"),
            edges=(("n1", "n2"),),
            states=("s1",),
            observations=("o1",),
            actions=("a1",),
            mappings={"n1": {"kind": "function"}},
        )
        b = make_bundle(
            node_ids=("n1", "n2", "n3"),
            edges=(("n1", "n2"), ("n2", "n3")),
            states=("s1", "s2"),
            observations=("o1", "o2"),
            actions=("a1",),
            mappings={"n1": {"kind": "function"}, "n2": {"kind": "class"}},
        )
        analyzer = DriftAnalyzer(a, b)

        report = analyzer.generate_diff_report()
        assert "# Architectural Drift Report" in report
        assert "## Structural Changes" in report
        assert "## Semantic Changes" in report
        assert "## State Space Changes" in report
        assert "Added: 1" in report  # 1 node added

    def test_generate_diff_mermaid_has_graph_td(self):
        a = make_bundle(node_ids=("n1",))
        b = make_bundle(node_ids=("n1", "n2"), edges=(("n1", "n2"),))
        analyzer = DriftAnalyzer(a, b)

        mermaid = analyzer.generate_diff_mermaid()
        assert mermaid.startswith("graph TD")
        assert "Drift[Architectural Drift Report]" in mermaid
        assert "Added Nodes" in mermaid
        assert "style NA fill:#90EE90" in mermaid

    def test_to_dict_returns_serializable(self):
        a = make_bundle(node_ids=("n1",))
        b = make_bundle(node_ids=("n1", "n2"))
        analyzer = DriftAnalyzer(a, b)

        result = analyzer.to_dict()
        assert set(result.keys()) == {
            "total_score",
            "architectural_score",
            "semantic_churn_score",
            "details",
        }
        assert 0.0 <= result["total_score"] <= 1.0

    def test_structural_drift_changed_nodes(self):
        """Nodes with the same id but different attributes → changed_nodes."""
        a = {
            "graph": {
                "nodes": [{"id": "n1", "kind": "function", "attributes": {"v": 1}}],
                "edges": [],
            },
            "state_space": {},
            "mappings": {},
        }
        b = {
            "graph": {
                "nodes": [{"id": "n1", "kind": "function", "attributes": {"v": 2}}],
                "edges": [],
            },
            "state_space": {},
            "mappings": {},
        }
        analyzer = DriftAnalyzer(a, b)
        struct = analyzer.compute_structural_drift()
        assert struct["nodes_changed_count"] == 1
        assert "n1" in struct["nodes_changed"]

    def test_semantic_drift_changed_mappings(self):
        a = make_bundle(mappings={"m1": {"label": "v1"}, "m2": {"label": "v2"}})
        b = make_bundle(mappings={"m1": {"label": "v1-changed"}, "m3": {"label": "v3"}})
        analyzer = DriftAnalyzer(a, b)

        drift = analyzer.compute_semantic_drift()
        assert drift["new_count"] == 1  # m3
        assert drift["lost_count"] == 1  # m2
        assert drift["changed_count"] == 1  # m1 label changed

    def test_semantic_churn_uses_mapping_counts(self):
        a = make_bundle(mappings={})
        b = make_bundle(mappings={"m1": {}, "m2": {}})
        analyzer = DriftAnalyzer(a, b)

        churn = analyzer.compute_semantic_churn_score()
        assert 0.0 < churn <= 1.0


# =============================================================== Metrics


class TestCodebaseMetricsReport:
    """Exercise CodebaseMetrics edge cases + format_report / to_dict."""

    def test_complexity_score_empty_graph(self):
        metrics = CodebaseMetrics({"nodes": [], "edges": []}, {}, {})
        assert metrics.complexity_score() == 0.0

    def test_complexity_score_single_node(self):
        metrics = CodebaseMetrics(
            {"nodes": [{"id": "n1"}], "edges": []},
            {},
            {},
        )
        # max_edges = 1*0/2 = 0 → early return 0.0
        assert metrics.complexity_score() == 0.0

    def test_complexity_score_many_nodes(self):
        nodes = [{"id": f"n{i}"} for i in range(10)]
        edges = [{"source": f"n{i}", "target": f"n{i + 1}", "kind": "CALLS"} for i in range(9)]
        metrics = CodebaseMetrics({"nodes": nodes, "edges": edges}, {}, {})
        score = metrics.complexity_score()
        assert 0.0 < score < 1.0

    def test_coupling_score_no_edges(self):
        metrics = CodebaseMetrics(
            {"nodes": [{"id": "n1"}, {"id": "n2"}], "edges": []},
            {},
            {},
        )
        assert metrics.coupling_score() == 0.0

    def test_coupling_score_single_module(self):
        """With a single module, coupling is 0."""
        metrics = CodebaseMetrics(
            {
                "nodes": [
                    {"id": "n1", "parent_id": "m1"},
                    {"id": "n2", "parent_id": "m1"},
                ],
                "edges": [{"source": "n1", "target": "n2", "kind": "CALLS"}],
            },
            {},
            {},
        )
        assert metrics.coupling_score() == 0.0

    def test_coupling_score_cross_module(self):
        metrics = CodebaseMetrics(
            {
                "nodes": [
                    {"id": "n1", "parent_id": "m1"},
                    {"id": "n2", "parent_id": "m2"},
                    {"id": "n3", "parent_id": "m2"},
                ],
                "edges": [
                    {"source": "n1", "target": "n2", "kind": "CALLS"},  # cross
                    {"source": "n2", "target": "n3", "kind": "CALLS"},  # intra
                ],
            },
            {},
            {},
        )
        assert metrics.coupling_score() == pytest.approx(0.5)

    def test_coupling_uses_attributes_module_fallback(self):
        metrics = CodebaseMetrics(
            {
                "nodes": [
                    {"id": "n1", "attributes": {"module": "alpha"}},
                    {"id": "n2", "attributes": {"module": "beta"}},
                ],
                "edges": [{"source": "n1", "target": "n2", "kind": "CALLS"}],
            },
            {},
            {},
        )
        assert metrics.coupling_score() == pytest.approx(1.0)

    def test_coupling_skips_edges_missing_endpoints(self):
        metrics = CodebaseMetrics(
            {
                "nodes": [
                    {"id": "n1", "parent_id": "m1"},
                    {"id": "n2", "parent_id": "m2"},
                ],
                "edges": [
                    {"source": "", "target": "n2", "kind": "CALLS"},
                    {"source": "n1", "target": "", "kind": "CALLS"},
                    {"source": "n1", "target": "n2", "kind": "CALLS"},
                ],
            },
            {},
            {},
        )
        # Only one valid cross-module edge out of three, so coupling = 1/3
        assert metrics.coupling_score() == pytest.approx(1 / 3)

    def test_cohesion_score_no_edges(self):
        metrics = CodebaseMetrics(
            {"nodes": [{"id": "n1"}], "edges": []},
            {},
            {},
        )
        assert metrics.cohesion_score() == 0.0

    def test_cohesion_score_intra_module(self):
        metrics = CodebaseMetrics(
            {
                "nodes": [
                    {"id": "n1", "parent_id": "m1"},
                    {"id": "n2", "parent_id": "m1"},
                    {"id": "n3", "parent_id": "m2"},
                ],
                "edges": [
                    {"source": "n1", "target": "n2", "kind": "CALLS"},  # intra
                    {"source": "n1", "target": "n3", "kind": "CALLS"},  # cross
                ],
            },
            {},
            {},
        )
        assert metrics.cohesion_score() == pytest.approx(0.5)

    def test_cohesion_skips_edges_missing_endpoints(self):
        metrics = CodebaseMetrics(
            {
                "nodes": [
                    {"id": "n1", "parent_id": "m1"},
                    {"id": "n2", "parent_id": "m1"},
                ],
                "edges": [
                    {"source": None, "target": "n2", "kind": "CALLS"},
                    {"source": "n1", "target": "n2", "kind": "CALLS"},
                ],
            },
            {},
            {},
        )
        assert metrics.cohesion_score() == pytest.approx(0.5)

    def test_semantic_coverage_empty_graph_is_covered(self):
        metrics = CodebaseMetrics({}, {}, {})
        assert metrics.semantic_coverage() == 1.0

    def test_semantic_coverage_partial(self):
        metrics = CodebaseMetrics(
            {
                "nodes": [{"id": "n1"}, {"id": "n2"}, {"id": "n3"}],
                "edges": [],
            },
            {},
            {"n1": {}, "n2": {}},
        )
        assert metrics.semantic_coverage() == pytest.approx(2 / 3)

    def test_observability_no_state_vars(self):
        metrics = CodebaseMetrics({}, {}, {})
        assert metrics.observability_score() == 1.0

    def test_observability_partial(self):
        metrics = CodebaseMetrics(
            {},
            {
                "states": [{"var_id": "v1"}, {"var_id": "v2"}],
                "observations": [{"modality_id": "o1", "observes_state_vars": ["v1"]}],
                "actions": [],
            },
            {},
        )
        assert metrics.observability_score() == pytest.approx(0.5)

    def test_controllability_no_state_vars(self):
        metrics = CodebaseMetrics({}, {}, {})
        assert metrics.controllability_score() == 1.0

    def test_controllability_partial(self):
        metrics = CodebaseMetrics(
            {},
            {
                "states": [{"var_id": "v1"}, {"var_id": "v2"}],
                "observations": [],
                "actions": [{"action_id": "a1", "affects_state_vars": ["v2"]}],
            },
            {},
        )
        assert metrics.controllability_score() == pytest.approx(0.5)

    def test_summary_returns_metrics_report(self):
        metrics = CodebaseMetrics(
            {
                "nodes": [{"id": "n1"}, {"id": "n2"}],
                "edges": [{"source": "n1", "target": "n2", "kind": "CALLS"}],
            },
            {
                "states": [{"var_id": "v1"}],
                "observations": [],
                "actions": [],
            },
            {},
        )
        report = metrics.summary()
        assert isinstance(report, MetricsReport)
        assert report.node_count == 2
        assert report.edge_count == 1
        assert report.state_var_count == 1

    def test_format_report_has_sections(self):
        metrics = CodebaseMetrics(
            {
                "nodes": [
                    {"id": "n1", "parent_id": "m1"},
                    {"id": "n2", "parent_id": "m1"},
                    {"id": "n3", "parent_id": "m2"},
                ],
                "edges": [
                    {"source": "n1", "target": "n2", "kind": "CALLS"},
                    {"source": "n2", "target": "n3", "kind": "CALLS"},
                ],
            },
            {
                "states": [{"var_id": "v1"}],
                "observations": [{"modality_id": "o1", "observes_state_vars": ["v1"]}],
                "actions": [{"action_id": "a1", "affects_state_vars": ["v1"]}],
            },
            {"n1": {}},
        )
        report = metrics.format_report()

        # Structural / section headers
        assert "# Codebase Metrics Report" in report
        assert "## Architectural Metrics" in report
        assert "## Coverage Metrics" in report
        assert "## Graph Structure" in report
        assert "## State Space Structure" in report

        # Named metrics
        assert "Complexity Score" in report
        assert "Coupling Score" in report
        assert "Cohesion Score" in report
        assert "Semantic Coverage" in report
        assert "Observability Score" in report
        assert "Controllability Score" in report
        assert "Nodes" in report
        assert "Edges" in report

    def test_format_report_handles_single_node(self):
        """Single-node graph → density guarded against n*(n-1)/2 == 0."""
        metrics = CodebaseMetrics(
            {"nodes": [{"id": "n1"}], "edges": []},
            {"states": [], "observations": [], "actions": []},
            {},
        )
        report = metrics.format_report()
        assert "Density" in report
        # With node_count=1 the density should render as 0.0000
        assert "0.0000" in report

    def test_to_dict_complete(self):
        metrics = CodebaseMetrics(
            {
                "nodes": [{"id": "n1"}, {"id": "n2"}],
                "edges": [{"source": "n1", "target": "n2", "kind": "CALLS"}],
            },
            {
                "states": [{"var_id": "v1"}],
                "observations": [],
                "actions": [],
            },
            {"n1": {}, "n2": {}},
        )
        result = metrics.to_dict()

        assert "complexity_score" in result
        assert "graph_structure" in result
        assert result["graph_structure"]["node_count"] == 2
        assert result["graph_structure"]["edge_count"] == 1
        assert "density" in result["graph_structure"]
        assert result["state_space_structure"]["state_variables"] == 1

    def test_to_dict_single_node_density_is_zero(self):
        """Single node should yield density of 0 (not div-by-zero)."""
        metrics = CodebaseMetrics(
            {"nodes": [{"id": "n1"}], "edges": []},
            {},
            {},
        )
        result = metrics.to_dict()
        assert result["graph_structure"]["density"] == 0
