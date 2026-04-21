"""Tests for the cytoscape.js force-directed HTML export (EXP-6).

No mocks — the tests exercise :mod:`cogant.viz.cytoscape_view` and
:class:`cogant.viz.html_renderer.HTMLSiteRenderer` directly using small
real graph dicts and real :class:`SemanticMapping` instances.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from cogant.schemas.semantic import MappingKind, SemanticMapping
from cogant.viz.cytoscape_view import (
    AI_ROLE_COLORS,
    CYTOSCAPE_CDN,
    DEFAULT_NODE_COLOR,
    MAX_NODE_SIZE,
    MIN_NODE_SIZE,
    build_cytoscape_graph_data,
    build_cytoscape_html,
    render_cytoscape_html,
)
from cogant.viz.html_renderer import HTMLSiteRenderer

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def small_graph() -> dict:
    """A minimal program graph with five nodes and a clear degree ordering."""
    return {
        "nodes": [
            {"id": "n1", "name": "state_module", "kind": "MODULE"},
            {"id": "n2", "name": "observe_input", "kind": "FUNCTION"},
            {"id": "n3", "name": "take_action", "kind": "FUNCTION"},
            {"id": "n4", "name": "policy", "kind": "FUNCTION"},
            {"id": "n5", "name": "constraint_check", "kind": "FUNCTION"},
        ],
        "edges": [
            {"source": "n1", "target": "n2", "kind": "CALLS"},
            {"source": "n1", "target": "n3", "kind": "CALLS"},
            {"source": "n1", "target": "n4", "kind": "CALLS"},
            {"source": "n4", "target": "n5", "kind": "DEPENDS_ON"},
        ],
    }


@pytest.fixture
def semantic_mappings() -> list[SemanticMapping]:
    """Real SemanticMapping instances covering all colour-mapped roles."""
    return [
        SemanticMapping(
            id="m1",
            kind=MappingKind.HIDDEN_STATE,
            graph_fragment_node_ids=["n1"],
            semantic_label="state",
            confidence_score=0.9,
        ),
        SemanticMapping(
            id="m2",
            kind=MappingKind.OBSERVATION,
            graph_fragment_node_ids=["n2"],
            semantic_label="obs",
            confidence_score=0.8,
        ),
        SemanticMapping(
            id="m3",
            kind=MappingKind.ACTION,
            graph_fragment_node_ids=["n3"],
            semantic_label="action",
            confidence_score=0.85,
        ),
        SemanticMapping(
            id="m4",
            kind=MappingKind.POLICY,
            graph_fragment_node_ids=["n4"],
            semantic_label="policy",
            confidence_score=0.75,
        ),
        SemanticMapping(
            id="m5",
            kind=MappingKind.CONSTRAINT,
            graph_fragment_node_ids=["n5"],
            semantic_label="constraint",
            confidence_score=0.7,
        ),
    ]


# ---------------------------------------------------------------------------
# build_cytoscape_graph_data
# ---------------------------------------------------------------------------


def test_build_cytoscape_graph_data_shape(small_graph) -> None:
    data = build_cytoscape_graph_data(small_graph)
    assert set(data.keys()) == {"nodes", "edges"}
    assert len(data["nodes"]) == 5
    assert len(data["edges"]) == 4
    # Each node must carry the enrichment fields.
    for node in data["nodes"]:
        assert {"id", "label", "role", "confidence", "degree", "color", "size"} <= node.keys()


def test_build_cytoscape_graph_data_assigns_role_colours(small_graph, semantic_mappings) -> None:
    data = build_cytoscape_graph_data(small_graph, semantic_mappings)
    nodes_by_id = {n["id"]: n for n in data["nodes"]}
    assert nodes_by_id["n1"]["role"] == "HIDDEN_STATE"
    assert nodes_by_id["n1"]["color"] == AI_ROLE_COLORS["HIDDEN_STATE"]
    assert nodes_by_id["n2"]["role"] == "OBSERVATION"
    assert nodes_by_id["n2"]["color"] == AI_ROLE_COLORS["OBSERVATION"]
    assert nodes_by_id["n3"]["role"] == "ACTION"
    assert nodes_by_id["n3"]["color"] == AI_ROLE_COLORS["ACTION"]
    assert nodes_by_id["n4"]["role"] == "POLICY"
    assert nodes_by_id["n4"]["color"] == AI_ROLE_COLORS["POLICY"]
    assert nodes_by_id["n5"]["role"] == "CONSTRAINT"
    assert nodes_by_id["n5"]["color"] == AI_ROLE_COLORS["CONSTRAINT"]


def test_build_cytoscape_graph_data_unmapped_nodes_use_default(small_graph) -> None:
    data = build_cytoscape_graph_data(small_graph, mappings=None)
    for node in data["nodes"]:
        assert node["role"] == "UNKNOWN"
        assert node["color"] == DEFAULT_NODE_COLOR


def test_build_cytoscape_graph_data_degrees_are_correct(small_graph) -> None:
    data = build_cytoscape_graph_data(small_graph)
    degrees = {n["id"]: n["degree"] for n in data["nodes"]}
    # n1 has 3 outgoing edges; n4 participates in 2 (in + out); others = 1.
    assert degrees["n1"] == 3
    assert degrees["n4"] == 2
    assert degrees["n2"] == 1
    assert degrees["n3"] == 1
    assert degrees["n5"] == 1


def test_build_cytoscape_graph_data_sizes_are_within_bounds(small_graph) -> None:
    data = build_cytoscape_graph_data(small_graph)
    sizes = [n["size"] for n in data["nodes"]]
    assert all(MIN_NODE_SIZE <= s <= MAX_NODE_SIZE for s in sizes)
    # Highest-degree node should be the biggest.
    largest = max(data["nodes"], key=lambda n: n["degree"])
    assert largest["id"] == "n1"
    assert largest["size"] == MAX_NODE_SIZE


def test_build_cytoscape_graph_data_accepts_dict_mapping_form(small_graph) -> None:
    """Graphs where nodes/edges are dict-of-dicts should also work."""
    graph = {
        "nodes": {n["id"]: n for n in small_graph["nodes"]},
        "edges": {f"e{i}": e for i, e in enumerate(small_graph["edges"])},
    }
    data = build_cytoscape_graph_data(graph)
    assert len(data["nodes"]) == 5
    assert len(data["edges"]) == 4


def test_build_cytoscape_graph_data_handles_empty_graph() -> None:
    data = build_cytoscape_graph_data({"nodes": [], "edges": []})
    assert data == {"nodes": [], "edges": []}


# ---------------------------------------------------------------------------
# build_cytoscape_html / render_cytoscape_html
# ---------------------------------------------------------------------------


def test_html_export_contains_cytoscape(small_graph) -> None:
    """The exported HTML must reference cytoscape.js."""
    html = build_cytoscape_html(small_graph)
    assert "cytoscape" in html.lower()
    assert CYTOSCAPE_CDN in html


def test_html_export_references_cose_layout(small_graph) -> None:
    html = build_cytoscape_html(small_graph)
    assert "cose" in html


def test_html_export_graph_data_is_valid_json(small_graph, semantic_mappings) -> None:
    """The embedded <script type='application/json'> blob must parse."""
    html = build_cytoscape_html(small_graph, semantic_mappings)
    match = re.search(
        r'<script id="cogant-graph-data" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    assert match is not None, "graph data script block not found in HTML"
    parsed = json.loads(match.group(1))
    assert "nodes" in parsed and "edges" in parsed
    assert len(parsed["nodes"]) == 5
    assert len(parsed["edges"]) == 4
    # Check role assignment survived the round trip.
    roles = {n["id"]: n["role"] for n in parsed["nodes"]}
    assert roles["n1"] == "HIDDEN_STATE"
    assert roles["n2"] == "OBSERVATION"


def test_html_export_node_colors_by_role(small_graph) -> None:
    """HTML must contain the canonical colours for at least HIDDEN_STATE and OBSERVATION."""
    html = build_cytoscape_html(small_graph)
    assert AI_ROLE_COLORS["HIDDEN_STATE"] in html
    assert AI_ROLE_COLORS["OBSERVATION"] in html
    # Plus the other three roles — they're injected through the JS legend map.
    assert AI_ROLE_COLORS["ACTION"] in html
    assert AI_ROLE_COLORS["POLICY"] in html
    assert AI_ROLE_COLORS["CONSTRAINT"] in html


def test_render_cytoscape_html_writes_file(tmp_path: Path, small_graph) -> None:
    target = tmp_path / "nested" / "force_graph.html"
    returned = render_cytoscape_html(small_graph, target)
    assert returned == target
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "cytoscape" in content.lower()


# ---------------------------------------------------------------------------
# HTMLSiteRenderer integration
# ---------------------------------------------------------------------------


def test_html_site_renderer_emits_force_graph_page(tmp_path: Path, small_graph) -> None:
    bundle = {
        "target": "demo-repo",
        "artifacts": {},
        "errors": [],
        "stage_results": {},
        "program_graph": small_graph,
        "semantic_mappings": [
            {
                "kind": "HIDDEN_STATE",
                "graph_fragment_node_ids": ["n1"],
                "confidence_score": 0.9,
            },
            {
                "kind": "OBSERVATION",
                "graph_fragment_node_ids": ["n2"],
                "confidence_score": 0.8,
            },
        ],
    }
    renderer = HTMLSiteRenderer(bundle)
    renderer.render(str(tmp_path))

    force_page = tmp_path / "graph" / "force_graph.html"
    assert force_page.exists(), "force_graph.html was not written by the site renderer"
    content = force_page.read_text(encoding="utf-8")
    assert "cytoscape" in content.lower()
    assert AI_ROLE_COLORS["HIDDEN_STATE"] in content
    assert AI_ROLE_COLORS["OBSERVATION"] in content

    # The overview index must now link to the force graph page too.
    index_page = tmp_path / "index.html"
    assert "graph/force_graph.html" in index_page.read_text(encoding="utf-8")
