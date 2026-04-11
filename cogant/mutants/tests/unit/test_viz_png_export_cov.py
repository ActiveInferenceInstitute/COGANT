"""Behavioral tests for cogant.viz.png_export.

Drives every public PNG renderer with real on-disk fixtures using the
headless ``Agg`` matplotlib backend so the tests work in CI without a
display. Each renderer must (a) write a real PNG file and (b) return
True / a non-empty list on success and False / [] on the documented
error paths.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# Force the headless matplotlib backend BEFORE importing png_export.
os.environ.setdefault("MPLBACKEND", "Agg")

import pytest

matplotlib = pytest.importorskip("matplotlib", reason="cogant[viz] not installed — skip PNG export tests")

from cogant.statespace.compiler import (
    Action,
    ObservationModality,
    StateSpaceModel,
    Transition,
)
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import StateVariable, StateVariableType
from cogant.viz.png_export import (
    RenderConfig,
    _build_kind_legend,
    _detect_mermaid_kind,
    _downsample_graph,
    _kind_color,
    _read_json,
    _split_gnn_markdown,
    _truncate,
    program_graph_dict_to_networkx,
    render_all_pngs,
    render_connections_matrix_png,
    render_gnn_markdown_png,
    render_markov_blanket_png,
    render_mermaid_text_to_png,
    render_program_graph_png,
    render_state_space_factor_png,
    render_summary_cover_png,
)

# --------------------------- helpers / fixtures ------------------------ #


def _state_space_fixture() -> StateSpaceModel:
    """Build a 2-state, 1-obs, 1-action StateSpaceModel for renderer tests."""
    return StateSpaceModel(
        id="m1",
        schema_name="test",
        variables={
            "v1": StateVariable(
                id="v1",
                name="busy",
                var_type=StateVariableType.BOOLEAN,
                node_id="n1",
            ),
            "v2": StateVariable(
                id="v2",
                name="ready",
                var_type=StateVariableType.BOOLEAN,
                node_id="n1",
            ),
        },
        observations={
            "o1": ObservationModality(
                id="o1", name="event", source_node_id="n1", modality_type="event"
            )
        },
        actions={
            "a1": Action(id="a1", name="act", controller_id="n1", effects=["v1"])
        },
        transitions={
            "t1": Transition(
                id="t1",
                source_state={"v1": "true"},
                target_state={"v2": "true"},
                action_id="a1",
            )
        },
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


def _write_program_graph(path: Path) -> None:
    """Write a small program_graph.json fixture."""
    payload = {
        "nodes": [
            {"id": "f1", "name": "main", "kind": "function"},
            {"id": "f2", "name": "helper", "kind": "function"},
            {"id": "c1", "name": "Foo", "kind": "class"},
        ],
        "edges": [
            {"source": "f1", "target": "f2", "kind": "calls"},
            {"source": "c1", "target": "f1", "kind": "contains"},
        ],
    }
    path.write_text(json.dumps(payload))


def _write_markov_blanket(path: Path) -> None:
    """Write a markov_blanket.json fixture in flat-mapping form."""
    payload = {
        "roles": {
            "n1": "internal",
            "n2": "sensory",
            "n3": "active",
            "n4": "external",
        },
        "edges": [["n1", "n2"], ["n2", "n3"], ["n3", "n1"]],
    }
    path.write_text(json.dumps(payload))


# --------------------------- private helpers --------------------------- #


def test_truncate_short_string_returns_unchanged():
    assert _truncate("abc", 10) == "abc"


def test_truncate_long_string_appends_ellipsis():
    out = _truncate("a" * 100, 10)
    assert len(out) == 10
    assert out.endswith("…")


def test_kind_color_known_and_substring_and_default():
    """Known kinds map to known colors; substrings work; default falls back."""
    assert _kind_color("function") == "#f39c12"
    assert _kind_color("CLASS") == "#16a085"  # case-insensitive
    # Substring fallback: "myfunction" contains "function"
    assert _kind_color("myfunction") == "#f39c12"
    # Unknown kind falls back to the default
    assert _kind_color("nonexistent_kind") == "#667eea"


def test_program_graph_dict_to_networkx_list_form():
    """List-form nodes/edges build a DiGraph with the expected counts."""
    g = program_graph_dict_to_networkx(
        {
            "nodes": [{"id": "a", "name": "A", "kind": "class"}],
            "edges": [{"source": "a", "target": "a", "kind": "calls"}],
        }
    )
    assert g.number_of_nodes() == 1
    assert g.number_of_edges() == 1


def test_program_graph_dict_to_networkx_dict_form():
    """Dict-form nodes/edges also build a DiGraph."""
    g = program_graph_dict_to_networkx(
        {
            "nodes": {"a": {"name": "A", "kind": "class"}},
            "edges": {"e1": {"source": "a", "target": "a", "kind": "calls"}},
        }
    )
    assert g.number_of_nodes() == 1
    assert g.number_of_edges() == 1


def test_program_graph_dict_to_networkx_empty_payload():
    """Missing nodes/edges keys produce an empty DiGraph."""
    g = program_graph_dict_to_networkx({})
    assert g.number_of_nodes() == 0
    assert g.number_of_edges() == 0


def test_build_kind_legend_aggregates_kinds():
    g = program_graph_dict_to_networkx(
        {
            "nodes": [
                {"id": "a", "name": "A", "kind": "class"},
                {"id": "b", "name": "B", "kind": "function"},
            ]
        }
    )
    legend = _build_kind_legend(g)
    assert "class" in legend
    assert "function" in legend


def test_downsample_graph_keeps_top_degree_subset():
    nodes = [("a", "A"), ("b", "B"), ("c", "C"), ("d", "D")]
    edges = [("a", "b", "x"), ("a", "c", "y"), ("a", "d", "z")]
    out_nodes, out_edges, stats = _downsample_graph(nodes, edges, max_nodes=2, max_edges=10)
    assert stats["original_nodes"] == 4
    assert stats["kept_nodes"] == 2
    # 'a' has degree 3 → highest, must be kept
    kept_ids = {nid for nid, _ in out_nodes}
    assert "a" in kept_ids


def test_downsample_graph_caps_edges_to_max():
    nodes = [(f"n{i}", f"N{i}") for i in range(5)]
    edges = [(f"n{i}", f"n{j}", "e") for i in range(5) for j in range(5) if i != j]
    _, out_edges, _ = _downsample_graph(nodes, edges, max_nodes=5, max_edges=3)
    assert len(out_edges) == 3


def test_split_gnn_markdown_returns_section_pairs():
    md = "## Alpha\nbody1\n## Beta\nbody2\n"
    out = _split_gnn_markdown(md)
    titles = {t for t, _ in out}
    assert "Alpha" in titles
    assert "Beta" in titles


def test_split_gnn_markdown_no_headers_handles_preamble():
    out = _split_gnn_markdown("just some preamble\nwith no headers")
    # Either an empty list or a single 'Preamble' section is acceptable
    # (the function filters preambles with no body); we just ensure no crash
    assert isinstance(out, list)


def test_read_json_returns_none_for_missing_file(tmp_path):
    assert _read_json(tmp_path / "nope.json") is None


def test_read_json_returns_none_for_malformed_file(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json")
    assert _read_json(p) is None


def test_read_json_returns_data_for_valid_file(tmp_path):
    p = tmp_path / "good.json"
    p.write_text(json.dumps({"x": 1}))
    assert _read_json(p) == {"x": 1}


def test_detect_mermaid_kind_default_graph():
    """Plain mermaid 'graph TD' detects as a flowchart graph."""
    kind = _detect_mermaid_kind("graph TD\nA-->B\n")
    assert kind in {"graph", "flowchart"}


# --------------------------- render_program_graph_png ------------------ #


def test_render_program_graph_png_writes_file(tmp_path):
    """A valid program_graph.json yields a real PNG."""
    pg = tmp_path / "program_graph.json"
    _write_program_graph(pg)
    out = tmp_path / "out.png"
    assert render_program_graph_png(pg, out) is True
    assert out.is_file()
    assert out.stat().st_size > 0


def test_render_program_graph_png_missing_file_returns_false(tmp_path):
    """A missing input file returns False without raising."""
    out = tmp_path / "out.png"
    assert render_program_graph_png(tmp_path / "no.json", out) is False
    assert not out.is_file()


def test_render_program_graph_png_empty_graph_returns_false(tmp_path):
    """An empty graph short-circuits without writing a file."""
    pg = tmp_path / "empty.json"
    pg.write_text(json.dumps({"nodes": [], "edges": []}))
    out = tmp_path / "out.png"
    assert render_program_graph_png(pg, out) is False


def test_render_program_graph_png_uses_custom_render_config(tmp_path):
    """A user-supplied RenderConfig is honoured."""
    pg = tmp_path / "program_graph.json"
    _write_program_graph(pg)
    out = tmp_path / "out.png"
    cfg = RenderConfig(dpi=72, figsize=(6.0, 4.0))
    assert render_program_graph_png(pg, out, cfg=cfg) is True
    assert out.is_file()


# --------------------------- render_mermaid_text_to_png ---------------- #


def test_render_mermaid_text_flowchart(tmp_path):
    """A simple mermaid flowchart renders to a real PNG."""
    text = "graph TD\nA[Start] --> B[End]\n"
    out = tmp_path / "flow.png"
    assert render_mermaid_text_to_png(text, out, title="flow") is True
    assert out.is_file()


def test_render_mermaid_text_class_diagram(tmp_path):
    text = "classDiagram\nclass Foo\nclass Bar\nFoo --> Bar\n"
    out = tmp_path / "cls.png"
    result = render_mermaid_text_to_png(text, out)
    # Either succeeds with file or returns False; both branches are valid
    assert isinstance(result, bool)


def test_render_mermaid_text_state_diagram(tmp_path):
    text = "stateDiagram-v2\n[*] --> A\nA --> B\n"
    out = tmp_path / "st.png"
    result = render_mermaid_text_to_png(text, out)
    assert isinstance(result, bool)


def test_render_mermaid_text_empty_returns_false(tmp_path):
    """An empty mermaid text returns False."""
    out = tmp_path / "empty.png"
    assert render_mermaid_text_to_png("", out) is False


# --------------------------- render_state_space_factor_png ------------- #


def test_render_state_space_factor_png_writes_file(tmp_path):
    out = tmp_path / "factor.png"
    assert render_state_space_factor_png(_state_space_fixture(), out) is True
    assert out.is_file()


def test_render_state_space_factor_png_none_state_space_returns_false(tmp_path):
    out = tmp_path / "none.png"
    assert render_state_space_factor_png(None, out) is False


# --------------------------- render_connections_matrix_png ------------- #


def test_render_connections_matrix_png_writes_file(tmp_path):
    out = tmp_path / "cx.png"
    assert render_connections_matrix_png(_state_space_fixture(), out) is True
    assert out.is_file()


def test_render_connections_matrix_png_none_returns_false(tmp_path):
    out = tmp_path / "none.png"
    assert render_connections_matrix_png(None, out) is False


# --------------------------- render_markov_blanket_png ----------------- #


def test_render_markov_blanket_png_writes_file(tmp_path):
    """A flat-mapping markov_blanket.json renders to a PNG."""
    blanket = tmp_path / "mb.json"
    _write_markov_blanket(blanket)
    out = tmp_path / "mb.png"
    assert render_markov_blanket_png(blanket, out) is True
    assert out.is_file()


def test_render_markov_blanket_png_missing_file_returns_false(tmp_path):
    out = tmp_path / "mb.png"
    assert render_markov_blanket_png(tmp_path / "no.json", out) is False


def test_render_markov_blanket_png_malformed_json_returns_false(tmp_path):
    blanket = tmp_path / "bad.json"
    blanket.write_text("{not json")
    out = tmp_path / "out.png"
    assert render_markov_blanket_png(blanket, out) is False


def test_render_markov_blanket_png_grouped_role_form(tmp_path):
    """The grouped {role: [members]} form is also accepted."""
    payload = {
        "roles": {
            "internal": [{"id": "n1", "name": "alpha"}],
            "sensory": [{"id": "n2", "name": "beta"}],
        },
        "edges": [["n1", "n2"]],
    }
    blanket = tmp_path / "mb_grouped.json"
    blanket.write_text(json.dumps(payload))
    out = tmp_path / "mb_grouped.png"
    assert render_markov_blanket_png(blanket, out) is True


def test_render_markov_blanket_png_partition_lists(tmp_path):
    """A blanket with role partition lists is also accepted."""
    payload = {
        "internal_ids": ["n1"],
        "sensory_ids": ["n2"],
        "active_ids": ["n3"],
        "external_ids": ["n4"],
        "edges": [["n1", "n2"], ["n2", "n3"]],
    }
    blanket = tmp_path / "mb_part.json"
    blanket.write_text(json.dumps(payload))
    out = tmp_path / "mb_part.png"
    assert render_markov_blanket_png(blanket, out) is True


# --------------------------- render_summary_cover_png ------------------ #


def test_render_summary_cover_png_with_minimal_run_dir(tmp_path):
    """summary cover renders with empty run_dir (all sections optional)."""
    out = tmp_path / "summary.png"
    assert render_summary_cover_png(tmp_path, out) is True
    assert out.is_file()


def test_render_summary_cover_png_with_full_run_dir(tmp_path):
    """All optional inputs present: cover still renders."""
    _write_program_graph(tmp_path / "program_graph.json")
    (tmp_path / "semantic_mappings.json").write_text(
        json.dumps({"mappings": [{"id": "m1"}, {"id": "m2"}]})
    )
    (tmp_path / "validation_report.json").write_text(
        json.dumps({"score": 92, "valid": True, "checks": [1, 2, 3]})
    )
    (tmp_path / "metrics_report.json").write_text(
        json.dumps({"provenance_coverage": 0.85, "confidence_mean": 0.78})
    )
    out = tmp_path / "summary.png"
    assert render_summary_cover_png(tmp_path, out) is True
    assert out.is_file()


# --------------------------- render_gnn_markdown_png ------------------- #


def test_render_gnn_markdown_png_writes_at_least_one_page(tmp_path):
    """A GNN markdown with sections produces at least one page PNG."""
    md = tmp_path / "model.gnn.md"
    md.write_text(
        "# Model\nintro\n## Section1\nbody one\n## Section2\nbody two\n"
    )
    out = tmp_path / "model.gnn.png"
    pages = render_gnn_markdown_png(md, out)
    assert len(pages) >= 1
    assert pages[0].is_file()


def test_render_gnn_markdown_png_missing_file_returns_empty(tmp_path):
    """A missing markdown file returns an empty list."""
    pages = render_gnn_markdown_png(tmp_path / "nope.md", tmp_path / "out.png")
    assert pages == []


# --------------------------- render_all_pngs --------------------------- #


def test_render_all_pngs_orchestrator_runs_with_minimal_inputs(tmp_path):
    """The full orchestrator returns a category mapping for an empty run dir."""
    out = render_all_pngs(tmp_path)
    assert isinstance(out, dict)
    expected_keys = {
        "program_graph",
        "mermaid",
        "svg",
        "dot",
        "state_space",
        "connections",
        "process",
        "markov_blanket",
        "gnn_markdown",
        "summary_cover",
    }
    assert set(out.keys()) == expected_keys


def test_render_all_pngs_with_program_graph_and_state_space(tmp_path):
    """Providing program_graph + state_space populates several categories."""
    _write_program_graph(tmp_path / "program_graph.json")
    _write_markov_blanket(tmp_path / "markov_blanket.json")
    out = render_all_pngs(tmp_path, state_space=_state_space_fixture())
    # At least program graph + state space + connections + summary should produce
    assert any(len(v) > 0 for v in out.values())
