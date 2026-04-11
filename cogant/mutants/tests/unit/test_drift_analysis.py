"""Unit tests for DriftAnalyzer module.

Tests drift analysis between two slightly different program graphs,
verifying structural, semantic, and state-space drift computation.
"""

from cogant.scoring.drift import DriftAnalyzer, DriftScore
from cogant.scoring.metrics import CodebaseMetrics


class TestDriftAnalyzer:
    """Test suite for drift analysis."""

    def create_minimal_bundle(self, num_nodes=3, num_edges=2, num_states=2):
        """Create a minimal bundle with graph and state space."""
        nodes = [
            {"id": f"node_{i}", "kind": "function", "attributes": {}}
            for i in range(num_nodes)
        ]
        edges = [
            {"source": f"node_{i}", "target": f"node_{i+1}", "kind": "CALLS"}
            for i in range(min(num_edges, num_nodes - 1))
        ]
        states = [
            {
                "var_id": f"state_{i}",
                "name": f"variable_{i}",
                "kind": "scalar",
            }
            for i in range(num_states)
        ]
        observations = [
            {
                "modality_id": f"obs_{i}",
                "modality": "sensor",
                "observes_state_vars": [f"state_{i}"],
            }
            for i in range(num_states)
        ]
        actions = [
            {
                "action_id": f"action_{i}",
                "action_type": "control",
                "affects_state_vars": [f"state_{i}"],
            }
            for i in range(num_states)
        ]

        return {
            "graph": {
                "nodes": nodes,
                "edges": edges,
            },
            "state_space": {
                "states": states,
                "observations": observations,
                "actions": actions,
                "policies": [],
            },
            "mappings": {
                f"node_{i}": {"kind": "function", "semantic_label": f"func_{i}"}
                for i in range(num_nodes)
            },
        }

    def test_identical_bundles_zero_drift(self):
        """Identical bundles should have zero drift."""
        bundle = self.create_minimal_bundle(num_nodes=3, num_edges=2)

        analyzer = DriftAnalyzer(bundle, bundle)
        drift = analyzer._compute_drift_score()

        assert isinstance(drift, DriftScore)
        assert drift.total_score == 0.0
        assert drift.architectural_score == 0.0
        assert drift.semantic_churn_score == 0.0

    def test_node_added_drift(self):
        """Adding a node should increase architectural drift."""
        bundle_a = self.create_minimal_bundle(num_nodes=3, num_edges=2)
        bundle_b = self.create_minimal_bundle(num_nodes=5, num_edges=3)

        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        drift = analyzer._compute_drift_score()

        assert isinstance(drift, DriftScore)
        assert drift.architectural_score > 0.0
        assert drift.total_score > 0.0

        # Check structural drift details
        struct = drift.details.get("structural_drift", {})
        assert struct.get("nodes_added_count", 0) > 0

    def test_node_removed_drift(self):
        """Removing a node should increase architectural drift."""
        bundle_a = self.create_minimal_bundle(num_nodes=5, num_edges=3)
        bundle_b = self.create_minimal_bundle(num_nodes=3, num_edges=2)

        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        drift = analyzer._compute_drift_score()

        assert isinstance(drift, DriftScore)
        assert drift.architectural_score > 0.0

        struct = drift.details.get("structural_drift", {})
        assert struct.get("nodes_removed_count", 0) > 0

    def test_edge_changed_drift(self):
        """Changing edge count should increase architectural drift."""
        bundle_a = self.create_minimal_bundle(num_nodes=4, num_edges=2)
        bundle_b = self.create_minimal_bundle(num_nodes=4, num_edges=4)

        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        drift = analyzer._compute_drift_score()

        assert drift.architectural_score > 0.0

        struct = drift.details.get("structural_drift", {})
        assert struct.get("edges_added_count", 0) > 0

    def test_semantic_drift_mapping_added(self):
        """Adding semantic mappings should increase semantic churn."""
        bundle_a = self.create_minimal_bundle(num_nodes=2)
        bundle_a["mappings"] = {
            "node_0": {"kind": "function", "semantic_label": "func_0"}
        }

        bundle_b = self.create_minimal_bundle(num_nodes=2)
        bundle_b["mappings"] = {
            "node_0": {"kind": "function", "semantic_label": "func_0"},
            "node_1": {"kind": "function", "semantic_label": "func_1"},
        }

        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        drift = analyzer._compute_drift_score()

        sem = drift.details.get("semantic_drift", {})
        assert sem.get("new_count", 0) > 0

    def test_state_space_drift(self):
        """State space changes should be tracked."""
        bundle_a = self.create_minimal_bundle(num_states=2)
        bundle_b = self.create_minimal_bundle(num_states=4)

        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        drift = analyzer._compute_drift_score()

        ss = drift.details.get("state_space_drift", {})
        assert ss.get("state_vars_added", 0) > 0

    def test_structural_drift_computation(self):
        """Verify structural drift is computed correctly."""
        bundle_a = self.create_minimal_bundle(num_nodes=3, num_edges=2)
        bundle_b = self.create_minimal_bundle(num_nodes=4, num_edges=3)

        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        struct = analyzer.compute_structural_drift()

        assert "nodes_added" in struct
        assert "nodes_removed" in struct
        assert "nodes_changed" in struct
        assert "edges_added_count" in struct
        assert "edges_removed_count" in struct

    def test_semantic_drift_computation(self):
        """Verify semantic drift is computed correctly."""
        bundle_a = self.create_minimal_bundle()
        bundle_b = self.create_minimal_bundle()

        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        sem = analyzer.compute_semantic_drift()

        assert "new_mappings" in sem
        assert "lost_mappings" in sem
        assert "changed_mappings" in sem
        assert "new_count" in sem
        assert "lost_count" in sem
        assert "changed_count" in sem

    def test_state_space_drift_computation(self):
        """Verify state space drift is computed correctly."""
        bundle_a = self.create_minimal_bundle(num_states=2)
        bundle_b = self.create_minimal_bundle(num_states=3)

        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        ss = analyzer.compute_state_space_drift()

        assert "state_vars_added" in ss
        assert "state_vars_removed" in ss
        assert "state_vars_changed" in ss
        assert "observations_added" in ss
        assert "observations_removed" in ss
        assert "actions_added" in ss
        assert "actions_removed" in ss

    def test_diff_report_generation(self):
        """Verify diff report markdown is generated."""
        bundle_a = self.create_minimal_bundle(num_nodes=3)
        bundle_b = self.create_minimal_bundle(num_nodes=4)

        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        report = analyzer.generate_diff_report()

        assert isinstance(report, str)
        assert "Architectural Drift Report" in report
        assert "Structural Changes" in report
        assert "Semantic Changes" in report
        assert "State Space Changes" in report

    def test_diff_mermaid_generation(self):
        """Verify Mermaid diagram is generated."""
        bundle_a = self.create_minimal_bundle(num_nodes=3)
        bundle_b = self.create_minimal_bundle(num_nodes=4)

        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        diagram = analyzer.generate_diff_mermaid()

        assert isinstance(diagram, str)
        assert "graph TD" in diagram
        assert "Drift" in diagram

    def test_to_dict_serialization(self):
        """Verify drift analysis can be serialized to dict."""
        bundle_a = self.create_minimal_bundle()
        bundle_b = self.create_minimal_bundle()

        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        result_dict = analyzer.to_dict()

        assert "total_score" in result_dict
        assert "architectural_score" in result_dict
        assert "semantic_churn_score" in result_dict
        assert "details" in result_dict
        assert isinstance(result_dict["total_score"], float)
        assert 0.0 <= result_dict["total_score"] <= 1.0

    def test_code_change_scenario(self):
        """Simulate a realistic code change scenario."""
        # Baseline: simple 3-function app
        baseline = {
            "graph": {
                "nodes": [
                    {"id": "main", "kind": "function", "attributes": {}},
                    {"id": "auth", "kind": "function", "attributes": {}},
                    {"id": "db", "kind": "function", "attributes": {}},
                ],
                "edges": [
                    {"source": "main", "target": "auth", "kind": "CALLS"},
                    {"source": "auth", "target": "db", "kind": "CALLS"},
                ],
            },
            "state_space": {
                "states": [
                    {"var_id": "user", "name": "current_user", "kind": "scalar"},
                    {"var_id": "session", "name": "session_token", "kind": "scalar"},
                ],
                "observations": [
                    {"modality_id": "obs_user", "modality": "sensor", "observes_state_vars": ["user"]},
                ],
                "actions": [
                    {"action_id": "login", "action_type": "control", "affects_state_vars": ["user"]},
                ],
                "policies": [],
            },
            "mappings": {
                "main": {"kind": "function"},
                "auth": {"kind": "function"},
                "db": {"kind": "function"},
            },
        }

        # Modified: added caching layer and new observation
        modified = {
            "graph": {
                "nodes": [
                    {"id": "main", "kind": "function", "attributes": {}},
                    {"id": "auth", "kind": "function", "attributes": {}},
                    {"id": "cache", "kind": "function", "attributes": {}},
                    {"id": "db", "kind": "function", "attributes": {}},
                ],
                "edges": [
                    {"source": "main", "target": "auth", "kind": "CALLS"},
                    {"source": "auth", "target": "cache", "kind": "CALLS"},
                    {"source": "cache", "target": "db", "kind": "CALLS"},
                ],
            },
            "state_space": {
                "states": [
                    {"var_id": "user", "name": "current_user", "kind": "scalar"},
                    {"var_id": "session", "name": "session_token", "kind": "scalar"},
                    {"var_id": "cache_state", "name": "cache_status", "kind": "scalar"},
                ],
                "observations": [
                    {"modality_id": "obs_user", "modality": "sensor", "observes_state_vars": ["user"]},
                    {"modality_id": "obs_cache", "modality": "sensor", "observes_state_vars": ["cache_state"]},
                ],
                "actions": [
                    {"action_id": "login", "action_type": "control", "affects_state_vars": ["user"]},
                    {"action_id": "invalidate_cache", "action_type": "control", "affects_state_vars": ["cache_state"]},
                ],
                "policies": [],
            },
            "mappings": {
                "main": {"kind": "function"},
                "auth": {"kind": "function"},
                "cache": {"kind": "function"},
                "db": {"kind": "function"},
            },
        }

        analyzer = DriftAnalyzer(baseline, modified)
        drift = analyzer._compute_drift_score()

        # Verify drift was detected
        assert drift.total_score > 0.0
        assert drift.architectural_score > 0.0

        # Verify specific changes
        struct = drift.details.get("structural_drift", {})
        assert struct.get("nodes_added_count", 0) >= 1  # cache node added
        assert struct.get("edges_added_count", 0) >= 1  # new edge

        ss = drift.details.get("state_space_drift", {})
        assert ss.get("state_vars_added", 0) >= 1  # cache_state added
        assert ss.get("observations_added", 0) >= 1  # obs_cache added

    def test_empty_bundle_handling(self):
        """Empty bundles should be handled gracefully."""
        empty = {"graph": {"nodes": [], "edges": []}, "state_space": {}, "mappings": {}}
        bundle = self.create_minimal_bundle()

        analyzer = DriftAnalyzer(empty, bundle)
        drift = analyzer._compute_drift_score()

        assert isinstance(drift, DriftScore)
        # Should detect addition of all nodes
        struct = drift.details.get("structural_drift", {})
        assert struct.get("nodes_added_count", 0) > 0

    def test_drift_score_normalization(self):
        """Drift scores should be normalized to [0, 1]."""
        bundle_a = self.create_minimal_bundle(num_nodes=1)
        bundle_b = self.create_minimal_bundle(num_nodes=100)

        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        drift = analyzer._compute_drift_score()

        assert 0.0 <= drift.total_score <= 1.0
        assert 0.0 <= drift.architectural_score <= 1.0
        assert 0.0 <= drift.semantic_churn_score <= 1.0

    def test_metrics_integration(self):
        """Verify drift analysis works with CodebaseMetrics."""
        bundle_a = self.create_minimal_bundle(num_nodes=3, num_edges=2, num_states=2)
        bundle_b = self.create_minimal_bundle(num_nodes=4, num_edges=3, num_states=3)

        # Compute metrics on both bundles
        metrics_a = CodebaseMetrics(
            bundle_a["graph"],
            bundle_a["state_space"],
            bundle_a["mappings"],
        )
        metrics_b = CodebaseMetrics(
            bundle_b["graph"],
            bundle_b["state_space"],
            bundle_b["mappings"],
        )

        summary_a = metrics_a.summary()
        summary_b = metrics_b.summary()

        # Verify metrics differ
        assert summary_a.node_count != summary_b.node_count
        assert summary_a.state_var_count != summary_b.state_var_count

        # Verify drift analysis also detects changes
        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        drift = analyzer._compute_drift_score()
        assert drift.total_score > 0.0


