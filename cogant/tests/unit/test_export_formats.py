"""Unit tests for multi-format export module."""

from pathlib import Path

import pytest

from cogant.export.formats import (
    ExportConfig,
    ExportFormat,
    MultiFormatExporter,
)
from cogant.schemas.core import Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph


@pytest.mark.unit
class TestExportFormat:
    """Test ExportFormat enum."""

    def test_export_format_json(self) -> None:
        """Test JSON format enum value."""
        assert ExportFormat.JSON.value == "json"

    def test_export_format_graphml(self) -> None:
        """Test GraphML format enum value."""
        assert ExportFormat.GRAPHML.value == "graphml"

    def test_export_format_parquet(self) -> None:
        """Test Parquet format enum value."""
        assert ExportFormat.PARQUET.value == "parquet"

    def test_export_format_svg(self) -> None:
        """Test SVG format enum value."""
        assert ExportFormat.SVG.value == "svg"

    def test_export_format_png(self) -> None:
        """Test PNG format enum value."""
        assert ExportFormat.PNG.value == "png"

    def test_export_format_pdf(self) -> None:
        """Test PDF format enum value."""
        assert ExportFormat.PDF.value == "pdf"

    def test_export_format_mermaid(self) -> None:
        """Test Mermaid format enum value."""
        assert ExportFormat.MERMAID.value == "mermaid"

    def test_export_format_dot(self) -> None:
        """Test DOT format enum value."""
        assert ExportFormat.DOT.value == "dot"

    def test_export_format_jsonlines(self) -> None:
        """Test JSONLINES format enum value."""
        assert ExportFormat.JSONLINES.value == "jsonlines"

    def test_all_export_formats(self) -> None:
        """Test that all 9 expected export formats exist."""
        formats = list(ExportFormat)
        assert len(formats) == 9


@pytest.mark.unit
class TestExportConfig:
    """Test ExportConfig dataclass."""

    def test_export_config_creation(self) -> None:
        """Test creating an ExportConfig."""
        config = ExportConfig(
            formats=[ExportFormat.JSON, ExportFormat.DOT],
            output_dir="/tmp/output",
            prefix="test_export",
            overwrite=True,
        )
        assert len(config.formats) == 2
        assert config.output_dir == "/tmp/output"
        assert config.prefix == "test_export"
        assert config.overwrite is True

    def test_export_config_defaults(self) -> None:
        """Test ExportConfig with default values."""
        config = ExportConfig(
            formats=[ExportFormat.JSON],
            output_dir="/tmp",
        )
        assert config.prefix == "cogant_export"
        assert config.overwrite is False

    def test_export_config_single_format(self) -> None:
        """Test ExportConfig with single format."""
        config = ExportConfig(
            formats=[ExportFormat.JSON],
            output_dir="/tmp",
        )
        assert len(config.formats) == 1


