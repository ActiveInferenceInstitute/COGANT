"""
Bundle exporter - orchestrates full export to multiple formats.

Writes GNN markdown, JSON, GraphML, Parquet, HTML, and provenance bundle
to output directory with manifest.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from cogant.export.graphml import GraphMLExporter
from cogant.export.parquet import ParquetExporter
from cogant.gnn.formatter import GNNMarkdownFormatter
from cogant.gnn.json_export import GNNJSONExporter
from cogant.process.extractor import ProcessModel
from cogant.schemas.graph import ProgramGraph
from cogant.statespace.compiler import StateSpaceModel

logger = logging.getLogger(__name__)


@dataclass
class BundleManifest:
    """Manifest for an export bundle."""
    bundle_id: str
    schema_name: str
    created_at: datetime
    files: dict[str, str]  # filename -> description
    checksums: dict[str, str]  # filename -> checksum
    metadata: dict[str, Any]


class BundleExporter:
    """
    Orchestrates full export to multiple formats and creates a complete bundle.
    """

    FORMATS = ["markdown", "json", "graphml", "parquet", "html"]

    def __init__(
        self,
        program_graph: ProgramGraph,
        state_space_model: StateSpaceModel,
        process_model: ProcessModel,
        semantic_mappings: dict[str, Any],
        output_dir: Path,
    ):
        """
        Initialize the exporter.

        Args:
            program_graph: The program graph.
            state_space_model: The state space model.
            process_model: The process model.
            semantic_mappings: Semantic mappings dictionary.
            output_dir: Output directory path.
        """
        self.graph = program_graph
        self.state_space = state_space_model
        self.process = process_model
        self.mappings = semantic_mappings
        self.output_dir = Path(output_dir)

    def export(self, formats: list[str] | None = None) -> Path:
        """
        Export model to all specified formats.

        Args:
            formats: List of formats to export. Defaults to all formats.

        Returns:
            Path to the output bundle directory.
        """
        if formats is None:
            formats = self.FORMATS

        logger.info(f"Exporting bundle to {self.output_dir} in formats: {formats}")

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Track files and checksums
        files = {}
        checksums = {}

        # Export each format
        if "markdown" in formats:
            file_path, checksum = self._export_markdown()
            if file_path:
                files["gnn.md"] = "GNN model in markdown format"
                checksums["gnn.md"] = checksum

        if "json" in formats:
            file_path, checksum = self._export_json()
            if file_path:
                files["gnn.json"] = "GNN model in JSON format"
                checksums["gnn.json"] = checksum

        if "graphml" in formats:
            file_path, checksum = self._export_graphml()
            if file_path:
                files["program_graph.graphml"] = "Program graph in GraphML format"
                checksums["program_graph.graphml"] = checksum

        if "parquet" in formats:
            file_paths, checksums_dict = self._export_parquet()
            files.update(dict.fromkeys(file_paths, "Graph data in Parquet format"))
            checksums.update(checksums_dict)

        if "html" in formats:
            file_path, checksum = self._export_html()
            if file_path:
                files["index.html"] = "Interactive HTML visualization"
                checksums["index.html"] = checksum

        # Write manifest
        manifest = self._create_manifest(files, checksums)
        manifest_path = self.output_dir / "MANIFEST.json"
        with open(manifest_path, "w") as f:
            json.dump(self._manifest_to_dict(manifest), f, indent=2, default=str)
        files["MANIFEST.json"] = "Bundle manifest"
        checksums["MANIFEST.json"] = self._compute_checksum(manifest_path)

        logger.info(f"Export complete: {len(files)} files written")
        return self.output_dir

    def _export_markdown(self) -> tuple[Path | None, str]:
        """Export to markdown format."""
        try:
            formatter = GNNMarkdownFormatter(
                self.graph,
                self.state_space,
                self.process,
                self.mappings,
            )
            content = formatter.format()

            output_path = self.output_dir / "gnn.md"
            with open(output_path, "w") as f:
                f.write(content)

            checksum = self._compute_checksum(output_path)
            logger.info(f"Exported markdown: {output_path}")
            return output_path, checksum
        except Exception as e:
            logger.error(f"Failed to export markdown: {e}")
            return None, ""

    def _export_json(self) -> tuple[Path | None, str]:
        """Export to JSON format."""
        try:
            exporter = GNNJSONExporter(
                self.graph,
                self.state_space,
                self.process,
                self.mappings,
            )
            content = exporter.export_to_string(indent=2)

            output_path = self.output_dir / "gnn.json"
            with open(output_path, "w") as f:
                f.write(content)

            checksum = self._compute_checksum(output_path)
            logger.info(f"Exported JSON: {output_path}")
            return output_path, checksum
        except Exception as e:
            logger.error(f"Failed to export JSON: {e}")
            return None, ""

    def _export_graphml(self) -> tuple[Path | None, str]:
        """Export to GraphML format."""
        try:
            exporter = GraphMLExporter(self.graph)
            content = exporter.export()

            output_path = self.output_dir / "program_graph.graphml"
            with open(output_path, "w") as f:
                f.write(content)

            checksum = self._compute_checksum(output_path)
            logger.info(f"Exported GraphML: {output_path}")
            return output_path, checksum
        except Exception as e:
            logger.error(f"Failed to export GraphML: {e}")
            return None, ""

    def _export_parquet(self) -> tuple[list[str], dict[str, str]]:
        """Export to Parquet format."""
        try:
            exporter = ParquetExporter(self.graph)
            files = exporter.export(self.output_dir)

            checksums = {
                f: self._compute_checksum(self.output_dir / f)
                for f in files
            }
            logger.info(f"Exported Parquet: {len(files)} files")
            return files, checksums
        except Exception as e:
            logger.error(f"Failed to export Parquet: {e}")
            return [], {}

    def _export_html(self) -> tuple[Path | None, str]:
        """Export to HTML format."""
        try:
            # For now, create a simple HTML wrapper
            html_content = self._generate_html()

            output_path = self.output_dir / "index.html"
            with open(output_path, "w") as f:
                f.write(html_content)

            checksum = self._compute_checksum(output_path)
            logger.info(f"Exported HTML: {output_path}")
            return output_path, checksum
        except Exception as e:
            logger.error(f"Failed to export HTML: {e}")
            return None, ""

    def _generate_html(self) -> str:
        """Generate HTML visualization."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>GNN Model: {self.state_space.schema_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .section {{ margin: 20px 0; padding: 10px; border: 1px solid #ddd; }}
    </style>
