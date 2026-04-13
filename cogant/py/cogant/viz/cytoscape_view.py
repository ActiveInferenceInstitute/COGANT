"""Cytoscape.js force-directed graph view for the COGANT HTML export.

Emits a single self-contained HTML page (CDN-loaded ``cytoscape.min.js``, no
npm required) that renders a program graph using the ``cose`` force-directed
layout. Nodes are colour-coded by their COGANT AI role (from semantic
mappings) and sized by degree (number of incident edges).

Public entry points
-------------------
- :func:`build_cytoscape_graph_data` — pure function that turns a program
  graph dict + optional semantic mappings into the ``{nodes, edges}`` payload
  consumed by ``cytoscape()``.
- :func:`render_cytoscape_html` — writes a full HTML page to disk.
- :func:`build_cytoscape_html` — returns the full HTML page as a string
  (no I/O; used by :mod:`cogant.viz.html_renderer`).

The ``AI_ROLE_COLORS`` mapping is intentionally exported so downstream tests
and callers can assert or reuse the canonical role -> colour assignment.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Canonical role -> colour mapping used by the cytoscape view.
#
# Keys match ``cogant.schemas.semantic.MappingKind`` enum *names* (upper case)
# so that arbitrary ``MappingKind`` values can be looked up via ``.name``.
# Anything not in the map falls back to ``DEFAULT_NODE_COLOR``.
# ---------------------------------------------------------------------------
AI_ROLE_COLORS: dict[str, str] = {
    "HIDDEN_STATE": "#9b59b6",  # purple
    "OBSERVATION": "#3498db",   # blue
    "ACTION": "#e67e22",        # orange
    "POLICY": "#2ecc71",        # green
    "CONSTRAINT": "#e74c3c",    # red
}

DEFAULT_NODE_COLOR: str = "#95a5a6"
"""Neutral grey used for nodes without a semantic mapping."""

MIN_NODE_SIZE: int = 20
"""Minimum cytoscape node diameter (px) -- used when degree = 0."""

MAX_NODE_SIZE: int = 60
"""Maximum cytoscape node diameter (px) -- used for the highest-degree node."""

CYTOSCAPE_CDN: str = (
    "https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js"
)
"""CDN URL for cytoscape.js. Pinned to a specific version for reproducibility."""


# ---------------------------------------------------------------------------
# Data shaping
# ---------------------------------------------------------------------------


def _node_list(graph: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return the node collection of ``graph`` as a list regardless of shape."""
    raw = graph.get("nodes", [])
    if isinstance(raw, Mapping):
        return list(raw.values())
    return list(raw)