@pytest.mark.unit
class TestMultiFormatExporter:
    """Test MultiFormatExporter."""

    def test_exporter_creation(self) -> None:
        """Test creating a MultiFormatExporter."""
        exporter = MultiFormatExporter()
        assert exporter is not None
        assert exporter.typed_exporter is not None
        assert exporter.schema_exporter is not None

    def test_export_gnn_bundle_json(self, tmp_path: Path) -> None:
        """Test exporting GNN bundle as JSON."""
        exporter = MultiFormatExporter()
        bundle = {
            "version": "0.5.0",
            "metadata": {"id": "test_bundle", "schema_name": "TestAgent"},
            "state_space": {
                "hidden_states": ["state1", "state2"],
                "observations": ["obs1"],
                "actions": ["act1"],
            },
            "matrices": {
                "A": [[0.9, 0.1]],
                "B": [[[0.8, 0.2]]],
                "C": [1.0],
                "D": [0.5],
            },
        }

        config = ExportConfig(
            formats=[ExportFormat.JSON],
            output_dir=str(tmp_path),
            prefix="test_bundle",
        )

        results = exporter.export_gnn_bundle(bundle, config)
        assert ExportFormat.JSON in results
        assert Path(results[ExportFormat.JSON]).exists()

    def test_export_gnn_bundle_jsonlines(self, tmp_path: Path) -> None:
        """Test exporting GNN bundle as JSONLINES."""
        exporter = MultiFormatExporter()
        bundle = {
            "version": "0.5.0",
            "metadata": {"id": "test", "schema_name": "Test"},
            "state_space": {"hidden_states": ["s1"]},
        }

        config = ExportConfig(
            formats=[ExportFormat.JSONLINES],
            output_dir=str(tmp_path),
        )

        results = exporter.export_gnn_bundle(bundle, config)
        assert ExportFormat.JSONLINES in results

    def test_export_all_no_formats_raises(self, tmp_path: Path) -> None:
        """Test that export_all raises when no formats specified."""
        exporter = MultiFormatExporter()
        config = ExportConfig(
            formats=[],
            output_dir=str(tmp_path),
        )

        with pytest.raises(ValueError):
            exporter.export_all({}, config)

    def test_export_graph_no_formats_raises(self, tmp_path: Path) -> None:
        """Test that export_graph raises when no formats specified."""
        exporter = MultiFormatExporter()
        metadata = GraphMetadata(repo_uri="test://repo")
        graph = ProgramGraph(metadata=metadata)

        config = ExportConfig(
            formats=[],
            output_dir=str(tmp_path),
        )

        with pytest.raises(ValueError):
            exporter.export_graph(graph, config)

    def test_export_gnn_bundle_no_formats_raises(self, tmp_path: Path) -> None:
        """Test that export_gnn_bundle raises when no formats specified."""
        exporter = MultiFormatExporter()
        config = ExportConfig(
            formats=[],
            output_dir=str(tmp_path),
        )

        with pytest.raises(ValueError):
            exporter.export_gnn_bundle({}, config)

    def test_export_creates_output_directory(self, tmp_path: Path) -> None:
        """Test that export creates output directory if needed."""
        exporter = MultiFormatExporter()
        nonexistent_dir = tmp_path / "nonexistent"
        assert not nonexistent_dir.exists()

        bundle = {
            "version": "0.5.0",
            "metadata": {},
            "matrices": {},
        }

        config = ExportConfig(
            formats=[ExportFormat.JSON],
            output_dir=str(nonexistent_dir),
        )

        exporter.export_gnn_bundle(bundle, config)
        assert nonexistent_dir.exists()

    @pytest.mark.slow
    def test_export_program_graph_json(self, tmp_path: Path) -> None:
        """Test exporting program graph as JSON."""
        exporter = MultiFormatExporter()
        metadata = GraphMetadata(repo_uri="test://repo")
        graph = ProgramGraph(metadata=metadata)

        # Add a node
        node = Node(
            id="test_node",
            kind=NodeKind.FUNCTION,
            name="test_func",
            qualified_name="module.test_func",
        )
        graph.add_node(node)

        config = ExportConfig(
            formats=[ExportFormat.JSON],
            output_dir=str(tmp_path),
            prefix="test_graph",
        )

        results = exporter.export_graph(graph, config)
        assert ExportFormat.JSON in results
        assert Path(results[ExportFormat.JSON]).exists()

    def test_export_gnn_bundle_multiple_formats(self, tmp_path: Path) -> None:
        """Test exporting GNN bundle to multiple formats."""
        exporter = MultiFormatExporter()
        bundle = {
            "version": "0.5.0",
            "metadata": {"id": "test"},
        }

        config = ExportConfig(
            formats=[ExportFormat.JSON, ExportFormat.JSONLINES],
            output_dir=str(tmp_path),
        )

        results = exporter.export_gnn_bundle(bundle, config)
        assert ExportFormat.JSON in results
        assert ExportFormat.JSONLINES in results

    def test_export_config_custom_prefix(self, tmp_path: Path) -> None:
        """Test export with custom prefix."""
        exporter = MultiFormatExporter()
        bundle = {"version": "0.5.0"}

        config = ExportConfig(
            formats=[ExportFormat.JSON],
            output_dir=str(tmp_path),
            prefix="custom_name",
        )

        results = exporter.export_gnn_bundle(bundle, config)
        output_file = Path(results[ExportFormat.JSON])
        assert "custom_name" in output_file.name
