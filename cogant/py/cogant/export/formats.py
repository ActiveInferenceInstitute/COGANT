"""
Multi-format batch export for COGANT artifacts.

Supports exporting to multiple formats (JSON, GraphML, Parquet, SVG, etc.)
in a single operation with consistent configuration.
"""

import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from cogant.export.graphml import GraphMLExporter
from cogant.export.json_schema import JSONSchemaExporter
from cogant.export.parquet import ParquetExporter
from cogant.export.svg_export import SVGExporter
from cogant.export.typed_export import TypedExporter
from cogant.schemas.graph import ProgramGraph

logger = logging.getLogger(__name__)


class ExportFormat(Enum):
    """Supported export formats."""

    JSON = "json"
    GRAPHML = "graphml"
    PARQUET = "parquet"
    SVG = "svg"
    PNG = "png"
    PDF = "pdf"
    MERMAID = "mermaid"
    DOT = "dot"
    JSONLINES = "jsonlines"


@dataclass
class ExportConfig:
    """Configuration for multi-format export."""

    formats: list[ExportFormat]
    output_dir: str
    prefix: str = "cogant_export"
    overwrite: bool = False


class MultiFormatExporter:
    """Orchestrates export of COGANT artifacts to multiple formats."""

    def __init__(self) -> None:
        """Initialize the MultiFormatExporter."""
        self.typed_exporter = TypedExporter()
        self.graphml_exporter_class = GraphMLExporter
        self.parquet_exporter_class = ParquetExporter
        self.svg_exporter = SVGExporter()
        self.schema_exporter = JSONSchemaExporter()

    def export_all(
        self,
        pipeline_result: dict[str, Any],
        config: ExportConfig,
    ) -> dict[ExportFormat, str]:
        """
        Export pipeline result to all requested formats.

        Args:
            pipeline_result: Complete pipeline execution result.
            config: Export configuration.

        Returns:
            Dict mapping ExportFormat to output file path.

        Raises:
            ValueError: If no formats specified or output directory is invalid.
        """
        if not config.formats:
            raise ValueError("At least one export format must be specified")

        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results: dict[ExportFormat, str] = {}

        logger.info(
            f"Exporting pipeline result to {len(config.formats)} formats in {output_dir}"
        )

        for fmt in config.formats:
            try:
                output_path = self._export_format(
                    pipeline_result,
                    fmt,
                    output_dir,
                    config.prefix,
                )
                if output_path:
                    results[fmt] = output_path
                    logger.info(f"Exported {fmt.value}: {output_path}")
            except Exception as e:
                logger.error(f"Failed to export {fmt.value}: {e}")

        return results

    def export_graph(
        self,
        graph: ProgramGraph,
        config: ExportConfig,
    ) -> dict[ExportFormat, str]:
        """
        Export a ProgramGraph to requested formats.

        Args:
            graph: ProgramGraph to export.
            config: Export configuration.

        Returns:
            Dict mapping ExportFormat to output file path.
        """
        if not config.formats:
            raise ValueError("At least one export format must be specified")

        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results: dict[ExportFormat, str] = {}

        logger.info(f"Exporting program graph to {len(config.formats)} formats")

        for fmt in config.formats:
            try:
                output_path = self._export_graph_format(graph, fmt, output_dir, config.prefix)
                if output_path:
                    results[fmt] = output_path
                    logger.info(f"Exported {fmt.value}: {output_path}")
            except Exception as e:
                logger.error(f"Failed to export graph as {fmt.value}: {e}")

        return results

    def export_gnn_bundle(
        self,
        bundle: dict[str, Any],
        config: ExportConfig,
    ) -> dict[ExportFormat, str]:
        """
        Export a GNN bundle to requested formats.

        Args:
            bundle: GNN bundle dictionary to export.
            config: Export configuration.

        Returns:
            Dict mapping ExportFormat to output file path.
        """
        if not config.formats:
            raise ValueError("At least one export format must be specified")

        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results: dict[ExportFormat, str] = {}

        logger.info(f"Exporting GNN bundle to {len(config.formats)} formats")

        for fmt in config.formats:
            try:
                output_path = self._export_bundle_format(bundle, fmt, output_dir, config.prefix)
                if output_path:
                    results[fmt] = output_path
                    logger.info(f"Exported {fmt.value}: {output_path}")
            except Exception as e:
                logger.error(f"Failed to export bundle as {fmt.value}: {e}")

        return results

    def _export_format(
        self,
        pipeline_result: dict[str, Any],
        fmt: ExportFormat,
        output_dir: Path,
        prefix: str,
    ) -> str | None:
        """Export pipeline result to a specific format."""
        if fmt == ExportFormat.JSON:
            return self._export_pipeline_json(pipeline_result, output_dir, prefix)
        elif fmt == ExportFormat.JSONLINES:
            return self._export_pipeline_jsonlines(pipeline_result, output_dir, prefix)
        else:
            logger.warning(f"Unsupported pipeline export format: {fmt.value}")
            return None

    def _export_graph_format(
        self,
        graph: ProgramGraph,
        fmt: ExportFormat,
        output_dir: Path,
        prefix: str,
    ) -> str | None:
        """Export program graph to a specific format."""
        if fmt == ExportFormat.JSON:
            output_path = output_dir / f"{prefix}_graph.json"
            data = self.typed_exporter.export_typed_graph(graph)
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
            return str(output_path)
        elif fmt == ExportFormat.GRAPHML:
            output_path = output_dir / f"{prefix}_graph.graphml"
            exporter = self.graphml_exporter_class(graph)
            content = exporter.export()
            with open(output_path, "w") as f:
                f.write(content)
            return str(output_path)
        elif fmt == ExportFormat.PARQUET:
            exporter = self.parquet_exporter_class(graph)
            files = exporter.export(output_dir)
            return files[0] if files else None
        elif fmt == ExportFormat.SVG:
            output_path = output_dir / f"{prefix}_graph.svg"
            return self.svg_exporter.export_program_graph(graph, str(output_path))
        elif fmt == ExportFormat.DOT:
            output_path = output_dir / f"{prefix}_graph.dot"
            dot_content = self.typed_exporter.export_graphviz_dot(graph)
            with open(output_path, "w") as f:
                f.write(dot_content)
            return str(output_path)
        else:
            logger.warning(f"Unsupported graph export format: {fmt.value}")
            return None

    def _export_bundle_format(
        self,
        bundle: dict[str, Any],
        fmt: ExportFormat,
        output_dir: Path,
        prefix: str,
    ) -> str | None:
        """Export GNN bundle to a specific format."""
        if fmt == ExportFormat.JSON:
            output_path = output_dir / f"{prefix}_bundle.json"
            with open(output_path, "w") as f:
                json.dump(bundle, f, indent=2, default=str)
            return str(output_path)
        elif fmt == ExportFormat.JSONLINES:
            # Export bundle metadata as JSONL
            output_path = output_dir / f"{prefix}_bundle.jsonl"
            with open(output_path, "w") as f:
                if "metadata" in bundle:
                    f.write(json.dumps(bundle["metadata"]) + "\n")
                if "state_space" in bundle:
                    f.write(json.dumps(bundle["state_space"]) + "\n")
            return str(output_path)
        else:
            logger.warning(f"Unsupported bundle export format: {fmt.value}")
            return None

    def _export_pipeline_json(
        self,
        pipeline_result: dict[str, Any],
        output_dir: Path,
        prefix: str,
    ) -> str:
        """Export pipeline result as JSON."""
        output_path = output_dir / f"{prefix}_result.json"
        with open(output_path, "w") as f:
            json.dump(pipeline_result, f, indent=2, default=str)
        return str(output_path)

    def _export_pipeline_jsonlines(
        self,
        pipeline_result: dict[str, Any],
        output_dir: Path,
        prefix: str,
    ) -> str:
        """Export pipeline result as JSONL."""
        output_path = output_dir / f"{prefix}_result.jsonl"
        with open(output_path, "w") as f:
            # Export metadata, graph summary, and mappings as separate lines
            if "config" in pipeline_result:
                f.write(json.dumps(pipeline_result["config"]) + "\n")
            if "validation_results" in pipeline_result:
                f.write(json.dumps(pipeline_result["validation_results"]) + "\n")
            if "gnn_bundle" in pipeline_result:
                f.write(json.dumps(pipeline_result["gnn_bundle"]) + "\n")
        return str(output_path)
