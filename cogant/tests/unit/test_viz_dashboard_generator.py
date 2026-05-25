"""Targeted unit tests for: exercise cogant.viz.dashboard.generator empty-state paths.

These tests drive DashboardGenerator with a real but minimally-populated
graph / state-space / process-model / validation report, plus several
variants to trigger the "no nodes", "no state variables", "no process
model", "no GNN validation", etc. branches that are otherwise uncovered.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from cogant.process.extractor import ProcessModel
from cogant.schemas.graph import (
    Edge,
    EdgeKind,
    GraphMetadata,
    Node,
    NodeKind,
    ProgramGraph,
)
from cogant.statespace.compiler import StateSpaceModel
from cogant.statespace.temporal import TimeRegime
from cogant.validate.report import ValidationReport
from cogant.viz.dashboard.generator import DashboardGenerator


def _empty_state_space() -> StateSpaceModel:
    return StateSpaceModel(
        id="ss-empty",
        schema_name="v0.1.0",
        variables={},
        observations={},
        actions={},
        transitions={},
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


def _empty_process_model() -> ProcessModel:
    return ProcessModel(
        id="pm-empty",
        schema_name="v0.1.0",
        stages={},
        connections={},
    )


def _empty_validation_report() -> ValidationReport:
    return ValidationReport(
        id="vr-empty",
        schema_name="v0.1.0",
        validated_at=datetime.now(),
        model_id="m-empty",
        issues=[],
        is_valid=True,
        coverage_score=0.0,
        confidence_score=0.0,
        summary="ok",
    )


def _empty_graph() -> ProgramGraph:
    return ProgramGraph(
        metadata=GraphMetadata(repo_uri="test", languages={"python"}),
    )


def _graph_with_content() -> ProgramGraph:
    g = ProgramGraph(
        metadata=GraphMetadata(repo_uri="test", languages={"python"}),
    )
    g.add_node(
        Node(
            id="n:file",
            kind=NodeKind.FILE,
            name="main.py",
            qualified_name="main.py",
            path="main.py",
            language="python",
        )
    )
    g.add_node(
        Node(
            id="n:fn",
            kind=NodeKind.FUNCTION,
            name="main",
            qualified_name="main",
            path="main.py",
            language="python",
        )
    )
    g.add_edge(
        Edge(
            id="e:file->fn",
            source_id="n:file",
            target_id="n:fn",
            kind=EdgeKind.CONTAINS,
        )
    )
    return g


# ---------------------------------------------------------------------------
# Tests that hit empty-state branches
# ---------------------------------------------------------------------------


class TestDashboardGeneratorEmptyState:
    """Exercise every "No X to display" branch in DashboardGenerator."""

    def test_generates_full_html_from_empty_inputs(self) -> None:
        dg = DashboardGenerator(
            graph=_empty_graph(),
            state_space=_empty_state_space(),
            process_model=_empty_process_model(),
            semantic_mappings={},
            mermaid_diagrams={},
            validation_report=_empty_validation_report(),
            repo_name="empty-repo",
        )
        html = dg.generate()
        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html
        assert "COGANT Dashboard" in html
        # Empty-state fragments we expect
        assert "No nodes to display" in html
        assert "No edges to display" in html
        assert "No semantic mappings to display" in html
        assert "No state variables" in html
        assert "No observations" in html
        assert "No actions" in html
        assert "No transitions" in html
        assert "No process model available" in html
        assert "No GNN validation report available" in html
        assert "No semantic mappings available" in html

    def test_generate_node_distribution_chart_empty(self) -> None:
        dg = DashboardGenerator(
            graph=_empty_graph(),
            state_space=_empty_state_space(),
            process_model=_empty_process_model(),
            semantic_mappings={},
            mermaid_diagrams={},
            validation_report=_empty_validation_report(),
            repo_name="x",
        )
        out = dg._generate_node_distribution_chart()
        assert out == "<p>No nodes to display</p>"

    def test_generate_edge_distribution_chart_empty(self) -> None:
        dg = DashboardGenerator(
            graph=_empty_graph(),
            state_space=_empty_state_space(),
            process_model=_empty_process_model(),
            semantic_mappings={},
            mermaid_diagrams={},
            validation_report=_empty_validation_report(),
            repo_name="x",
        )
        out = dg._generate_edge_distribution_chart()
        assert out == "<p>No edges to display</p>"

    def test_generate_state_variables_table_empty(self) -> None:
        dg = DashboardGenerator(
            graph=_empty_graph(),
            state_space=_empty_state_space(),
            process_model=_empty_process_model(),
            semantic_mappings={},
            mermaid_diagrams={},
            validation_report=_empty_validation_report(),
            repo_name="x",
        )
        assert dg._generate_state_variables_table() == "<p>No state variables</p>"
        assert dg._generate_observations_table() == "<p>No observations</p>"
        assert dg._generate_actions_table() == "<p>No actions</p>"
        assert dg._generate_transitions_table() == "<p>No transitions</p>"


class TestDashboardGeneratorPopulated:
    """Exercise the populated / non-empty rendering branches too."""

    def test_generate_chart_with_nodes_and_edges(self) -> None:
        dg = DashboardGenerator(
            graph=_graph_with_content(),
            state_space=_empty_state_space(),
            process_model=_empty_process_model(),
            semantic_mappings={},
            mermaid_diagrams={"graph_nodes": "graph TD\nA-->B"},
            validation_report=_empty_validation_report(),
            repo_name="non-empty",
        )
        node_svg = dg._generate_node_distribution_chart()
        assert "<svg" in node_svg
        edge_svg = dg._generate_edge_distribution_chart()
        assert "<svg" in edge_svg
        html = dg.generate()
        assert "non-empty" in html
        # non-empty graph should NOT emit the "No nodes to display" fragment
        assert "No nodes to display" not in html
        assert "No edges to display" not in html

    def test_load_optional_data_reads_trace_json(self, tmp_path: Path) -> None:
        """When output_dir contains active_inference_trace.json it must be loaded."""
        trace_path = tmp_path / "active_inference_trace.json"
        trace_path.write_text(json.dumps({"steps": [{"t": 0}]}))
        dg = DashboardGenerator(
            graph=_empty_graph(),
            state_space=_empty_state_space(),
            process_model=_empty_process_model(),
            semantic_mappings={},
            mermaid_diagrams={},
            validation_report=_empty_validation_report(),
            repo_name="x",
            output_dir=tmp_path,
        )
        assert dg.trace_data is not None
        assert dg.trace_data["steps"][0]["t"] == 0

    def test_load_optional_data_reads_simulation_trace(self, tmp_path: Path) -> None:
        """Falls back to simulation_trace.json if active_inference_trace.json missing."""
        sim_path = tmp_path / "simulation_trace.json"
        sim_path.write_text(json.dumps({"events": [42]}))
        dg = DashboardGenerator(
            graph=_empty_graph(),
            state_space=_empty_state_space(),
            process_model=_empty_process_model(),
            semantic_mappings={},
            mermaid_diagrams={},
            validation_report=_empty_validation_report(),
            repo_name="x",
            output_dir=tmp_path,
        )
        assert dg.trace_data == {"events": [42]}

    def test_load_optional_data_reads_gnn_validation(self, tmp_path: Path) -> None:
        """GNN validation report JSON gets loaded into gnn_validation field."""
        (tmp_path / "gnn_validation_report.json").write_text(
            json.dumps({"valid": True, "score": 99.0, "errors": [], "warnings": []})
        )
        dg = DashboardGenerator(
            graph=_empty_graph(),
            state_space=_empty_state_space(),
            process_model=_empty_process_model(),
            semantic_mappings={},
            mermaid_diagrams={},
            validation_report=_empty_validation_report(),
            repo_name="x",
            output_dir=tmp_path,
        )
        assert dg.gnn_validation is not None
        assert dg.gnn_validation["valid"] is True
        # Now generate() should render GNN package validation tab (not the empty state)
        html = dg.generate()
        assert "No GNN validation report available" not in html
        assert "Package Status" in html

    def test_load_optional_data_tolerates_broken_trace_json(self, tmp_path: Path) -> None:
        """Corrupt trace JSON must be swallowed (exception path)."""
        (tmp_path / "active_inference_trace.json").write_text("{not: valid json")
        dg = DashboardGenerator(
            graph=_empty_graph(),
            state_space=_empty_state_space(),
            process_model=_empty_process_model(),
            semantic_mappings={},
            mermaid_diagrams={},
            validation_report=_empty_validation_report(),
            repo_name="x",
            output_dir=tmp_path,
        )
        # Graceful: trace_data stays None, no exception raised
        assert dg.trace_data is None

    def test_load_optional_data_tolerates_broken_gnn_validation(self, tmp_path: Path) -> None:
        """Corrupt GNN validation JSON must be swallowed (exception path)."""
        (tmp_path / "gnn_validation_report.json").write_text("not valid json at all")
        dg = DashboardGenerator(
            graph=_empty_graph(),
            state_space=_empty_state_space(),
            process_model=_empty_process_model(),
            semantic_mappings={},
            mermaid_diagrams={},
            validation_report=_empty_validation_report(),
            repo_name="x",
            output_dir=tmp_path,
        )
        assert dg.gnn_validation is None

    def test_output_dir_as_string_is_accepted(self, tmp_path: Path) -> None:
        """String output_dir is coerced to Path in _load_optional_data."""
        (tmp_path / "active_inference_trace.json").write_text("{}")
        dg = DashboardGenerator(
            graph=_empty_graph(),
            state_space=_empty_state_space(),
            process_model=_empty_process_model(),
            semantic_mappings={},
            mermaid_diagrams={},
            validation_report=_empty_validation_report(),
            repo_name="x",
            output_dir=str(tmp_path),
        )
        assert dg.trace_data == {}
