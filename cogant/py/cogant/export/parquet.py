"""
Parquet exporter for efficient data storage.

Exports nodes and edges as Parquet files using pyarrow.
"""

import logging
from pathlib import Path
from typing import Any

from cogant.schemas.graph import ProgramGraph

logger = logging.getLogger(__name__)


class ParquetExporter:
    """
    Exports program graph to Parquet format for efficient storage and analysis.
    """

    def __init__(self, program_graph: ProgramGraph):
        """
        Initialize the exporter.

        Args:
            program_graph: The program graph to export.
        """
        self.graph = program_graph

    def export(self, output_dir: Path) -> list[str]:
        """
        Export nodes and edges to Parquet files.

        Args:
            output_dir: Output directory path.

        Returns:
            List of exported file names.
        """
        logger.info(f"Exporting graph to Parquet in {output_dir}...")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        files: list[str] = []

        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            logger.warning("pyarrow not installed, skipping Parquet export")
            return files

        # Export nodes
        nodes_file = self._export_nodes(output_dir, pa, pq)
        if nodes_file:
            files.append(nodes_file)

        # Export edges
        edges_file = self._export_edges(output_dir, pa, pq)
        if edges_file:
            files.append(edges_file)

        logger.info(f"Exported {len(files)} Parquet files")
        return files

    def _export_nodes(self, output_dir: Path, pa: Any, pq: Any) -> str | None:
        """Export nodes to Parquet."""
        try:
            data = self._prepare_nodes_data()

            # Create Arrow table
            table = pa.table(data)

            # Write Parquet file
            output_path = output_dir / "nodes.parquet"
            pq.write_table(table, str(output_path))

            logger.debug(f"Exported {len(data['id'])} nodes to {output_path}")
            return "nodes.parquet"
        except Exception as e:
            logger.error(f"Failed to export nodes: {e}")
            return None

    def _export_edges(self, output_dir: Path, pa: Any, pq: Any) -> str | None:
        """Export edges to Parquet."""
        try:
            data = self._prepare_edges_data()

            # Create Arrow table
            table = pa.table(data)

            # Write Parquet file
            output_path = output_dir / "edges.parquet"
            pq.write_table(table, str(output_path))

            logger.debug(f"Exported {len(data['id'])} edges to {output_path}")
            return "edges.parquet"
        except Exception as e:
            logger.error(f"Failed to export edges: {e}")
            return None

    def _prepare_nodes_data(self) -> dict[str, list[Any]]:
        """Prepare nodes data for Parquet export."""
        data: dict[str, list[Any]] = {
            "id": [],
            "name": [],
            "kind": [],
            "qualified_name": [],
            "path": [],
            "language": [],
            "source_range": [],
        }

        for node in self.graph.nodes.values():
            data["id"].append(node.id)
            data["name"].append(node.name)
            data["kind"].append(str(node.kind))
            data["qualified_name"].append(node.qualified_name)
            data["path"].append(node.path or "")
            data["language"].append(node.language or "")
            data["source_range"].append(str(node.source_range or {}))

        return data

    def _prepare_edges_data(self) -> dict[str, list[Any]]:
        """Prepare edges data for Parquet export."""
        data: dict[str, list[Any]] = {
            "id": [],
            "source_id": [],
            "target_id": [],
            "kind": [],
            "weight": [],
        }

        for edge in self.graph.edges.values():
            data["id"].append(edge.id)
            data["source_id"].append(edge.source_id)
            data["target_id"].append(edge.target_id)
            data["kind"].append(str(edge.kind))
            data["weight"].append(edge.weight)

        return data
