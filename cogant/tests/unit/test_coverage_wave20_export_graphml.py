"""Coverage tests for cogant.export.graphml — wave 20.

Targets uncovered branches in GraphMLExporter:
- export_with_metadata (lines 86-124)
- _add_node_with_metadata branches (lines 170-197)
- _add_edge metadata source_file branch (line 212)
- key definitions for semantic case (line 131)
- node path/language branches (line 161)
"""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from cogant.export.graphml import GraphMLExporter
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph

pytestmark = pytest.mark.unit


def _make_simple_graph() -> ProgramGraph:
    """Two-node, one-edge program graph with full metadata."""
    meta = GraphMetadata(repo_uri="file:///tmp/repo")
    meta.languages = {"python"}
    g = ProgramGraph(metadata=meta)
    g.add_node(
        Node(
            id="n1",
            kind=NodeKind.FUNCTION,
            name="run",
            qualified_name="pkg.run",
            path="pkg/file.py",
            language="python",
            source_range={"start": {"line": 7, "column": 0}, "end": {"line": 12, "column": 0}},
        )
    )
    g.add_node(
        Node(
            id="n2",
            kind=NodeKind.FUNCTION,
            name="helper",
            qualified_name="pkg.helper",
            path="pkg/file.py",
            language="python",
        )
    )
    edge = Edge(
        id="e1",
        source_id="n1",
        target_id="n2",
        kind=EdgeKind.CALLS,
        weight=2.5,
        metadata={"source_file": "pkg/file.py"},
    )
    g.add_edge(edge)
    return g


def _make_minimal_graph() -> ProgramGraph:
    """Graph with one minimal node lacking optional path/language."""
    meta = GraphMetadata(repo_uri="file:///tmp/min")
    g = ProgramGraph(metadata=meta)
    g.add_node(
        Node(
            id="m1",
            kind=NodeKind.MODULE,
            name="bare",
            qualified_name="bare",
        )
    )
    return g


# ---------------------------------------------------------------------------
# export() basic XML round-trip
# ---------------------------------------------------------------------------


def test_export_returns_valid_xml_with_nodes_and_edges() -> None:
    """export() emits a parseable GraphML XML doc with nodes/edges."""
    graph = _make_simple_graph()
    exporter = GraphMLExporter(graph)

    xml_str = exporter.export()
    assert xml_str.startswith("<?xml")
    # Must be valid XML
    root = ET.fromstring(xml_str)  # noqa: S314 - trusted local string
    # Locate <graph> element regardless of namespacing
    graph_elem = next(c for c in root if c.tag.endswith("graph"))
    assert graph_elem.get("edgedefault") == "directed"

    # Confirm two nodes and one edge present
    nodes = [c for c in graph_elem if c.tag.endswith("node")]
    edges = [c for c in graph_elem if c.tag.endswith("edge")]
    assert len(nodes) == 2
    assert len(edges) == 1


def test_export_minimal_node_omits_optional_data_keys() -> None:
    """Nodes without path/language do not emit those data keys."""
    graph = _make_minimal_graph()
    exporter = GraphMLExporter(graph)

    xml_str = exporter.export()
    root = ET.fromstring(xml_str)  # noqa: S314
    graph_elem = next(c for c in root if c.tag.endswith("graph"))
    node_elem = next(c for c in graph_elem if c.tag.endswith("node"))
    keys = {d.get("key") for d in node_elem if d.tag.endswith("data")}
    assert "kind" in keys
    assert "qualified_name" in keys
    # Optional attributes absent
    assert "path" not in keys
    assert "language" not in keys


# ---------------------------------------------------------------------------
# export_with_metadata() — semantic annotations
# ---------------------------------------------------------------------------


def test_export_with_metadata_writes_file(tmp_path: Path) -> None:
    """export_with_metadata writes a GraphML file at the given path."""
    graph = _make_simple_graph()
    exporter = GraphMLExporter(graph)

    out = tmp_path / "deep" / "nested" / "graph.graphml"
    mappings = {
        "mappings": {
            "n1": {"role": "controller", "confidence": 0.92},
            "n2": {"role": "helper", "confidence": 0.5},
        }
    }
    written = exporter.export_with_metadata(graph, mappings, str(out))
    assert written == str(out)
    assert out.exists()
    content = out.read_text()
    assert "controller" in content
    assert "0.92" in content


def test_export_with_metadata_handles_missing_mapping(tmp_path: Path) -> None:
    """Nodes without a mapping entry still emit, just without semantic data."""
    graph = _make_simple_graph()
    exporter = GraphMLExporter(graph)

    out = tmp_path / "g.graphml"
    # Only n1 has a mapping; n2 must still appear
    mappings = {"mappings": {"n1": {"role": "actor", "confidence": 0.7}}}
    exporter.export_with_metadata(graph, mappings, str(out))
    text = out.read_text()
    assert text.count("<node") == 2
    assert "actor" in text


def test_export_with_metadata_empty_mappings_dict(tmp_path: Path) -> None:
    """Empty mappings={} (no 'mappings' subkey) still produces output."""
    graph = _make_simple_graph()
    exporter = GraphMLExporter(graph)

    out = tmp_path / "empty.graphml"
    written = exporter.export_with_metadata(graph, {}, str(out))
    assert Path(written).exists()


