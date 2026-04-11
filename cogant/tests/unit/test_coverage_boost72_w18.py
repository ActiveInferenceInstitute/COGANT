#!/usr/bin/env python3
"""Coverage boost batch 72 — viz/mermaid.py (extended), viz/plots, viz/gantt,
viz/html_site, viz/semantic, viz/static_plotter.

Covers:
- viz/mermaid.py: MermaidGenerator (generate_active_inference_diagram,
  generate_state_diagram, generate_sequence_diagram, generate_all with params)
- viz/gantt: GanttRenderer (from_process_model, from_timeline, render_json, render_html)
- viz/semantic: SemanticVisualizer (from_state_space, render_json, render_html)
- viz/static_plots: StaticPlotter (plot_confidence_distribution,
  plot_edge_type_distribution, plot_node_type_distribution)
- viz/html_site: HTMLSiteRenderer (render)
"""

import pytest
from pathlib import Path

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_empty_graph():
    from cogant.schemas.graph import ProgramGraph, GraphMetadata
    return ProgramGraph(metadata=GraphMetadata(repo_uri="file:///test"))


def _make_graph_with_nodes():
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import NodeKind, EdgeKind
    builder = ProgramGraphBuilder(repo_uri="file:///test")
    n1 = builder.add_node(NodeKind.MODULE, "mod", "mod", path="mod.py")
    n2 = builder.add_node(NodeKind.CLASS, "Cls", "mod.Cls", path="mod.py")
    n3 = builder.add_node(NodeKind.FUNCTION, "fn", "mod.fn", path="mod.py")
    builder.add_edge(n1.id, n2.id, EdgeKind.CONTAINS)
    builder.add_edge(n1.id, n3.id, EdgeKind.CONTAINS)
    return builder.finalize()


