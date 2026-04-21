"""
SVG diagram export for program graphs and Markov blankets.

Exports program graphs and Markov blanket partitions as SVG diagrams using
graphviz DOT format with graceful fallback when graphviz is unavailable.
"""

import logging
import subprocess
from pathlib import Path

from cogant.markov.blanket import MarkovBlanket
from cogant.schemas.graph import ProgramGraph

logger = logging.getLogger(__name__)


class SVGExporter:
    """Export program graphs and Markov blankets as SVG diagrams."""

    def __init__(self) -> None:
        """Initialize the SVGExporter."""
        self._graphviz_available = self._check_graphviz()

    def export_program_graph(self, graph: ProgramGraph, output_path: str) -> str:
        """
        Export a ProgramGraph as SVG diagram.

        Converts the program graph to graphviz DOT format and renders it as SVG.
        If graphviz is not installed, returns the DOT string and logs a warning.

        Args:
            graph: ProgramGraph to export.
            output_path: Path where SVG file should be written.

        Returns:
            Path to the generated SVG file if successful, otherwise the DOT string.
        """
        logger.info(f"Exporting program graph to SVG: {output_path}")

        dot_string = self.graph_to_dot(graph)

        if self._graphviz_available:
            return self._render_dot_to_svg(dot_string, output_path)
        else:
            logger.warning(
                "graphviz not available; returning DOT format. Install graphviz to render as SVG."
            )
            dot_path = output_path.replace(".svg", ".dot")
            Path(dot_path).write_text(dot_string)
            return dot_path

    def export_markov_blanket(self, blanket: MarkovBlanket, output_path: str) -> str:
        """
        Export a Markov blanket partition as SVG diagram with colored regions.

        Renders the blanket with subgraph clusters for each partition region,
        color-coded to distinguish different roles.

        Args:
            blanket: MarkovBlanket partition to export.
            output_path: Path where SVG file should be written.

        Returns:
            Path to the generated SVG file if successful, otherwise the DOT string.
        """
        logger.info(f"Exporting Markov blanket to SVG: {output_path}")

        dot_string = self.blanket_to_dot(blanket)

        if self._graphviz_available:
            return self._render_dot_to_svg(dot_string, output_path)
        else:
            logger.warning(
                "graphviz not available; returning DOT format. Install graphviz to render as SVG."
            )
            dot_path = output_path.replace(".svg", ".dot")
            Path(dot_path).write_text(dot_string)
            return dot_path

    def graph_to_dot(self, graph: ProgramGraph) -> str:
        """
        Convert a ProgramGraph to graphviz DOT language format.

        Creates a directed graph with nodes colored by kind and edges labeled
        by relationship type and weighted by edge weight.

        Args:
            graph: ProgramGraph to convert.

        Returns:
            DOT format string representation of the graph.
        """
        lines = ["digraph program_graph {", "    rankdir=LR;", "    node [shape=box];"]

        # Add nodes with colors and labels
        for node in graph.nodes.values():
            safe_id = self._safe_id(node.id)
            label = node.name
            color = self._get_node_color(str(node.kind))
            lines.append(
                f'    {safe_id} [label="{label}", shape=box, color="{color}", style=filled];'
            )

        # Add edges with labels and weights
        for edge in graph.edges.values():
            source_safe = self._safe_id(edge.source_id)
            target_safe = self._safe_id(edge.target_id)
            label = edge.kind.value
            width = max(0.5, min(3.0, edge.weight))
            lines.append(f'    {source_safe} -> {target_safe} [label="{label}", penwidth={width}];')

        lines.append("}")
        return "\n".join(lines)

    def blanket_to_dot(self, blanket: MarkovBlanket) -> str:
        """
        Convert a Markov blanket partition to graphviz DOT with subgraph clusters.

        Creates subgraph clusters for each partition region with distinct colors.
        Nodes are colored by their role within the partition.

        Args:
            blanket: MarkovBlanket partition to convert.

        Returns:
            DOT format string representation with subgraph clusters.
        """
        lines = ["digraph markov_blanket {", "    rankdir=LR;"]
        lines.append("    graph [bgcolor=white];")

        # Define cluster colors
        cluster_colors = {
            "core": "lightblue",
            "markov": "lightgreen",
            "external": "lightgray",
        }

        # Add nodes grouped by partition region
        cluster_id = 0
        for region_name, nodes in blanket.partitions.items():
            color = cluster_colors.get(region_name, "white")
            lines.append(f"    subgraph cluster_{cluster_id} {{")
            lines.append(f'        label="{region_name}";')
            lines.append("        style=filled;")
            lines.append(f'        color="{color}";')
            lines.append(f'        fillcolor="{color}";')

            for node_id in nodes:
                safe_id = self._safe_id(node_id)
                lines.append(f"        {safe_id};")

            lines.append("    }")
            cluster_id += 1

        # Add edges from core to other partitions
        if hasattr(blanket, "edges"):
            for edge in blanket.edges:  # type: ignore
                source_safe = self._safe_id(edge.source_id)
                target_safe = self._safe_id(edge.target_id)
                lines.append(f"    {source_safe} -> {target_safe};")

        lines.append("}")
        return "\n".join(lines)

    def _safe_id(self, node_id: str) -> str:
        """Convert a node ID to a safe graphviz identifier."""
        return node_id.replace("-", "_").replace(".", "_").replace("/", "_")

    def _get_node_color(self, kind: str) -> str:
        """Map node kind to a color for visualization."""
        color_map = {
            "class": "lightblue",
            "function": "lightgreen",
            "method": "lightyellow",
            "module": "lightcyan",
            "variable": "lightgray",
            "endpoint": "lightcoral",
            "data_structure": "lightsalmon",
            "test": "lightsteelblue",
            "policy": "thistle",
            "action": "khaki",
            "hidden_state": "plum",
            "observation": "peachpuff",
        }
        return color_map.get(kind, "white")

    def _check_graphviz(self) -> bool:
        """Check if graphviz is installed."""
        try:
            subprocess.run(
                ["dot", "-V"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _render_dot_to_svg(self, dot_string: str, output_path: str) -> str:
        """
        Render DOT string to SVG using graphviz.

        Args:
            dot_string: DOT format string.
            output_path: Path where SVG should be written.

        Returns:
            Path to the generated SVG file.

        Raises:
            RuntimeError: If graphviz rendering fails.
        """
        try:
            subprocess.run(
                ["dot", "-Tsvg", "-o", output_path],
                input=dot_string.encode("utf-8"),
                capture_output=True,
                timeout=30,
                check=True,
            )
            logger.info(f"Generated SVG: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to render SVG: {e.stderr.decode('utf-8', errors='ignore')}")
            raise RuntimeError(f"graphviz rendering failed: {e}") from e
        except subprocess.TimeoutExpired as e:
            logger.error("graphviz rendering timed out")
            raise RuntimeError("graphviz rendering timed out") from e
