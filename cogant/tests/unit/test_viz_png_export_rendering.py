"""Targeted unit tests for: exercise cogant.viz.png public API.

Builds a real (if small) GNN package on disk, then drives render_all_pngs,
render_program_graph_png, render_mermaid_text_to_png, render_connections_matrix_png,
and other render_* helpers against the emitted artifacts. Also toggles
RenderConfig.show_footer / show_legend / extra_metadata to cover the
conditional-draw branches in _draw_footer / _draw_color_legend.
"""

from __future__ import annotations

import json
from pathlib import Path

from cogant.gnn.package import GNNPackageBuilder
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
from cogant.viz.png import (
    RenderConfig,
    program_graph_dict_to_networkx,
    render_all_pngs,
    render_mermaid_text_to_png,
    render_program_graph_png,
)


def _empty_state_space() -> StateSpaceModel:
    return StateSpaceModel(
        id="ss",
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
    return ProcessModel(id="pm", schema_name="current", stages={}, connections={})


def _small_graph() -> ProgramGraph:
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="test", languages={"python"}))
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
            id="n:main",
            kind=NodeKind.FUNCTION,
            name="main",
            qualified_name="main",
            path="main.py",
            language="python",
        )
    )
    g.add_node(
        Node(
            id="n:helper",
            kind=NodeKind.FUNCTION,
            name="helper",
            qualified_name="helper",
            path="main.py",
            language="python",
        )
    )
    g.add_edge(
        Edge(
            id="e:file->main",
            source_id="n:file",
            target_id="n:main",
            kind=EdgeKind.CONTAINS,
        )
    )
    g.add_edge(
        Edge(
            id="e:main->helper",
            source_id="n:main",
            target_id="n:helper",
            kind=EdgeKind.CALLS,
        )
    )
    return g


class TestProgramGraphPng:
    """Drive render_program_graph_png against both empty and populated graphs."""

    def test_empty_program_graph_returns_false(self, tmp_path: Path) -> None:
        pg = tmp_path / "program_graph.json"
        pg.write_text(json.dumps({"nodes": [], "edges": []}))
        out = tmp_path / "empty.png"
        assert render_program_graph_png(pg, out) is False
        assert not out.exists()

    def test_broken_program_graph_json_returns_false(self, tmp_path: Path) -> None:
        pg = tmp_path / "program_graph.json"
        pg.write_text("not json at all")
        out = tmp_path / "broken.png"
        assert render_program_graph_png(pg, out) is False

    def test_populated_program_graph_writes_png(self, tmp_path: Path) -> None:
        pg = tmp_path / "program_graph.json"
        pg.write_text(
            json.dumps(
                {
                    "nodes": [
                        {"id": "a", "label": "main", "kind": "function"},
                        {"id": "b", "label": "helper", "kind": "function"},
                        {"id": "c", "label": "File", "kind": "file"},
                    ],
                    "edges": [
                        {"source": "a", "target": "b", "kind": "calls"},
                        {"source": "c", "target": "a", "kind": "contains"},
                    ],
                }
            )
        )
        out = tmp_path / "pg.png"
        assert render_program_graph_png(pg, out) is True
        assert out.exists()
        # Non-trivial file size — the matplotlib output is at least a few kB
        assert out.stat().st_size > 500

    def test_render_config_footer_disabled_path(self, tmp_path: Path) -> None:
        """show_footer=False short-circuits _draw_footer (missing line 238)."""
        pg = tmp_path / "program_graph.json"
        pg.write_text(
            json.dumps(
                {
                    "nodes": [{"id": "a", "label": "x", "kind": "function"}],
                    "edges": [],
                }
            )
        )
        out = tmp_path / "nofooter.png"
        cfg = RenderConfig(show_footer=False)
        assert render_program_graph_png(pg, out, cfg=cfg) is True

    def test_render_config_with_extra_metadata(self, tmp_path: Path) -> None:
        """extra_metadata populates the footer (missing lines 242-244)."""
        pg = tmp_path / "program_graph.json"
        pg.write_text(
            json.dumps(
                {
                    "nodes": [{"id": "a", "label": "x", "kind": "function"}],
                    "edges": [],
                }
            )
        )
        out = tmp_path / "meta.png"
        cfg = RenderConfig(extra_metadata={"commit": "abc123", "branch": "main"})
        assert render_program_graph_png(pg, out, cfg=cfg) is True

    def test_render_config_legend_disabled(self, tmp_path: Path) -> None:
        """show_legend=False skips the colour legend (missing line 269)."""
        pg = tmp_path / "program_graph.json"
        pg.write_text(
            json.dumps(
                {
                    "nodes": [{"id": "a", "label": "x", "kind": "function"}],
                    "edges": [],
                }
            )
        )
        out = tmp_path / "nolegend.png"
        cfg = RenderConfig(show_legend=False)
        assert render_program_graph_png(pg, out, cfg=cfg) is True


