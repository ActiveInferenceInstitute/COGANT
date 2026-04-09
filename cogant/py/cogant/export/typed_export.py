"""
Typed export formats for program graphs and models.

Supports JSON, DOT, Cytoscape.js, and adjacency matrix formats with full type information.
"""

from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import json
import logging

from cogant.schemas.core import Node, Edge, NodeKind, EdgeKind
from cogant.schemas.graph import ProgramGraph

logger = logging.getLogger(__name__)


class TypedExporter:
    """Export program graphs in various typed formats."""

    def __init__(self):
        """Initialize the TypedExporter."""
        pass

    def export_typed_graph(self, graph: ProgramGraph) -> Dict[str, Any]:
        """
        Export full typed JSON with all node/edge metadata and provenance.

        Args:
            graph: ProgramGraph to export.

        Returns:
            Dict with "metadata", "nodes", "edges" keys containing complete graph data.
        """
        export_dict: Dict[str, Any] = {}

        # Export metadata
        export_dict["metadata"] = {
            "repo_uri": graph.metadata.repo_uri,
            "languages": list(graph.metadata.languages),
            "version": graph.metadata.version,
            "created_at": graph.metadata.created_at.isoformat(),
            "updated_at": graph.metadata.updated_at.isoformat(),
            "evidence_sources": graph.metadata.evidence_sources,
            "custom_metadata": graph.metadata.custom_metadata,
            "node_count": graph.node_count(),
            "edge_count": graph.edge_count(),
        }

        # Export nodes with full metadata
        nodes_list: List[Dict[str, Any]] = []
        for node in graph.nodes.values():
            node_dict = {
                "id": node.id,
                "kind": node.kind.value,
                "name": node.name,
                "qualified_name": node.qualified_name,
                "path": node.path,
                "language": node.language,
                "source_range": node.source_range,
                "metadata": node.metadata,
                "created_at": node.created_at.isoformat(),
            }
            nodes_list.append(node_dict)

        export_dict["nodes"] = nodes_list

        # Export edges with full metadata and provenance
        edges_list: List[Dict[str, Any]] = []
        for edge in graph.edges.values():
            edge_dict = {
                "id": edge.id,
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "kind": edge.kind.value,
                "weight": edge.weight,
                "metadata": edge.metadata,
                "evidence_sources": edge.evidence_sources,
                "created_at": edge.created_at.isoformat(),
            }
            edges_list.append(edge_dict)

        export_dict["edges"] = edges_list

        return export_dict

    def export_graphviz_dot(self, graph: ProgramGraph) -> str:
        """
        Export graph in Graphviz DOT format.

        Args:
            graph: ProgramGraph to export.

        Returns:
            DOT format string.
        """
        lines = ["digraph program_graph {", '    rankdir=LR;', '    node [shape=box];']

        # Add nodes with labels
        for node in graph.nodes.values():
            safe_id = node.id.replace("-", "_").replace(".", "_")
            label = node.name
            kind = node.kind.value
            color = self._get_node_color(node.kind)
            lines.append(
                f'    {safe_id} [label="{label}", shape=box, color="{color}"];'
            )

        # Add edges
        for edge in graph.edges.values():
            source_safe = edge.source_id.replace("-", "_").replace(".", "_")
            target_safe = edge.target_id.replace("-", "_").replace(".", "_")
            label = edge.kind.value
            width = max(0.5, min(3.0, edge.weight))
            lines.append(f'    {source_safe} -> {target_safe} [label="{label}", penwidth={width}];')

        lines.append("}")

        return "\n".join(lines)

    def export_cytoscape_json(self, graph: ProgramGraph) -> Dict[str, Any]:
        """
        Export in Cytoscape.js compatible JSON format.

        Args:
            graph: ProgramGraph to export.

        Returns:
            Dict with "elements" key containing nodes and edges for Cytoscape.
        """
        elements: List[Dict[str, Any]] = []

        # Add nodes
        for node in graph.nodes.values():
            node_element = {
                "data": {
                    "id": node.id,
                    "label": node.name,
                    "kind": node.kind.value,
                    "qualified_name": node.qualified_name,
                    "language": node.language,
                }
            }
            elements.append(node_element)

        # Add edges
        for edge in graph.edges.values():
            edge_element = {
                "data": {
                    "id": edge.id,
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "label": edge.kind.value,
                    "weight": edge.weight,
                }
            }
            elements.append(edge_element)

        return {"elements": elements}

    def export_adjacency_matrix(self, graph: ProgramGraph) -> Dict[str, Any]:
        """
        Export adjacency matrix as nested dict with labels.

        Args:
            graph: ProgramGraph to export.

        Returns:
            Dict with "matrix", "node_labels", "edge_types" keys.
        """
        node_list = list(graph.nodes.values())
        node_indices = {node.id: idx for idx, node in enumerate(node_list)}

        # Create adjacency matrix
        n = len(node_list)
        matrix: List[List[int]] = [[0] * n for _ in range(n)]

        edge_type_map: Dict[str, List[List[int]]] = {}

        for edge in graph.edges.values():
            if edge.source_id in node_indices and edge.target_id in node_indices:
                source_idx = node_indices[edge.source_id]
                target_idx = node_indices[edge.target_id]
                matrix[source_idx][target_idx] = int(edge.weight)

                # Track which edge types appear at this position
                edge_kind = edge.kind.value
                if edge_kind not in edge_type_map:
                    edge_type_map[edge_kind] = [[source_idx, target_idx, int(edge.weight)]]
                else:
                    edge_type_map[edge_kind].append([source_idx, target_idx, int(edge.weight)])

        # Create node labels
        node_labels = [
            {
                "index": idx,
                "id": node.id,
                "name": node.name,
                "kind": node.kind.value,
            }
            for idx, node in enumerate(node_list)
        ]

        return {
            "matrix": matrix,
            "node_labels": node_labels,
            "edge_types": edge_type_map,
            "dimensions": [n, n],
        }

    def _get_node_color(self, kind: NodeKind) -> str:
        """Map node kind to a color for visualization."""
        color_map = {
            NodeKind.CLASS: "lightblue",
            NodeKind.FUNCTION: "lightgreen",
            NodeKind.METHOD: "lightyellow",
            NodeKind.MODULE: "lightcyan",
            NodeKind.VARIABLE: "lightgray",
            NodeKind.ENDPOINT: "lightcoral",
            NodeKind.DATA_STRUCTURE: "lightsalmon",
            NodeKind.TEST: "lightsteelblue",
            NodeKind.POLICY: "thistle",
            NodeKind.ACTION: "khaki",
        }
        return color_map.get(kind, "white")
