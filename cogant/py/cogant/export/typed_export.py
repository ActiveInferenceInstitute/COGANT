"""
Typed export formats for program graphs and models.

Supports JSON, DOT, Cytoscape.js, adjacency matrix, JSONL, and Arrow IPC formats
with full type information.
"""

import json
import logging
from pathlib import Path
from typing import Any

from cogant.schemas.core import NodeKind
from cogant.schemas.graph import ProgramGraph

logger = logging.getLogger(__name__)


class TypedExporter:
    """Export program graphs in various typed formats."""

    def __init__(self) -> None:
        """Initialize the TypedExporter."""
        pass

    def export_typed_graph(self, graph: ProgramGraph) -> dict[str, Any]:
        """
        Export full typed JSON with all node/edge metadata and provenance.

        Args:
            graph: ProgramGraph to export.

        Returns:
            Dict with "metadata", "nodes", "edges" keys containing complete graph data.
        """
        export_dict: dict[str, Any] = {}

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
        nodes_list: list[dict[str, Any]] = []
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
        edges_list: list[dict[str, Any]] = []
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

    def export_cytoscape_json(self, graph: ProgramGraph) -> dict[str, Any]:
        """
        Export in Cytoscape.js compatible JSON format.

        Args:
            graph: ProgramGraph to export.

        Returns:
            Dict with "elements" key containing nodes and edges for Cytoscape.
        """
        elements: list[dict[str, Any]] = []

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

    def export_adjacency_matrix(self, graph: ProgramGraph) -> dict[str, Any]:
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
        matrix: list[list[int]] = [[0] * n for _ in range(n)]

        edge_type_map: dict[str, list[list[int]]] = {}

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

    def to_jsonlines(self, items: list[Any], output_path: str) -> str:
        """
        Export items as newline-delimited JSON (JSONL).

        Each item is written as a separate JSON object on its own line.
        Useful for streaming large datasets or multiple independent records.

        Args:
            items: List of items to export.
            output_path: Path where JSONL file should be written.

        Returns:
            Path to the written JSONL file.
        """
        logger.info(f"Exporting {len(items)} items to JSONL: {output_path}")

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            for item in items:
                json_line = json.dumps(item, default=str)
                f.write(json_line + "\n")

        logger.info(f"Exported {len(items)} lines to {output_path}")
        return str(output_file)

    def to_arrow_ipc(self, items: list[Any], output_path: str) -> str:
        """
        Export items as Apache Arrow IPC (Inter-Process Communication) format.

        Requires pyarrow to be installed. IPC format is efficient for binary
        interchange between processes and can be memory-mapped.

        Args:
            items: List of items to export.
            output_path: Path where Arrow IPC file should be written.

        Returns:
            Path to the written Arrow IPC file.

        Raises:
            ImportError: If pyarrow is not installed.
        """
        try:
            import pyarrow as pa
        except ImportError:
            logger.error("pyarrow not installed; cannot export Arrow IPC format")
            raise ImportError("pyarrow required for Arrow IPC export") from None

        logger.info(f"Exporting {len(items)} items to Arrow IPC: {output_path}")

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Convert items to Arrow table
        # For now, assume items are dicts (node/edge exports)
        if items and isinstance(items[0], dict):
            table = pa.Table.from_pylist(items)
            with pa.ipc.new_file(str(output_file)) as writer:
                writer.write_table(table)
        else:
            logger.warning("Cannot convert items to Arrow table; skipping export")
            return output_path

        logger.info(f"Exported Arrow IPC: {output_path}")
        return str(output_file)

    def export_summary(self, pipeline_result: dict[str, Any]) -> dict[str, Any]:
        """
        Export a compact summary of pipeline result suitable for logging/monitoring.

        Returns key metrics and status without full data, suitable for
        dashboards, logs, or API responses.

        Args:
            pipeline_result: Complete pipeline execution result.

        Returns:
            Summary dict with essential information.
        """
        summary: dict[str, Any] = {}

        # Core status
        summary["status"] = pipeline_result.get("status", "unknown")
        summary["timestamp"] = pipeline_result.get("timestamp", None)
        summary["duration_seconds"] = pipeline_result.get("duration_seconds", 0)

        # Graph stats
        if "program_graph" in pipeline_result:
            graph_data = pipeline_result["program_graph"]
            summary["graph_stats"] = {
                "node_count": graph_data.get("metadata", {}).get("node_count", 0),
                "edge_count": graph_data.get("metadata", {}).get("edge_count", 0),
                "languages": graph_data.get("metadata", {}).get("languages", []),
            }

        # Semantic mappings stats
        if "semantic_mappings" in pipeline_result:
            mappings = pipeline_result["semantic_mappings"]
            if "mappings" in mappings:
                role_counts: dict[str, int] = {}
                for mapping in mappings["mappings"].values():
                    role = mapping.get("role", "unknown")
                    role_counts[role] = role_counts.get(role, 0) + 1
                summary["semantic_mapping_stats"] = role_counts

        # State space stats
        if "state_space_model" in pipeline_result:
            state_space = pipeline_result["state_space_model"]
            summary["state_space_stats"] = {
                "hidden_states": len(state_space.get("hidden_states", [])),
                "observations": len(state_space.get("observations", [])),
                "actions": len(state_space.get("actions", [])),
            }

        # Validation results
        if "validation_results" in pipeline_result:
            val_results = pipeline_result["validation_results"]
            summary["validation"] = {
                "passed": val_results.get("passed", False),
                "score": val_results.get("score", 0),
                "finding_count": len(val_results.get("findings", [])),
            }

        return summary

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