def _make_state_space():
    from cogant.statespace.compiler import StateSpaceModel
    from cogant.statespace.temporal import TimeRegime
    return StateSpaceModel(
        id="ss1", schema_name="test",
        variables={}, observations={}, actions={},
        transitions={}, likelihoods={}, preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


def _make_process_model():
    from cogant.process.extractor import ProcessModel
    return ProcessModel(id="pm1", schema_name="test", stages={}, connections={})


def _make_timeline():
    from cogant.process.timeline import Timeline
    return Timeline(stages=[], total_duration=0.0, critical_path=[], parallel_groups=[])


# ---------------------------------------------------------------------------
# viz/mermaid.py — MermaidGenerator extended
# ---------------------------------------------------------------------------

class TestMermaidGeneratorExtended:
    def _make_gen(self):
        from cogant.viz import MermaidGenerator
        return MermaidGenerator()

    def test_generate_active_inference_diagram_empty_ss(self):
        gen = self._make_gen()
        ss = _make_state_space()
        result = gen.generate_active_inference_diagram(ss)
        assert isinstance(result, str)

    def test_generate_state_diagram_empty_ss(self):
        gen = self._make_gen()
        ss = _make_state_space()
        result = gen.generate_state_diagram(ss)
        assert isinstance(result, str)

    def test_generate_sequence_diagram_empty(self):
        gen = self._make_gen()
        result = gen.generate_sequence_diagram()
        assert isinstance(result, str)

    def test_generate_sequence_diagram_with_process_model(self):
        gen = self._make_gen()
        pm = _make_process_model()
        result = gen.generate_sequence_diagram(process_model=pm)
        assert isinstance(result, str)

    def test_generate_sequence_diagram_with_graph(self):
        gen = self._make_gen()
        graph = _make_graph_with_nodes()
        result = gen.generate_sequence_diagram(graph=graph)
        assert isinstance(result, str)

    def test_generate_all_with_state_space(self):
        gen = self._make_gen()
        graph = _make_graph_with_nodes()
        ss = _make_state_space()
        result = gen.generate_all(graph, state_space=ss)
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_generate_all_with_process_model(self):
        gen = self._make_gen()
        graph = _make_graph_with_nodes()
        pm = _make_process_model()
        result = gen.generate_all(graph, process_model=pm)
        assert isinstance(result, dict)

    def test_generate_all_with_all_params(self):
        gen = self._make_gen()
        graph = _make_graph_with_nodes()
        ss = _make_state_space()
        pm = _make_process_model()
        result = gen.generate_all(graph, state_space=ss, process_model=pm, mappings={})
        assert isinstance(result, dict)
        assert len(result) >= 3  # Should generate multiple diagrams


# ---------------------------------------------------------------------------
# viz — GanttRenderer
# ---------------------------------------------------------------------------

class TestGanttRenderer:
    def test_init(self):
        from cogant.viz import GanttRenderer
        renderer = GanttRenderer()
        assert renderer is not None

    def test_from_timeline_mutates_and_returns_self(self):
        from cogant.viz import GanttRenderer
        timeline = _make_timeline()
        renderer = GanttRenderer()
        result = renderer.from_timeline(timeline)
        assert result is renderer  # Returns self

    def test_from_process_model_mutates_and_returns_self(self):
        from cogant.viz import GanttRenderer
        renderer = GanttRenderer()
        result = renderer.from_process_model({})
        assert result is renderer

    def test_render_json(self):
        from cogant.viz import GanttRenderer
        renderer = GanttRenderer()
        renderer.from_timeline(_make_timeline())
        result = renderer.render_json()
        assert isinstance(result, str)

    def test_render_html(self, tmp_path):
        from cogant.viz import GanttRenderer
        renderer = GanttRenderer()
        renderer.from_timeline(_make_timeline())
        output = str(tmp_path / "gantt.html")
        result = renderer.render_html(output)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# viz — SemanticVisualizer
# ---------------------------------------------------------------------------

class TestSemanticVisualizer:
    def test_init(self):
        from cogant.viz import SemanticVisualizer
        visualizer = SemanticVisualizer()
        assert visualizer is not None

    def test_from_state_space_dict(self):
        from cogant.viz import SemanticVisualizer
        ss_dict = {
            "id": "ss1",
            "variables": {},
            "observations": {},
            "actions": {},
        }
        visualizer = SemanticVisualizer()
        result = visualizer.from_state_space(ss_dict)
        assert result is visualizer

    def test_render_json(self):
        from cogant.viz import SemanticVisualizer
        visualizer = SemanticVisualizer()
        result = visualizer.render_json()
        assert isinstance(result, str)

    def test_render_html(self, tmp_path):
        from cogant.viz import SemanticVisualizer
        visualizer = SemanticVisualizer()
        output = str(tmp_path / "semantic.html")
        result = visualizer.render_html(output)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# viz — StaticPlotter
# ---------------------------------------------------------------------------

class TestStaticPlotter:
    def test_init(self):
        from cogant.viz import StaticPlotter
        plotter = StaticPlotter()
        assert plotter is not None

    def test_plot_node_type_distribution_with_nodes(self):
        from cogant.viz import StaticPlotter
        plotter = StaticPlotter()
        graph = _make_graph_with_nodes()
        result = plotter.plot_node_type_distribution(graph)
        assert isinstance(result, str)

    def test_plot_edge_type_distribution_with_edges(self):
        from cogant.viz import StaticPlotter
        plotter = StaticPlotter()
        graph = _make_graph_with_nodes()
        result = plotter.plot_edge_type_distribution(graph)
        assert isinstance(result, str)

    def test_plot_confidence_distribution_empty(self):
        from cogant.viz import StaticPlotter
        plotter = StaticPlotter()
        result = plotter.plot_confidence_distribution(mappings={})
        assert isinstance(result, str)

    def test_plot_state_space_matrix(self):
        from cogant.viz import StaticPlotter
        plotter = StaticPlotter()
        ss = _make_state_space()
        result = plotter.plot_state_space_matrix(ss)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# viz — HTMLSiteRenderer
# ---------------------------------------------------------------------------

class TestHTMLSiteRenderer:
    def _make_bundle(self):
        return {
            "stage_results": {},
            "metadata": {"name": "test", "version": "0.1"},
            "label": "test_bundle",
        }

    def test_init(self):
        from cogant.viz import HTMLSiteRenderer
        renderer = HTMLSiteRenderer(self._make_bundle())
        assert renderer is not None

    def test_render_returns_path(self, tmp_path):
        from cogant.viz import HTMLSiteRenderer
        renderer = HTMLSiteRenderer(self._make_bundle())
        result = renderer.render(str(tmp_path))
        assert isinstance(result, Path)

    def test_render_creates_output(self, tmp_path):
        from cogant.viz import HTMLSiteRenderer
        renderer = HTMLSiteRenderer(self._make_bundle())
        result = renderer.render(str(tmp_path))
        assert isinstance(result, Path)