def test_export_with_metadata_includes_line_number(tmp_path: Path) -> None:
    """Nodes whose source_range carries a start.line emit line_number data."""
    graph = _make_simple_graph()
    exporter = GraphMLExporter(graph)

    out = tmp_path / "lines.graphml"
    exporter.export_with_metadata(graph, {"mappings": {}}, str(out))
    text = out.read_text()
    # n1 has source_range with start.line = 7 (truthy non-empty)
    assert "line_number" in text
    assert ">7<" in text


def test_export_with_metadata_skips_nonzero_falsy_line(tmp_path: Path) -> None:
    """source_range with start.line == 0 is falsy; line_number key not added."""
    meta = GraphMetadata(repo_uri="file:///tmp/repo")
    g = ProgramGraph(metadata=meta)
    g.add_node(
        Node(
            id="zero",
            kind=NodeKind.FUNCTION,
            name="zero_fn",
            qualified_name="zero_fn",
            path="x.py",
            source_range={"start": {"line": 0, "column": 0}},
        )
    )
    out = tmp_path / "zero.graphml"
    GraphMLExporter(g).export_with_metadata(g, {}, str(out))
    # Parse and check no line_number <data> element on the node
    root = ET.fromstring(out.read_text())  # noqa: S314
    graph_elem = next(c for c in root if c.tag.endswith("graph"))
    node_elem = next(c for c in graph_elem if c.tag.endswith("node"))
    data_keys = [d.get("key") for d in node_elem if d.tag.endswith("data")]
    assert "line_number" not in data_keys


def test_export_with_metadata_handles_non_dict_source_range(tmp_path: Path) -> None:
    """A non-dict source_range is ignored gracefully."""
    meta = GraphMetadata(repo_uri="file:///tmp/repo")
    g = ProgramGraph(metadata=meta)
    g.add_node(
        Node(
            id="nd",
            kind=NodeKind.FUNCTION,
            name="nd_fn",
            qualified_name="nd_fn",
            path="x.py",
            source_range={},  # dict, but no "start" key
        )
    )
    out = tmp_path / "nd.graphml"
    written = GraphMLExporter(g).export_with_metadata(g, {}, str(out))
    assert Path(written).exists()


# ---------------------------------------------------------------------------
# _add_edge — source_file metadata branch
# ---------------------------------------------------------------------------


def test_export_emits_source_file_when_present_in_edge_metadata() -> None:
    """Edges with metadata.source_file emit a source_file data element."""
    graph = _make_simple_graph()
    exporter = GraphMLExporter(graph)

    xml_str = exporter.export()
    assert "source_file" in xml_str
    assert "pkg/file.py" in xml_str


def test_export_omits_source_file_when_absent() -> None:
    """Edges without source_file metadata skip the source_file data element."""
    meta = GraphMetadata(repo_uri="file:///tmp/r")
    g = ProgramGraph(metadata=meta)
    g.add_node(Node(id="a", kind=NodeKind.FUNCTION, name="a", qualified_name="a"))
    g.add_node(Node(id="b", kind=NodeKind.FUNCTION, name="b", qualified_name="b"))
    g.add_edge(Edge(id="e", source_id="a", target_id="b", kind=EdgeKind.CALLS))

    xml_str = GraphMLExporter(g).export()
    root = ET.fromstring(xml_str)  # noqa: S314
    graph_elem = next(c for c in root if c.tag.endswith("graph"))
    edge_elem = next(c for c in graph_elem if c.tag.endswith("edge"))
    edge_keys = {d.get("key") for d in edge_elem if d.tag.endswith("data")}
    assert "source_file" not in edge_keys


# ---------------------------------------------------------------------------
# _add_key_definitions branch — with_semantic adds extra keys
# ---------------------------------------------------------------------------


def test_export_with_metadata_declares_semantic_keys(tmp_path: Path) -> None:
    """export_with_metadata declares semantic_role/confidence_score/module_path/line_number key defs."""
    graph = _make_simple_graph()
    exporter = GraphMLExporter(graph)
    out = tmp_path / "k.graphml"
    exporter.export_with_metadata(graph, {"mappings": {}}, str(out))
    text = out.read_text()
    assert 'id="semantic_role"' in text
    assert 'id="confidence_score"' in text
    assert 'id="module_path"' in text
    assert 'id="line_number"' in text


def test_basic_export_omits_semantic_key_definitions() -> None:
    """Plain export() does not declare semantic key definitions."""
    graph = _make_simple_graph()
    xml_str = GraphMLExporter(graph).export()
    assert 'id="semantic_role"' not in xml_str
    assert 'id="confidence_score"' not in xml_str


# ---------------------------------------------------------------------------
# _prettify
# ---------------------------------------------------------------------------


def test_prettify_indents_output() -> None:
    """The export string is multi-line (prettified)."""
    graph = _make_simple_graph()
    xml_str = GraphMLExporter(graph).export()
    # Pretty XML always contains newlines and indentation
    assert "\n" in xml_str
    # Some indentation present
    assert "  " in xml_str