class TestMetricsIntegration:
    """Test metrics computation with drift analysis."""

    def create_test_bundle(self):
        """Create a test bundle for metrics testing."""
        nodes = [
            {"id": f"func_{i}", "kind": "function", "parent_id": "module_0", "attributes": {}}
            for i in range(5)
        ]
        nodes.extend([
            {"id": f"class_{i}", "kind": "class", "parent_id": "module_1", "attributes": {}}
            for i in range(3)
        ])

        # Create edges to test coupling and cohesion
        edges = [
            # Within-module edges
            {"source": "func_0", "target": "func_1", "kind": "CALLS"},
            {"source": "func_1", "target": "func_2", "kind": "CALLS"},
            {"source": "class_0", "target": "class_1", "kind": "CALLS"},
            # Cross-module edges
            {"source": "func_2", "target": "class_0", "kind": "CALLS"},
            {"source": "func_3", "target": "class_1", "kind": "CALLS"},
        ]

        return {
            "graph": {"nodes": nodes, "edges": edges},
            "state_space": {
                "states": [
                    {"var_id": f"state_{i}", "name": f"var_{i}", "kind": "scalar"}
                    for i in range(3)
                ],
                "observations": [
                    {
                        "modality_id": f"obs_{i}",
                        "modality": "sensor",
                        "observes_state_vars": [f"state_{i}"],
                    }
                    for i in range(3)
                ],
                "actions": [
                    {
                        "action_id": f"action_{i}",
                        "action_type": "control",
                        "affects_state_vars": [f"state_{i}"],
                    }
                    for i in range(3)
                ],
                "policies": [],
            },
            "mappings": {
                f"func_{i}": {"kind": "function"} for i in range(5)
            },
        }

    def test_complexity_score_range(self):
        """Complexity score should be in [0, 1]."""
        bundle = self.create_test_bundle()
        metrics = CodebaseMetrics(
            bundle["graph"],
            bundle["state_space"],
            bundle["mappings"],
        )

        score = metrics.complexity_score()
        assert 0.0 <= score <= 1.0

    def test_coupling_score_range(self):
        """Coupling score should be in [0, 1]."""
        bundle = self.create_test_bundle()
        metrics = CodebaseMetrics(
            bundle["graph"],
            bundle["state_space"],
            bundle["mappings"],
        )

        score = metrics.coupling_score()
        assert 0.0 <= score <= 1.0

    def test_cohesion_score_range(self):
        """Cohesion score should be in [0, 1]."""
        bundle = self.create_test_bundle()
        metrics = CodebaseMetrics(
            bundle["graph"],
            bundle["state_space"],
            bundle["mappings"],
        )

        score = metrics.cohesion_score()
        assert 0.0 <= score <= 1.0

    def test_metrics_to_dict(self):
        """Metrics should serialize to dict correctly."""
        bundle = self.create_test_bundle()
        metrics = CodebaseMetrics(
            bundle["graph"],
            bundle["state_space"],
            bundle["mappings"],
        )

        result_dict = metrics.to_dict()

        assert "complexity_score" in result_dict
        assert "coupling_score" in result_dict
        assert "cohesion_score" in result_dict
        assert "semantic_coverage" in result_dict
        assert "observability_score" in result_dict
        assert "controllability_score" in result_dict
        assert "graph_structure" in result_dict
        assert "state_space_structure" in result_dict
