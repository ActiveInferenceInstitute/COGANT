"""Tests for raster export helpers (no mocks; small real graph dicts)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from cogant.viz.png_export import (
    RenderConfig,
    _downsample_graph,
    find_graph_dot,
    program_graph_dict_to_networkx,
    render_connections_matrix_png,
    render_graphviz_dot_to_png,
    render_process_gantt_png,
    render_program_graph_png,
    render_state_space_factor_png,
)


def test_program_graph_dict_to_networkx_list_and_dict() -> None:
    import networkx as nx

    d_list = {
        "nodes": [{"id": "a", "name": "A", "kind": "MODULE"}],
        "edges": [{"source": "a", "target": "a", "kind": "SELF"}],
    }
    g1 = program_graph_dict_to_networkx(d_list)
    assert isinstance(g1, nx.DiGraph)
    assert g1.number_of_nodes() == 1

    d_dict = {
        "nodes": {"x": {"id": "x", "name": "X", "kind": "CLASS"}},
        "edges": {"e1": {"source": "x", "target": "x", "kind": "LOOP"}},
    }
    g2 = program_graph_dict_to_networkx(d_dict)
    assert g2.number_of_edges() >= 1




def test_find_graph_dot_prefers_diagrams_subdir(tmp_path: Path) -> None:
    run = tmp_path / "run"
    (run / "diagrams").mkdir(parents=True)
    (run / "diagrams" / "graph.dot").write_text("digraph G { a -> b }\n", encoding="utf-8")
    (run / "graph.dot").write_text("digraph H { x -> y }\n", encoding="utf-8")
    assert find_graph_dot(run) == run / "diagrams" / "graph.dot"


def test_find_graph_dot_root_fallback(tmp_path: Path) -> None:
    run = tmp_path / "r"
    run.mkdir()
    (run / "graph.dot").write_text("digraph G { a -> b }\n", encoding="utf-8")
    assert find_graph_dot(run) == run / "graph.dot"


def test_render_program_graph_png_empty_graph_returns_false(tmp_path: Path) -> None:
    pg = tmp_path / "empty.json"
    pg.write_text('{"nodes":{},"edges":{}}', encoding="utf-8")
    out = tmp_path / "out.png"
    assert render_program_graph_png(pg, out) is False


def test_render_program_graph_png_writes_file(tmp_path: Path) -> None:
    pg = tmp_path / "program_graph.json"
    pg.write_text(
        json.dumps(
            {
                "nodes": {"n1": {"id": "n1", "name": "main", "kind": "MODULE"}},
                "edges": {},
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out.png"
    assert render_program_graph_png(pg, out) is True
    assert out.is_file()
    assert out.stat().st_size > 100


@pytest.mark.skipif(not shutil.which("dot"), reason="Graphviz dot not installed")
def test_render_graphviz_dot_to_png(tmp_path: Path) -> None:
    dot = tmp_path / "g.dot"
    dot.write_text('digraph G { a -> b [label="x"]; }\n', encoding="utf-8")
    png = tmp_path / "g.png"
    assert render_graphviz_dot_to_png(dot, png) is True
    assert png.is_file()


# --------------------------------------------------------------------------- #
# Large-graph safeguards: downsampling + matrix/Gantt caps                     #
# --------------------------------------------------------------------------- #


def test_downsample_graph_noop_when_under_cap() -> None:
    """Graphs that already fit in the render budget should pass through untouched."""
    nodes = [("n1", "A"), ("n2", "B"), ("n3", "C")]
    edges = [("n1", "n2", "calls"), ("n2", "n3", "calls")]
    sn, se, stats = _downsample_graph(nodes, edges, max_nodes=50, max_edges=100)
    assert len(sn) == 3
    assert len(se) == 2
    assert stats["original_nodes"] == 3 == stats["kept_nodes"]
    assert stats["original_edges"] == 2 == stats["kept_edges"]


def test_downsample_graph_keeps_highest_degree_nodes() -> None:
    """Downsampling must preserve the most-connected nodes, not arbitrary ones."""
    # "hub" is connected to 5 leaves; "island" is isolated. With cap=3 we want
    # hub + 2 highest-degree leaves, and the island to fall out.
    nodes = [
        ("hub", "Hub"),
        ("l1", "L1"),
        ("l2", "L2"),
        ("l3", "L3"),
        ("l4", "L4"),
        ("l5", "L5"),
        ("island", "Island"),
    ]
    edges = [
        ("hub", "l1", "calls"),
        ("hub", "l2", "calls"),
        ("hub", "l3", "calls"),
        ("hub", "l4", "calls"),
        ("hub", "l5", "calls"),
    ]
    sn, se, stats = _downsample_graph(nodes, edges, max_nodes=3, max_edges=100)
    ids = {nid for nid, _ in sn}
    assert "hub" in ids  # highest degree must survive
    assert "island" not in ids  # zero-degree must drop
    assert len(sn) == 3
    # Every retained edge must have both endpoints in the surviving set.
    assert all(s in ids and t in ids for s, t, _ in se)
    assert stats["original_nodes"] == 7
    assert stats["kept_nodes"] == 3


def test_downsample_graph_caps_edge_count() -> None:
    """Edge-count cap must kick in even when nodes already fit."""
    nodes = [(f"n{i}", f"N{i}") for i in range(4)]
    # Densely connect all 4 nodes → 12 directed edges.
    edges = [
        (f"n{i}", f"n{j}", "x") for i in range(4) for j in range(4) if i != j
    ]
    sn, se, stats = _downsample_graph(nodes, edges, max_nodes=4, max_edges=4)
    assert len(sn) == 4
    assert len(se) == 4
    assert stats["kept_edges"] == 4
    assert stats["original_edges"] == 12


# --------------------------------------------------------------------------- #
# State-space factor-graph layer cap                                           #
# --------------------------------------------------------------------------- #


def _make_state_space(n_vars: int, n_obs: int, n_acts: int) -> SimpleNamespace:
    return SimpleNamespace(
        variables=[
            SimpleNamespace(id=f"s{i}", name=f"state_{i}", cardinality=2)
            for i in range(n_vars)
        ],
        observations=[
            SimpleNamespace(id=f"o{i}", name=f"obs_{i}", cardinality=2)
            for i in range(n_obs)
        ],
        actions=[
            SimpleNamespace(id=f"u{i}", name=f"act_{i}", cardinality=2)
            for i in range(n_acts)
        ],
    )


def test_render_state_space_factor_png_handles_tiny(tmp_path: Path) -> None:
    ss = _make_state_space(2, 3, 1)
    out = tmp_path / "ss.png"
    assert render_state_space_factor_png(ss, out, cfg=RenderConfig()) is True
    assert out.stat().st_size > 500


def test_render_state_space_factor_png_handles_huge_layers(tmp_path: Path) -> None:
    """A 200×1200 state space must render in seconds, not hang on 240k edges.

    This is the GNN-self-analysis shape. Without the layer cap the factor
    graph would create ~240,000 likelihood edges and matplotlib would never
    return. With the cap the PNG should come out under a second.
    """
    import time

    ss = _make_state_space(200, 1200, 0)
    out = tmp_path / "ss_big.png"
    t0 = time.perf_counter()
    ok = render_state_space_factor_png(ss, out, cfg=RenderConfig())
    elapsed = time.perf_counter() - t0
    assert ok is True
    assert out.is_file()
    # Without the layer cap the ~240k-edge networkx graph takes >60s to
    # render; with the cap each layer is ~80 nodes and the full render
    # (including mpl import cold-start on first call) completes in ~15s.
    assert elapsed < 25.0, f"render took {elapsed:.2f}s — layer cap not active"


def test_render_connections_matrix_png_handles_huge_matrix(tmp_path: Path) -> None:
    """A 1200×200 A matrix must be capped — previous versions hung on set_xticks."""
    import time

    ss = _make_state_space(200, 1200, 0)
    out = tmp_path / "conn.png"
    t0 = time.perf_counter()
    ok = render_connections_matrix_png(ss, out, cfg=RenderConfig())
    elapsed = time.perf_counter() - t0
    assert ok is True
    assert out.is_file()
    assert elapsed < 10.0, f"connections matrix took {elapsed:.2f}s — tick cap not active"


# --------------------------------------------------------------------------- #
# Process Gantt row cap                                                        #
# --------------------------------------------------------------------------- #


def _make_process_model(n_stages: int) -> SimpleNamespace:
    return SimpleNamespace(
        process_id="test",
        stages=[
            SimpleNamespace(
                id=f"st{i}",
                name=f"stage_{i}",
                type="function",
                predecessors=[],
                successors=[],
                start=i,
                duration=1,
            )
            for i in range(n_stages)
        ],
        policies=[],
        timelines=[],
    )


def test_render_process_gantt_png_handles_huge_process(tmp_path: Path) -> None:
    """A 6800-stage process model must render via row cap, not hit canvas limit."""
    import time

    pm = _make_process_model(6800)
    out = tmp_path / "gantt.png"
    t0 = time.perf_counter()
    ok = render_process_gantt_png(pm, out, cfg=RenderConfig())
    elapsed = time.perf_counter() - t0
    assert ok is True
    assert out.is_file()
    assert elapsed < 20.0, f"Gantt render took {elapsed:.2f}s — row cap not active"


# --------------------------------------------------------------------------- #
# RenderConfig public API                                                      #
# --------------------------------------------------------------------------- #


def test_render_config_has_large_graph_caps() -> None:
    """The RenderConfig surface must expose the render-budget knobs."""
    cfg = RenderConfig()
    assert hasattr(cfg, "max_render_nodes")
    assert hasattr(cfg, "max_render_edges")
    assert hasattr(cfg, "max_sequence_participants")
    assert cfg.max_render_nodes > 0
    assert cfg.max_render_edges >= cfg.max_render_nodes
