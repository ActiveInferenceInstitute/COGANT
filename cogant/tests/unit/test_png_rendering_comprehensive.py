"""Comprehensive tests for the COGANT PNG rendering pipeline.

Covers every public surface added to ``cogant.viz.png_export``:
* the native Mermaid-to-PNG fallback for every diagram kind COGANT emits,
* SVG→PNG via whichever backend is available on the host,
* ``render_all_mermaid_in_run`` / ``render_all_svg_in_run`` file discovery,
* ``render_state_space_factor_png`` / ``render_process_gantt_png``,
* the one-shot ``render_all_pngs`` orchestrator entrypoint.

These tests intentionally use tiny structures so they stay under a second per
test even on CI runners with matplotlib's first-run font cache.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

_HAS_MATPLOTLIB = importlib.util.find_spec("matplotlib") is not None
_needs_matplotlib = pytest.mark.skipif(
    not _HAS_MATPLOTLIB,
    reason="matplotlib not installed — install cogant[viz] to enable PNG rendering tests",
)

from cogant.viz.png_export import (
    RenderConfig,
    _detect_mermaid_kind,
    _parse_mermaid_class_diagram,
    _parse_mermaid_flowchart,
    _parse_mermaid_gantt,
    _parse_mermaid_sequence,
    _parse_mermaid_state_diagram,
    _split_gnn_markdown,
    render_all_dot_in_run,
    render_all_mermaid_in_run,
    render_all_pngs,
    render_all_svg_in_run,
    render_connections_matrix_png,
    render_gnn_markdown_png,
    render_markov_blanket_png,
    render_mermaid_file_to_png,
    render_mermaid_text_to_png,
    render_process_gantt_png,
    render_state_space_factor_png,
    render_summary_cover_png,
    render_svg_file_to_png,
)

# --------------------------------------------------------------------------- #
# Mermaid kind detection + parsers                                             #
# --------------------------------------------------------------------------- #

class TestMermaidKindDetection:
    def test_detects_flowchart(self) -> None:
        assert _detect_mermaid_kind("flowchart TD\n    A-->B") == "graph"

    def test_detects_graph(self) -> None:
        assert _detect_mermaid_kind("graph LR\n    A-->B") == "graph"

    def test_detects_class_diagram(self) -> None:
        assert _detect_mermaid_kind("classDiagram\n    class Foo") == "class"

    def test_detects_state_diagram(self) -> None:
        assert _detect_mermaid_kind("stateDiagram-v2\n    [*] --> Idle") == "state"

    def test_detects_sequence(self) -> None:
        assert _detect_mermaid_kind("sequenceDiagram\n    Alice->>Bob: Hi") == "sequence"

    def test_detects_gantt(self) -> None:
        assert _detect_mermaid_kind("gantt\n    title X") == "gantt"

    def test_unknown_defaults_to_graph(self) -> None:
        assert _detect_mermaid_kind("random prefix") == "graph"


def _edge_pairs(edges: list[tuple[str, str, str]] | list[tuple[str, str]]) -> set[tuple[str, str]]:
    """Normalise edge tuples to (src, tgt) pairs regardless of arity."""
    pairs: set[tuple[str, str]] = set()
    for e in edges:
        if len(e) >= 2:
            pairs.add((e[0], e[1]))
    return pairs


class TestMermaidFlowchartParser:
    def test_extracts_edges_and_labels(self) -> None:
        text = (
            "graph TD\n"
            "    A[Start] --> B{Decide}\n"
            "    B -->|yes| C[Done]\n"
            "    B -->|no| A\n"
        )
        result = _parse_mermaid_flowchart(text)
        # Flowchart parser returns (nodes, edges, clusters) as 3-tuple.
        nodes, edges, _clusters = result
        node_ids = {nid for nid, _label in nodes}
        assert {"A", "B", "C"}.issubset(node_ids)
        pairs = _edge_pairs(edges)
        assert ("A", "B") in pairs
        assert ("B", "C") in pairs
        # Edge labels from `|...|` must be captured on the right edges.
        label_map = {(s, t): lbl for (s, t, lbl) in edges}
        assert label_map.get(("B", "C")) == "yes"
        assert label_map.get(("B", "A")) == "no"

    def test_ignores_subgraph_keywords(self) -> None:
        text = "graph TD\n    subgraph cluster\n    A --> B\n    end\n"
        nodes, edges, _clusters = _parse_mermaid_flowchart(text)
        pairs = _edge_pairs(edges)
        assert ("A", "B") in pairs
        assert "subgraph" not in {nid for nid, _ in nodes}
        assert "end" not in {nid for nid, _ in nodes}

    def test_ignores_linkstyle_and_stroke_directives(self) -> None:
        text = (
            "graph TD\n"
            "    a376d1875e845c15[Calculator]\n"
            "    30c03bc2cff0e4f8[input_digit]\n"
            "    a376d1875e845c15 --> 30c03bc2cff0e4f8\n"
            "    linkStyle 0 stroke:#CC0000,stroke-width:2px\n"
            "    30c03bc2cff0e4f8 -->|writes| a376d1875e845c15\n"
        )
        nodes, edges, _clusters = _parse_mermaid_flowchart(text)
        ids = {nid for nid, _ in nodes}
        # Hex IDs (digit-starting) must be captured.
        assert "a376d1875e845c15" in ids
        assert "30c03bc2cff0e4f8" in ids
        # linkStyle tokens must NEVER leak as graph nodes.
        for tok in ("CC0000", "stroke", "linkStyle", "pix", "writes", "reads"):
            assert tok not in ids
        label_map = {(s, t): lbl for (s, t, lbl) in edges}
        assert label_map.get(("30c03bc2cff0e4f8", "a376d1875e845c15")) == "writes"

    def test_captures_subgraph_cluster_label(self) -> None:
        text = (
            "graph TD\n"
            "    subgraph pkg_abc123['mypackage']\n"
            "        foo[Foo]\n"
            "    end\n"
        )
        nodes, _edges, clusters = _parse_mermaid_flowchart(text)
        assert "pkg_abc123" in clusters
        # cluster id itself must not appear as a node
        assert "pkg_abc123" not in {nid for nid, _ in nodes}


class TestMermaidClassDiagramParser:
    def test_class_with_fields_and_inheritance(self) -> None:
        text = (
            "classDiagram\n"
            "    class Animal {\n"
            "        +String name\n"
            "    }\n"
            "    class Dog\n"
            "    Animal <|-- Dog\n"
        )
        result = _parse_mermaid_class_diagram(text)
        nodes, edges = result[0], result[1]
        node_ids = {nid for nid, _ in nodes}
        assert {"Animal", "Dog"}.issubset(node_ids)
        pairs = _edge_pairs(edges)
        assert ("Animal", "Dog") in pairs


class TestMermaidStateDiagramParser:
    def test_transitions_and_aliases(self) -> None:
        text = (
            "stateDiagram-v2\n"
            "    s0: Calculator state\n"
            "    [*] --> s0\n"
            "    s0 --> s1: tick\n"
        )
        result = _parse_mermaid_state_diagram(text)
        nodes, edges = result[0], result[1]
        labels = dict(nodes)
        assert labels.get("s0") == "Calculator state"
        pairs = _edge_pairs(edges)
        assert ("s0", "s1") in pairs

    def test_handles_note_blocks(self) -> None:
        text = (
            "stateDiagram-v2\n"
            "    s0: Calculator\n"
            "    note right of s0\n"
            "        This note should be ignored\n"
            "    end note\n"
            "    s0 --> s1\n"
        )
        result = _parse_mermaid_state_diagram(text)
        edges = result[1]
        assert ("s0", "s1") in _edge_pairs(edges)

    def test_drops_malformed_transition(self) -> None:
        text = "stateDiagram-v2\n     --> s1\n"
        # A malformed edge with empty source must not produce spurious nodes.
        result = _parse_mermaid_state_diagram(text)
        edges = result[1]
        assert edges == []


class TestMermaidSequenceParser:
    def test_participants_and_messages(self) -> None:
        text = (
            "sequenceDiagram\n"
            "    participant Alice\n"
            "    participant Bob\n"
            "    Alice->>Bob: hello\n"
            "    Bob-->>Alice: world\n"
        )
        participants, messages = _parse_mermaid_sequence(text)
        assert participants == ["Alice", "Bob"]
        assert messages[0] == ("Alice", "Bob", "hello")
        assert messages[1] == ("Bob", "Alice", "world")


class TestMermaidGanttParser:
    def test_sections_and_durations(self) -> None:
        text = (
            "gantt\n"
            "    title Project\n"
            "    section Plan\n"
            "    design :a1, 3\n"
            "    section Build\n"
            "    code :a2, 4\n"
        )
        tasks = _parse_mermaid_gantt(text)
        assert len(tasks) == 2
        sections = [t[0] for t in tasks]
        assert sections == ["Plan", "Build"]
        # Durations come from numeric hints in the :a,dur segment.
        assert tasks[0][3] >= 1
        assert tasks[1][3] >= 1


# --------------------------------------------------------------------------- #
# Native mermaid-to-PNG renderer for every diagram kind                        #
# --------------------------------------------------------------------------- #

@_needs_matplotlib
class TestRenderMermaidTextToPng:
    def test_graph_render(self, tmp_path: Path) -> None:
        out = tmp_path / "g.png"
        ok = render_mermaid_text_to_png(
            "graph TD\n    A[Start] --> B[End]\n", out, title="graph_test"
        )
        assert ok is True
        assert out.stat().st_size > 1000

    def test_class_render(self, tmp_path: Path) -> None:
        out = tmp_path / "c.png"
        ok = render_mermaid_text_to_png(
            "classDiagram\n    class Animal\n    class Dog\n    Animal <|-- Dog\n", out
        )
        assert ok is True
        assert out.is_file()

    def test_state_render(self, tmp_path: Path) -> None:
        out = tmp_path / "s.png"
        ok = render_mermaid_text_to_png(
            "stateDiagram-v2\n    [*] --> Idle\n    Idle --> Running\n", out
        )
        assert ok is True
        assert out.is_file()

    def test_sequence_render(self, tmp_path: Path) -> None:
        out = tmp_path / "seq.png"
        ok = render_mermaid_text_to_png(
            "sequenceDiagram\n    Alice->>Bob: hi\n    Bob-->>Alice: hey\n",
            out,
            title="seq",
        )
        assert ok is True
        assert out.is_file()

    def test_gantt_render(self, tmp_path: Path) -> None:
        out = tmp_path / "gt.png"
        ok = render_mermaid_text_to_png(
            "gantt\n    section Plan\n    design :a1, 2\n    code :a2, 3\n", out
        )
        assert ok is True
        assert out.is_file()

    def test_empty_text_returns_false(self, tmp_path: Path) -> None:
        ok = render_mermaid_text_to_png("", tmp_path / "empty.png")
        assert ok is False


@_needs_matplotlib
class TestRenderMermaidFileFallback:
    def test_native_fallback_used_when_mmdc_absent(self, tmp_path: Path) -> None:
        src = tmp_path / "sample.mermaid"
        src.write_text("graph TD\n    A --> B\n", encoding="utf-8")
        dst = tmp_path / "sample.png"
        # allow_native_fallback=True is the default; result should succeed
        # even on hosts without mmdc installed because matplotlib is required.
        ok = render_mermaid_file_to_png(src, dst)
        assert ok is True
        assert dst.is_file()

    def test_native_fallback_disabled_returns_false_when_mmdc_missing(
        self, tmp_path: Path
    ) -> None:
        # mmdc is not installed in the test environment, so disabling the
        # fallback must cause a graceful ``False`` return.
        if shutil.which("mmdc"):
            pytest.skip("mmdc is installed; cannot verify fallback-disabled path")
        src = tmp_path / "x.mermaid"
        src.write_text("graph TD\n    A --> B\n", encoding="utf-8")
        dst = tmp_path / "x.png"
        ok = render_mermaid_file_to_png(src, dst, allow_native_fallback=False)
        assert ok is False


@_needs_matplotlib
class TestRenderAllMermaidInRun:
    def test_walks_run_directory(self, tmp_path: Path) -> None:
        (tmp_path / "a.mermaid").write_text("graph TD\n    A --> B\n")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.mermaid").write_text("graph TD\n    C --> D\n")
        (sub / "c.mmd").write_text("graph TD\n    E --> F\n")
        written = render_all_mermaid_in_run(tmp_path)
        stems = {p.stem for p in written}
        assert {"a", "b", "c"}.issubset(stems)
        for p in written:
            assert p.is_file()
            assert p.stat().st_size > 500


# --------------------------------------------------------------------------- #
# SVG → PNG                                                                    #
# --------------------------------------------------------------------------- #

def _importable(module_name: str) -> bool:
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


_HAS_SVG_BACKEND = bool(
    shutil.which("rsvg-convert")
    or shutil.which("inkscape")
    or shutil.which("convert")
    or _importable("cairosvg")
)


class TestSvgRendering:
    @pytest.mark.skipif(
        not (
            _importable("cairosvg")
            or shutil.which("rsvg-convert")
            or shutil.which("inkscape")
            or shutil.which("convert")
        ),
        reason="No SVG rendering backend installed",
    )
    def test_svg_to_png(self, tmp_path: Path) -> None:
        svg = tmp_path / "hello.svg"
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="80">'
            '<rect width="200" height="80" fill="steelblue"/>'
            '<text x="10" y="50" fill="white" font-size="16">hello</text>'
            "</svg>",
            encoding="utf-8",
        )
        png = tmp_path / "hello.png"
        ok = render_svg_file_to_png(svg, png)
        assert ok is True
        assert png.is_file()
        assert png.stat().st_size > 100

    def test_missing_source_returns_false(self, tmp_path: Path) -> None:
        ok = render_svg_file_to_png(tmp_path / "missing.svg", tmp_path / "x.png")
        assert ok is False

    def test_render_all_svg_in_run(self, tmp_path: Path) -> None:
        (tmp_path / "x.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10" fill="red"/></svg>'
        )
        written = render_all_svg_in_run(tmp_path)
        # On hosts with a backend we expect at least one PNG; otherwise zero
        # is also acceptable — the helper must not raise.
        assert isinstance(written, list)
        for p in written:
            assert p.is_file()


# --------------------------------------------------------------------------- #
# State-space factor and process Gantt PNG renderers                           #
# --------------------------------------------------------------------------- #

@_needs_matplotlib
class TestStateSpaceFactorPng:
    def test_renders_factor_graph(self, tmp_path: Path) -> None:
        ss = SimpleNamespace(
            variables={
                "s0": SimpleNamespace(id="s0", name="state_a"),
                "s1": SimpleNamespace(id="s1", name="state_b"),
            },
            observations={"o0": SimpleNamespace(id="o0", name="obs_a")},
            actions={"u0": SimpleNamespace(id="u0", name="act_a")},
        )
        out = tmp_path / "factor.png"
        assert render_state_space_factor_png(ss, out) is True
        assert out.stat().st_size > 1000

    def test_none_state_space_returns_false(self, tmp_path: Path) -> None:
        out = tmp_path / "nope.png"
        assert render_state_space_factor_png(None, out) is False


@_needs_matplotlib
class TestProcessGanttPng:
    def test_renders_gantt(self, tmp_path: Path) -> None:
        pm = SimpleNamespace(
            stages={
                "st0": SimpleNamespace(name="init", start=0, duration=2),
                "st1": SimpleNamespace(name="run", start=2, duration=3),
                "st2": SimpleNamespace(name="finalize", start=5, duration=1),
            }
        )
        out = tmp_path / "gantt.png"
        assert render_process_gantt_png(pm, out) is True
        assert out.stat().st_size > 1000

    def test_empty_stages_returns_false(self, tmp_path: Path) -> None:
        pm = SimpleNamespace(stages={})
        assert render_process_gantt_png(pm, tmp_path / "g.png") is False


# --------------------------------------------------------------------------- #
# One-shot entrypoint: render_all_pngs                                         #
# --------------------------------------------------------------------------- #

@_needs_matplotlib
class TestRenderAllPngs:
    def _write_corpus(self, run: Path) -> None:
        run.mkdir(parents=True, exist_ok=True)
        (run / "program_graph.json").write_text(
            json.dumps(
                {
                    "nodes": {
                        "m1": {"name": "ModA", "kind": "module"},
                        "c1": {"name": "ClassA", "kind": "class"},
                    },
                    "edges": {
                        "e1": {"source": "m1", "target": "c1", "kind": "contains"},
                    },
                }
            )
        )
        (run / "class_diagram.mermaid").write_text(
            "classDiagram\n    class A\n    class B\n    A <|-- B\n"
        )
        (run / "flowchart.mermaid").write_text("graph TD\n    X --> Y\n")
        (run / "shape.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30">'
            '<circle cx="15" cy="15" r="12" fill="green"/></svg>'
        )

    def test_writes_pngs_for_every_artifact(self, tmp_path: Path) -> None:
        run = tmp_path / "run"
        self._write_corpus(run)
        ss = SimpleNamespace(
            variables={"s0": SimpleNamespace(id="s0", name="state")},
            observations={"o0": SimpleNamespace(id="o0", name="obs")},
            actions={"u0": SimpleNamespace(id="u0", name="act")},
        )
        pm = SimpleNamespace(stages={"st0": SimpleNamespace(name="step", start=0, duration=2)})

        result = render_all_pngs(run, state_space=ss, process_model=pm)

        assert result["program_graph"], "program_graph.png missing"
        assert result["mermaid"], "mermaid PNGs missing"
        assert result["state_space"], "state_space_factor.png missing"
        assert result["process"], "process_gantt.png missing"

        # Mermaid siblings must live next to their source files.
        class_png = run / "class_diagram.png"
        flow_png = run / "flowchart.png"
        assert class_png.is_file()
        assert flow_png.is_file()
        assert class_png.stat().st_size > 500
        assert flow_png.stat().st_size > 500

        # Program graph PNG lives at run root.
        assert (run / "program_graph.png").is_file()

    def test_handles_missing_optional_inputs(self, tmp_path: Path) -> None:
        run = tmp_path / "run"
        run.mkdir()
        (run / "program_graph.json").write_text('{"nodes":{},"edges":{}}')
        # No state_space / process_model given; helper must still run.
        result = render_all_pngs(run)
        assert result["state_space"] == []
        assert result["process"] == []

    def test_idempotent_reruns_do_not_raise(self, tmp_path: Path) -> None:
        run = tmp_path / "run"
        self._write_corpus(run)
        render_all_pngs(run)
        # Second call should happily overwrite.
        result = render_all_pngs(run)
        assert sum(len(v) for v in result.values()) >= 1


# --------------------------------------------------------------------------- #
# dot → PNG discovery helper                                                   #
# --------------------------------------------------------------------------- #

@pytest.mark.skipif(not shutil.which("dot"), reason="Graphviz dot not installed")
class TestRenderAllDotInRun:
    def test_renders_every_dot(self, tmp_path: Path) -> None:
        (tmp_path / "a.dot").write_text("digraph G { a -> b; }\n")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.dot").write_text("digraph H { c -> d; }\n")
        written = render_all_dot_in_run(tmp_path)
        stems = {p.stem for p in written}
        assert {"a", "b"}.issubset(stems)


# --------------------------------------------------------------------------- #
# Connections matrix renderer (A/B/C/D quadrants)                              #
# --------------------------------------------------------------------------- #

@_needs_matplotlib
class TestRenderConnectionsMatrixPng:
    def test_renders_quadrants(self, tmp_path: Path) -> None:
        out = tmp_path / "connections.png"
        ss = SimpleNamespace(
            variables=[
                SimpleNamespace(id="s0", name="state0"),
                SimpleNamespace(id="s1", name="state1"),
            ],
            observations=[
                SimpleNamespace(id="o0", name="obs0"),
                SimpleNamespace(id="o1", name="obs1"),
                SimpleNamespace(id="o2", name="obs2"),
            ],
            actions=[SimpleNamespace(id="u0", name="act0")],
        )
        assert render_connections_matrix_png(ss, out) is True
        assert out.is_file()
        assert out.stat().st_size > 2000

    def test_empty_state_space_returns_false(self, tmp_path: Path) -> None:
        out = tmp_path / "empty.png"
        ss = SimpleNamespace(variables=[], observations=[], actions=[])
        # Should either render an informative placeholder or return False — but
        # never raise.
        try:
            render_connections_matrix_png(ss, out)
        except Exception as e:  # noqa: BLE001
            pytest.fail(f"raised on empty state-space: {e}")


# --------------------------------------------------------------------------- #
# Markov blanket renderer                                                      #
# --------------------------------------------------------------------------- #

@_needs_matplotlib
class TestRenderMarkovBlanketPng:
    def test_renders_roles_dict(self, tmp_path: Path) -> None:
        blanket = tmp_path / "markov_blanket.json"
        blanket.write_text(
            json.dumps(
                {
                    "roles": {
                        "n_int1": "internal",
                        "n_sen1": "sensory",
                        "n_act1": "active",
                        "n_ext1": "external",
                    },
                    "edges": [
                        ["n_sen1", "n_int1"],
                        ["n_int1", "n_act1"],
                        ["n_ext1", "n_sen1"],
                    ],
                }
            )
        )
        out = tmp_path / "blanket.png"
        assert render_markov_blanket_png(blanket, out) is True
        assert out.is_file()

    def test_accepts_partition_lists(self, tmp_path: Path) -> None:
        blanket = tmp_path / "markov_blanket.json"
        blanket.write_text(
            json.dumps(
                {
                    "internal_ids": ["i1", "i2"],
                    "sensory_ids": ["s1"],
                    "active_ids": ["a1"],
                    "external_ids": ["e1"],
                    "links": [{"source": "s1", "target": "i1"}],
                }
            )
        )
        out = tmp_path / "blanket2.png"
        assert render_markov_blanket_png(blanket, out) is True

    def test_accepts_grouped_roles_shape(self, tmp_path: Path) -> None:
        # This is the shape COGANT itself emits in gnn_package/markov_blanket.json.
        blanket = tmp_path / "markov_blanket.json"
        blanket.write_text(
            json.dumps(
                {
                    "roles": {
                        "internal": [
                            {"id": "n1", "name": "foo", "kind": "method"},
                            {"id": "n2", "name": "bar", "kind": "method"},
                        ],
                        "sensory": [{"id": "n3", "name": "Calc", "kind": "class"}],
                        "active": [],
                        "external": [{"id": "n4", "name": "logger"}],
                    },
                    "edges": [["n3", "n1"], ["n1", "n2"]],
                }
            )
        )
        out = tmp_path / "blanket_grouped.png"
        assert render_markov_blanket_png(blanket, out) is True
        assert out.is_file()
        assert out.stat().st_size > 2000

    def test_missing_file_returns_false(self, tmp_path: Path) -> None:
        out = tmp_path / "blanket.png"
        assert render_markov_blanket_png(tmp_path / "missing.json", out) is False


# --------------------------------------------------------------------------- #
# GNN markdown → multi-page PNG                                                #
# --------------------------------------------------------------------------- #

@_needs_matplotlib
class TestRenderGnnMarkdownPng:
    def _sample_gnn(self) -> str:
        sections = []
        for i in range(6):
            sections.append(
                f"## Section {i}\n"
                f"This is body of section {i}.\n"
                f"Line two.\n"
                f"Line three.\n"
            )
        return "# Top\nintroductory text\n" + "\n".join(sections)

    def test_splits_sections(self) -> None:
        text = self._sample_gnn()
        pairs = _split_gnn_markdown(text)
        titles = [t for t, _ in pairs]
        # Preamble (content before first `##`) is first, then Section 0..5.
        assert titles[0] == "Preamble"
        assert "Section 0" in titles
        assert "Section 5" in titles
        assert len(pairs) >= 6

    def test_renders_multiple_pages(self, tmp_path: Path) -> None:
        md = tmp_path / "model.gnn.md"
        md.write_text(self._sample_gnn())
        out = tmp_path / "gnn.png"
        pages = render_gnn_markdown_png(md, out, max_sections_per_page=2)
        assert len(pages) >= 3, f"expected ≥3 pages, got {len(pages)}"
        for p in pages:
            assert p.is_file()
            assert p.stat().st_size > 1000

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        assert render_gnn_markdown_png(tmp_path / "nope.md", tmp_path / "x.png") == []


# --------------------------------------------------------------------------- #
# Summary cover renderer                                                       #
# --------------------------------------------------------------------------- #

@_needs_matplotlib
class TestRenderSummaryCoverPng:
    def test_renders_with_minimal_inputs(self, tmp_path: Path) -> None:
        run = tmp_path / "run"
        run.mkdir()
        (run / "program_graph.json").write_text(
            json.dumps({"nodes": {"a": {}, "b": {}}, "edges": {"e": {"source": "a", "target": "b"}}})
        )
        (run / "semantic_mappings.json").write_text(json.dumps({"mappings": [1, 2, 3]}))
        (run / "validation_report.json").write_text(
            json.dumps({"checks": [{"name": "t", "level": "info", "status": "pass"}]})
        )
        out = run / "cover.png"
        assert render_summary_cover_png(run, out) is True
        assert out.is_file()

    def test_renders_with_no_inputs(self, tmp_path: Path) -> None:
        run = tmp_path / "run"
        run.mkdir()
        out = run / "cover.png"
        # No JSON context — still should not crash. May return False but must
        # never raise.
        try:
            render_summary_cover_png(run, out)
        except Exception as e:  # noqa: BLE001
            pytest.fail(f"summary cover raised: {e}")


# --------------------------------------------------------------------------- #
# render_all_pngs auto-discovery + full coverage                               #
# --------------------------------------------------------------------------- #

@_needs_matplotlib
class TestRenderAllPngsAutoDiscovery:
    def test_auto_loads_state_space_and_process_model(self, tmp_path: Path) -> None:
        run = tmp_path / "run"
        (run / "gnn_package").mkdir(parents=True)
        (run / "program_graph.json").write_text(
            json.dumps({"nodes": {"a": {}, "b": {}}, "edges": {"e": {"source": "a", "target": "b"}}})
        )
        (run / "gnn_package" / "state_space.json").write_text(
            json.dumps(
                {
                    "variables": [{"id": "s0", "name": "s0"}],
                    "observations": [{"id": "o0", "name": "o0"}],
                    "actions": [{"id": "u0", "name": "u0"}],
                }
            )
        )
        (run / "gnn_package" / "process_model.json").write_text(
            json.dumps({"stages": [{"id": "stg0", "name": "step"}], "policies": []})
        )
        (run / "markov_blanket.json").write_text(
            json.dumps(
                {
                    "roles": {"a": "internal", "b": "sensory"},
                    "edges": [["b", "a"]],
                }
            )
        )
        (run / "model.gnn.md").write_text("## A\nbody\n## B\nmore\n")

        cfg = RenderConfig(dpi=120, figsize=(14, 10))
        result = render_all_pngs(run, cfg=cfg)

        assert result["program_graph"], "program_graph.png not produced"
        assert result["state_space"], "state_space_factor.png not produced (auto-load failed)"
        assert result["connections"], "connections_matrix.png not produced"
        assert result["process"], "process_gantt.png not produced (auto-load failed)"
        assert result["markov_blanket"], "markov_blanket.png not produced"
        assert result["gnn_markdown"], "model_gnn.png not produced"
        assert result["summary_cover"], "summary_cover.png not produced"
