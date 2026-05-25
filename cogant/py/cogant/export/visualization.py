"""Compatibility visualization exports.

Historically, a few callers imported visualization helpers from
``cogant.export.visualization`` even though the maintained implementations now
live in :mod:`cogant.viz`.  This module keeps that public path real by
re-exporting the production visualizers and providing a small graph-to-Mermaid
adapter for plain dictionary graphs.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from cogant.viz.flow import FlowDiagrammer
from cogant.viz.inspection_dashboard import (
    build_inspection_model,
    render_graphical_abstract_png,
    render_graphical_abstract_svg,
    render_inspection_dashboard_html,
    write_inspection_artifacts,
)
from cogant.viz.matrix_view import MatrixVisualizer
from cogant.viz.pdf_export import PDFExporter
from cogant.viz.pipeline_view import PipelineVisualizer

__all__ = [
    "FlowDiagrammer",
    "GraphToMermaid",
    "MatrixVisualizer",
    "PDFExporter",
    "PipelineVisualizer",
    "build_inspection_model",
    "render_graphical_abstract_png",
    "render_graphical_abstract_svg",
    "render_inspection_dashboard_html",
    "write_inspection_artifacts",
]


def _safe_mermaid_id(value: Any) -> str:
    """Return a Mermaid-safe node id."""
    text = str(value or "node").strip() or "node"
    return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in text)


def _node_label(node: Mapping[str, Any]) -> str:
    """Extract the most readable label from a graph node dictionary."""
    return str(node.get("label") or node.get("name") or node.get("id") or "node")


class GraphToMermaid:
    """Convert a simple graph dictionary into a Mermaid flowchart.

    The adapter accepts the two common COGANT/export shapes:

    * ``{"nodes": [{"id": ..., "label": ...}], "edges": [...]}``
    * ``{"nodes": {"id": {...}}, "edges": {"edge_id": {...}}}``
    """

    def graph_to_mermaid(self, graph: Mapping[str, Any]) -> str:
        """Return Mermaid ``flowchart TD`` syntax for ``graph``."""
        lines = ["flowchart TD"]

        nodes_obj = graph.get("nodes") or []
        node_items: list[Mapping[str, Any]]
        if isinstance(nodes_obj, Mapping):
            node_items = []
            for node_id, data in nodes_obj.items():
                merged: dict[str, Any] = {"id": node_id}
                if isinstance(data, Mapping):
                    merged.update(data)
                node_items.append(merged)
        elif isinstance(nodes_obj, Sequence) and not isinstance(nodes_obj, (str, bytes)):
            node_items = [n for n in nodes_obj if isinstance(n, Mapping)]
        else:
            node_items = []

        known_ids: set[str] = set()
        for node in node_items:
            node_id = str(node.get("id") or _node_label(node))
            safe_id = _safe_mermaid_id(node_id)
            node_label_text = _node_label(node).replace('"', '\\"')
            known_ids.add(node_id)
            lines.append(f'    {safe_id}["{node_label_text}"]')

        edges_obj = graph.get("edges") or []
        edge_items: list[Mapping[str, Any]]
        if isinstance(edges_obj, Mapping):
            edge_items = [e for e in edges_obj.values() if isinstance(e, Mapping)]
        elif isinstance(edges_obj, Sequence) and not isinstance(edges_obj, (str, bytes)):
            edge_items = [e for e in edges_obj if isinstance(e, Mapping)]
        else:
            edge_items = []

        for edge in edge_items:
            source = edge.get("source") or edge.get("source_id")
            target = edge.get("target") or edge.get("target_id")
            if not source or not target:
                continue
            source_id = str(source)
            target_id = str(target)
            for node_id in (source_id, target_id):
                if node_id not in known_ids:
                    known_ids.add(node_id)
                    lines.append(f'    {_safe_mermaid_id(node_id)}["{node_id}"]')
            edge_label = edge.get("label") or edge.get("kind") or edge.get("type")
            if edge_label:
                lines.append(
                    f"    {_safe_mermaid_id(source_id)} -->|{str(edge_label).replace('|', '/')[:40]}| "
                    f"{_safe_mermaid_id(target_id)}"
                )
            else:
                lines.append(f"    {_safe_mermaid_id(source_id)} --> {_safe_mermaid_id(target_id)}")

        return "\n".join(lines)