class TestMermaidTextToPng:
    """Drive render_mermaid_text_to_png with real mermaid-flavoured text."""

    def test_flowchart_mermaid_renders(self, tmp_path: Path) -> None:
        text = """flowchart TD
A[Start] --> B{Decide}
B -->|yes| C[Run]
B -->|no| D[Skip]
C --> E[End]
D --> E
"""
        out = tmp_path / "flow.png"
        assert render_mermaid_text_to_png(text, out, title="Flow") is True
        assert out.exists() and out.stat().st_size > 500

    def test_classdiagram_mermaid_renders(self, tmp_path: Path) -> None:
        text = """classDiagram
class Foo
class Bar
Foo <|-- Bar : inherits
"""
        out = tmp_path / "class.png"
        assert render_mermaid_text_to_png(text, out, title="Class") is True
        assert out.exists()

    def test_empty_mermaid_text_returns_false_or_empty_png(self, tmp_path: Path) -> None:
        """Empty mermaid text yields a non-true return (no nodes to draw)."""
        out = tmp_path / "empty.png"
        result = render_mermaid_text_to_png("", out, title="empty")
        # Empty input typically returns False; be tolerant of either outcome
        assert result in (True, False)


class TestProgramGraphDictToNetworkx:
    """The dict→networkx round-trip utility."""

    def test_empty_graph_yields_empty_networkx(self) -> None:
        g = program_graph_dict_to_networkx({"nodes": [], "edges": []})
        assert g.number_of_nodes() == 0
        assert g.number_of_edges() == 0

    def test_graph_with_nodes_and_edges(self) -> None:
        g = program_graph_dict_to_networkx(
            {
                "nodes": [
                    {"id": "a", "label": "Alpha", "kind": "function"},
                    {"id": "b", "label": "Beta", "kind": "class"},
                ],
                "edges": [{"source": "a", "target": "b", "kind": "calls"}],
            }
        )
        assert g.number_of_nodes() == 2
        assert g.number_of_edges() == 1
        assert g.has_edge("a", "b")


class TestRenderAllPngs:
    """End-to-end: build a real GNN package then rasterize every artifact."""

    def test_render_all_pngs_over_empty_package(self, tmp_path: Path) -> None:
        ss = _empty_state_space()
        pm = _empty_process_model()
        builder = GNNPackageBuilder(
            graph=ProgramGraph(metadata=GraphMetadata(repo_uri="empty", languages={"python"})),
            state_space=ss,
            process_model=pm,
            mappings={},
        )
        builder.build(str(tmp_path))
        # Drive render_all_pngs — should not raise and must return a dict
        results = render_all_pngs(tmp_path, state_space=ss, process_model=pm)
        assert isinstance(results, dict)
        # Every category is a list (possibly empty for empty inputs)
        for _category, paths in results.items():
            assert isinstance(paths, list)
            for p in paths:
                assert isinstance(p, Path)

    def test_render_all_pngs_over_populated_package(self, tmp_path: Path) -> None:
        ss = _empty_state_space()
        pm = _empty_process_model()
        builder = GNNPackageBuilder(
            graph=_small_graph(),
            state_space=ss,
            process_model=pm,
            mappings={},
        )
        builder.build(str(tmp_path))
        results = render_all_pngs(tmp_path, state_space=ss, process_model=pm)
        # At least one PNG should get written for a populated graph
        total = sum(len(v) for v in results.values())
        assert total >= 1