def _edge_list(graph: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return the edge collection of ``graph`` as a list regardless of shape."""
    raw = graph.get("edges", [])
    if isinstance(raw, Mapping):
        return list(raw.values())
    return list(raw)


def _build_role_index(
    mappings: Iterable[Any] | None,
) -> dict[str, dict[str, Any]]:
    """Index semantic mappings by node id.

    ``mappings`` is expected to contain objects with ``kind`` and
    ``graph_fragment_node_ids`` fields (either a :class:`SemanticMapping`
    dataclass or an equivalent dict). When a node appears in several
    mappings, the mapping with the highest ``confidence_score`` wins so
    the colouring is stable and deterministic.
    """
    index: dict[str, dict[str, Any]] = {}
    if not mappings:
        return index

    for mapping in mappings:
        if hasattr(mapping, "kind") and not isinstance(mapping, Mapping):
            kind = mapping.kind
            node_ids = getattr(mapping, "graph_fragment_node_ids", []) or []
            confidence = float(getattr(mapping, "confidence_score", 0.0) or 0.0)
        else:
            kind = mapping.get("kind")
            node_ids = mapping.get("graph_fragment_node_ids", []) or []
            confidence = float(mapping.get("confidence_score", 0.0) or 0.0)

        if hasattr(kind, "name"):
            role = kind.name
        elif isinstance(kind, str):
            role = kind.upper()
        else:
            role = "UNKNOWN"

        for node_id in node_ids:
            existing = index.get(node_id)
            if existing is None or confidence >= existing.get("confidence", 0.0):
                index[node_id] = {"role": role, "confidence": confidence}

    return index


def _compute_degrees(edges: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    """Count the number of incident edges per node id (undirected)."""
    degree: dict[str, int] = {}
    for edge in edges:
        source = edge.get("source") or edge.get("source_id")
        target = edge.get("target") or edge.get("target_id")
        if source:
            degree[source] = degree.get(source, 0) + 1
        if target:
            degree[target] = degree.get(target, 0) + 1
    return degree


def _scale_degree_to_size(degree: int, max_degree: int) -> int:
    """Linearly scale ``degree`` to a pixel size in [MIN_NODE_SIZE, MAX_NODE_SIZE]."""
    if max_degree <= 0:
        return MIN_NODE_SIZE
    ratio = min(1.0, degree / max_degree)
    return int(round(MIN_NODE_SIZE + ratio * (MAX_NODE_SIZE - MIN_NODE_SIZE)))


def build_cytoscape_graph_data(
    graph: Mapping[str, Any],
    mappings: Iterable[Any] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Transform a program graph + semantic mappings into cytoscape payload.

    The returned dict has two keys:

    ``nodes``
        List of ``{id, label, role, confidence, degree, color, size}`` dicts.

    ``edges``
        List of ``{source, target, kind}`` dicts.

    The output is directly JSON-serialisable.
    """
    nodes_raw = _node_list(graph)
    edges_raw = _edge_list(graph)

    role_index = _build_role_index(mappings)
    degree_index = _compute_degrees(edges_raw)
    max_degree = max(degree_index.values(), default=0)

    nodes_out: list[dict[str, Any]] = []
    for node in nodes_raw:
        node_id = str(node.get("id") or node.get("qualified_name") or "")
        if not node_id:
            continue
        label = node.get("name") or node.get("label") or node_id
        role_info = role_index.get(node_id) or {}
        role = role_info.get("role", "UNKNOWN")
        confidence = float(role_info.get("confidence", 0.0) or 0.0)
        degree = int(degree_index.get(node_id, 0))
        color = AI_ROLE_COLORS.get(role, DEFAULT_NODE_COLOR)
        size = _scale_degree_to_size(degree, max_degree)

        nodes_out.append(
            {
                "id": node_id,
                "label": str(label),
                "role": role,
                "confidence": round(confidence, 4),
                "degree": degree,
                "color": color,
                "size": size,
            }
        )

    edges_out: list[dict[str, Any]] = []
    for edge in edges_raw:
        source = edge.get("source") or edge.get("source_id")
        target = edge.get("target") or edge.get("target_id")
        if not source or not target:
            continue
        kind = edge.get("kind") or edge.get("type") or edge.get("label") or "UNKNOWN"
        if hasattr(kind, "name"):
            kind_str = kind.name
        else:
            kind_str = str(kind).upper()
        edges_out.append(
            {
                "source": str(source),
                "target": str(target),
                "kind": kind_str,
            }
        )

    return {"nodes": nodes_out, "edges": edges_out}


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------


_CYTOSCAPE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>COGANT - Force-Directed Program Graph</title>
    <script src="__CYTOSCAPE_CDN__"></script>
    <style>
        body {
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f5f5f5;
            color: #222;
        }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 24px;
        }
        header h1 { margin: 0; font-size: 1.4rem; }
        header p  { margin: 4px 0 0 0; opacity: 0.85; font-size: 0.9rem; }
        #layout {
            display: grid;
            grid-template-columns: 1fr 280px;
            gap: 12px;
            padding: 12px;
            height: calc(100vh - 80px);
            box-sizing: border-box;
        }
        #cy {
            width: 100%;
            height: 100%;
            background: white;
            border: 1px solid #ddd;
            border-radius: 6px;
        }
        aside {
            background: white;
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 16px;
            overflow-y: auto;
        }
        aside h2 { font-size: 1rem; margin: 0 0 12px; color: #4a4a4a; }
        aside dl { margin: 0; }
        aside dt { font-weight: 600; font-size: 0.8rem; color: #666; }
        aside dd { margin: 0 0 10px 0; font-size: 0.9rem; word-break: break-word; }
        .legend { margin-top: 18px; border-top: 1px solid #eee; padding-top: 12px; }
        .legend h3 { margin: 0 0 8px; font-size: 0.85rem; color: #4a4a4a; }
        .legend ul { list-style: none; padding: 0; margin: 0; }
        .legend li { display: flex; align-items: center; margin-bottom: 4px; font-size: 0.8rem; }
        .legend .swatch {
            width: 12px; height: 12px; border-radius: 50%;
            margin-right: 8px; border: 1px solid #555;
        }
    </style>
</head>
<body>
    <header>
        <h1>COGANT Force-Directed Program Graph</h1>
        <p>Cytoscape.js (cose) layout - node size = degree - colour = AI role</p>
    </header>
    <div id="layout">
        <div id="cy"></div>
        <aside>
            <h2>Node details</h2>
            <dl id="details">
                <dt>Name</dt><dd id="d-name">Click a node...</dd>
                <dt>AI role</dt><dd id="d-role">-</dd>
                <dt>Confidence</dt><dd id="d-conf">-</dd>
                <dt>Edges</dt><dd id="d-deg">-</dd>
            </dl>
            <div class="legend">
                <h3>AI role legend</h3>
                <ul id="legend-items"></ul>
            </div>
        </aside>
    </div>
    <script id="cogant-graph-data" type="application/json">__GRAPH_JSON__</script>
    <script>
    (function () {
        var raw = document.getElementById('cogant-graph-data').textContent;
        var data = JSON.parse(raw);
        var AI_ROLE_COLORS = __AI_ROLE_COLORS__;
        var DEFAULT_COLOR = "__DEFAULT_COLOR__";

        var elements = [];
        data.nodes.forEach(function (n) {
            elements.push({ data: n });
        });
        data.edges.forEach(function (e, idx) {
            elements.push({
                data: {
                    id: 'e' + idx,
                    source: e.source,
                    target: e.target,
                    kind: e.kind
                }
            });
        });

        var cy = cytoscape({
            container: document.getElementById('cy'),
            elements: elements,
            style: [
                {
                    selector: 'node',
                    style: {
                        'background-color': 'data(color)',
                        'width': 'data(size)',
                        'height': 'data(size)',
                        'label': 'data(label)',
                        'font-size': 9,
                        'color': '#333',
                        'text-valign': 'bottom',
                        'text-halign': 'center',
                        'text-margin-y': 4,
                        'border-width': 1,
                        'border-color': '#333'
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 1,
                        'line-color': '#bbb',
                        'target-arrow-color': '#bbb',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'opacity': 0.6
                    }
                }
            ],
            layout: {
                name: 'cose',
                animate: false,
                nodeRepulsion: 4000,
                idealEdgeLength: 80,
                gravity: 0.25
            }
        });

        cy.on('tap', 'node', function (evt) {
            var n = evt.target.data();
            document.getElementById('d-name').textContent = n.label;
            document.getElementById('d-role').textContent = n.role;
            document.getElementById('d-conf').textContent = Number(n.confidence).toFixed(2);
            document.getElementById('d-deg').textContent = n.degree;
        });

        var legend = document.getElementById('legend-items');
        Object.keys(AI_ROLE_COLORS).forEach(function (role) {
            var li = document.createElement('li');
            var sw = document.createElement('span');
            sw.className = 'swatch';
            sw.style.background = AI_ROLE_COLORS[role];
            li.appendChild(sw);
            li.appendChild(document.createTextNode(role));
            legend.appendChild(li);
        });
        var unclassified = document.createElement('li');
        var uSw = document.createElement('span');
        uSw.className = 'swatch';
        uSw.style.background = DEFAULT_COLOR;
        unclassified.appendChild(uSw);
        unclassified.appendChild(document.createTextNode('UNCLASSIFIED'));
        legend.appendChild(unclassified);
    })();
    </script>
</body>
</html>
"""


def build_cytoscape_html(
    graph: Mapping[str, Any],
    mappings: Iterable[Any] | None = None,
) -> str:
    """Return a full HTML page rendering ``graph`` with cytoscape.js (no I/O)."""
    graph_data = build_cytoscape_graph_data(graph, mappings)
    graph_json = json.dumps(graph_data, separators=(",", ":"))
    roles_json = json.dumps(AI_ROLE_COLORS)

    html = _CYTOSCAPE_TEMPLATE
    html = html.replace("__CYTOSCAPE_CDN__", CYTOSCAPE_CDN)
    html = html.replace("__GRAPH_JSON__", graph_json)
    html = html.replace("__AI_ROLE_COLORS__", roles_json)
    html = html.replace("__DEFAULT_COLOR__", DEFAULT_NODE_COLOR)
    return html


def render_cytoscape_html(
    graph: Mapping[str, Any],
    output_path: str | Path,
    mappings: Iterable[Any] | None = None,
) -> Path:
    """Render ``graph`` as a self-contained cytoscape.js page at ``output_path``."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    html = build_cytoscape_html(graph, mappings)
    output.write_text(html, encoding="utf-8")
    logger.info("Cytoscape HTML graph written to %s", output)
    return output
