"""Targeted unit tests for: exercise cogant.viz.dashboard.generator empty-state paths.

These tests drive DashboardGenerator with a real but minimally-populated
graph / state-space / process-model / validation report, plus several
variants to trigger the "no nodes", "no state variables", "no process
model", "no GNN validation", etc. branches that are otherwise uncovered.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import pytest

from cogant import __version__
from cogant.process.extractor import ProcessModel
from cogant.runtime.inference import load_inference_trace, write_inference_trace_artifact
from cogant.schemas.graph import (
    Edge,
    EdgeKind,
    GraphMetadata,
    Node,
    NodeKind,
    ProgramGraph,
)
from cogant.schemas.semantic import MappingKind, SemanticMapping
from cogant.statespace.compiler import StateSpaceModel
from cogant.statespace.temporal import TimeRegime
from cogant.validate.report import ValidationReport
from cogant.viz.dashboard.generator import DashboardGenerator
from cogant.viz.dashboard.inference import render_inference_tab
from tests.gnn_execution_fixture import MODEL, package


def _empty_state_space() -> StateSpaceModel:
    return StateSpaceModel(
        id="ss-empty",
        schema_name="current",
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
        schema_name="current",
        stages={},
        connections={},
    )


def _empty_validation_report() -> ValidationReport:
    return ValidationReport(
        id="vr-empty",
        schema_name="current",
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

    @pytest.mark.parametrize("variation, expected_range", [(1e-16, 0.01), (0.1, 190.0)])
    def test_inference_chart_does_not_magnify_roundoff(
        self, tmp_path: Path, variation: float, expected_range: float
    ) -> None:
        package(tmp_path / "gnn_package")
        write_inference_trace_artifact(tmp_path, steps=2)
        trace = load_inference_trace(tmp_path)
        records = tuple(
            record.model_copy(update={"free_energy": index * variation})
            for index, record in enumerate(trace.trace)
        )
        rendered = render_inference_tab(trace.model_copy(update={"trace": records}))
        heights = [
            float(value) for value in re.findall(r'<circle cx="[^"]+" cy="([^"]+)"', rendered)
        ]
        if variation < 1e-12:
            assert max(heights) - min(heights) < expected_range
            assert "near-constant" in rendered
        else:
            assert max(heights) - min(heights) > expected_range
        assert trace.trace[0].free_energy != records[0].free_energy

    @pytest.mark.parametrize("dimensions", [{"n_states": 6, "n_obs": 3, "n_actions": 18}, {}])
    def test_package_summary_uses_recorded_state_dimensions(
        self, dimensions: dict[str, int]
    ) -> None:
        dg = DashboardGenerator(
            graph=_empty_graph(),
            state_space=_empty_state_space(),
            process_model=_empty_process_model(),
            semantic_mappings={},
            mermaid_diagrams={},
            validation_report=_empty_validation_report(),
            repo_name="x",
            gnn_validation={"valid": True, "dimensions": {"state_space": dimensions}},
        )
        rendered = dg._generate_gnn_package_tab()
        for label, key in (
            ("States", "n_states"),
            ("Observations", "n_obs"),
            ("Actions", "n_actions"),
        ):
            assert f"{label}: {dimensions.get(key, 'Not recorded')}" in rendered
        assert "Variables: 0" not in rendered

    def test_mapping_search_has_visible_label_and_real_mapping_fields(self) -> None:
        dg = DashboardGenerator(
            graph=_empty_graph(),
            state_space=_empty_state_space(),
            process_model=_empty_process_model(),
            semantic_mappings={
                "m1": SemanticMapping(
                    id="m1",
                    kind=MappingKind.ACTION,
                    semantic_label="Filter & act",
                    graph_fragment_node_ids=["one", "two"],
                    confidence_score=0.73,
                )
            },
            mermaid_diagrams={},
            validation_report=_empty_validation_report(),
            repo_name="x",
        )
        rendered = dg._generate_semantic_mappings_tab()
        assert '<label for="mapping-search">Search mappings</label>' in rendered
        assert 'id="mapping-search"' in rendered
        assert "Filter &amp; act" in rendered
        assert "73%" in rendered
        assert "<td>2</td>" in rendered

    def test_inference_table_escapes_labels_and_discloses_display_limits(
        self, tmp_path: Path
    ) -> None:
        package(tmp_path / "gnn_package")
        write_inference_trace_artifact(tmp_path, steps=101)
        trace = load_inference_trace(tmp_path)
        labels = trace.labels.model_copy(update={"states": ("<script>injected</script>", "other")})
        rendered = render_inference_tab(trace.model_copy(update={"labels": labels}))
        assert "<script>injected</script>" not in rendered
        assert "&lt;script&gt;injected&lt;/script&gt;" in rendered
        assert "Showing 100 of 101 recorded observations" in rendered
        assert "Table shows 20 of 101 observations" in rendered
        assert rendered.count("<circle") == 100
        assert rendered.count("<tr>") == 21

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
        assert f"<strong>Version:</strong> {__version__}" in html
        # non-empty graph should NOT emit the "No nodes to display" fragment
        assert "No nodes to display" not in html
        assert "No edges to display" not in html

    def test_load_optional_data_reads_trace_json(self, tmp_path: Path) -> None:
        package(tmp_path / "gnn_package")
        write_inference_trace_artifact(tmp_path, steps=2)
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
        assert dg.trace_data == load_inference_trace(tmp_path)
        rendered = dg._generate_active_inference_tab()
        assert dg.trace_data.source_sha256 in rendered
        assert dg.trace_data.matrices_sha256 in rendered
        assert "model_rollout" in rendered
        assert "empirical adequacy" in rendered
        assert f"{dg.trace_data.trace[0].free_energy:.4f}" in rendered
        assert "<svg" in rendered and "<circle" in rendered

    def test_load_optional_data_reads_trace_from_data_layout(self, tmp_path: Path) -> None:
        package(tmp_path / "gnn_package")
        (tmp_path / "data").mkdir()
        write_inference_trace_artifact(tmp_path, steps=1)
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
        assert dg.trace_data == load_inference_trace(tmp_path)
        assert "<circle" in dg._generate_active_inference_tab()

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

    @pytest.mark.parametrize("mutation", ["json", "source", "posterior", "missing_source"])
    def test_load_optional_data_rejects_corrupt_trace(self, tmp_path: Path, mutation: str) -> None:
        package(tmp_path / "gnn_package")
        trace_path = write_inference_trace_artifact(tmp_path, steps=2)
        source = tmp_path / "gnn_package" / "model.gnn.md"
        if mutation == "json":
            trace_path.write_text("{not: valid json")
        elif mutation == "source":
            source.write_text(MODEL + "\n")
        elif mutation == "missing_source":
            source.rename(source.with_suffix(".preserved"))
        else:
            payload = json.loads(trace_path.read_text())
            payload["trace"][0]["posterior"] = [0.5, 0.5]
            trace_path.write_text(json.dumps(payload))
        with pytest.raises((ValueError, OSError)):
            DashboardGenerator(
                graph=_empty_graph(),
                state_space=_empty_state_space(),
                process_model=_empty_process_model(),
                semantic_mappings={},
                mermaid_diagrams={},
                validation_report=_empty_validation_report(),
                repo_name="x",
                output_dir=tmp_path,
            )

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
        package(tmp_path / "gnn_package")
        write_inference_trace_artifact(tmp_path, steps=1)
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
        assert dg.trace_data == load_inference_trace(tmp_path)