</head>
<body>
    <h1>GNN Model: {self.state_space.schema_name}</h1>
    <div class="section">
        <h2>Model Summary</h2>
        <p>Schema: {self.state_space.schema_name}</p>
        <p>State Variables: {len(self.state_space.variables)}</p>
        <p>Observations: {len(self.state_space.observations)}</p>
        <p>Actions: {len(self.state_space.actions)}</p>
    </div>
</body>
</html>"""

    def _create_manifest(
        self,
        files: dict[str, str],
        checksums: dict[str, str],
    ) -> BundleManifest:
        """Create bundle manifest."""

        return BundleManifest(
            bundle_id=f"bundle_{self.state_space.id}",
            schema_name=self.state_space.schema_name,
            created_at=datetime.now(),
            files=files,
            checksums=checksums,
            metadata={
                "node_count": len(self.graph.nodes),
                "edge_count": len(self.graph.edges),
                "variable_count": len(self.state_space.variables),
                "stage_count": len(self.process.stages),
            },
        )

    def _manifest_to_dict(self, manifest: BundleManifest) -> dict[str, Any]:
        """Convert manifest to dictionary."""
        return {
            "bundle_id": manifest.bundle_id,
            "schema_name": manifest.schema_name,
            "created_at": str(manifest.created_at),
            "files": manifest.files,
            "checksums": manifest.checksums,
            "metadata": manifest.metadata,
        }

    def _compute_checksum(self, file_path: Path) -> str:
        """Compute SHA256 checksum of a file."""
        import hashlib
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
