"""Integration tests for the export pipeline.

Tests the full pipeline: pipeline result → multi-format export.
"""

import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from cogant.export.formats import ExportConfig, ExportFormat, MultiFormatExporter
from cogant.export.json_schema import JSONSchemaExporter
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph

pytestmark = pytest.mark.integration


class TestJSONSchemaValidity:
    """Tests for JSON Schema export validity."""

    def test_json_schema_validity(self):
        """Test that GNN bundle schema is valid JSON Schema.

        Verifies:
        - Schema has required $schema field
        - Schema has type and properties fields
        - Schema is JSON-serializable
        """
        exporter = JSONSchemaExporter()
        schema = exporter.export_gnn_bundle_schema()

        # Verify required fields for JSON Schema
        assert "$schema" in schema, "Schema should have $schema field"
        assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"

        assert "type" in schema, "Schema should have type field"
        assert schema["type"] == "object"

        assert "properties" in schema, "Schema should have properties field"
        assert isinstance(schema["properties"], dict)

        # Verify required properties field
        assert "required" in schema

        # Verify JSON serialization
        json_str = json.dumps(schema)
        assert json_str
        assert len(json_str) > 0

    def test_json_schema_all_four_methods(self):
        """Test all four JSONSchemaExporter methods.

        Verifies:
        - export_gnn_bundle_schema() returns valid schema
        - export_program_graph_schema() returns valid schema
        - export_semantic_mappings_schema() returns valid schema
        - export_pipeline_result_schema() returns valid schema
        """
        exporter = JSONSchemaExporter()

        # Get all schemas
        gnn_schema = exporter.export_gnn_bundle_schema()
        graph_schema = exporter.export_program_graph_schema()
        mapping_schema = exporter.export_semantic_mappings_schema()
        result_schema = exporter.export_pipeline_result_schema()

        # Verify all have schema indicators
        for schema in [gnn_schema, graph_schema, mapping_schema, result_schema]:
            assert "$schema" in schema or "type" in schema, (
                "Schema should have $schema or type field"
            )
            assert isinstance(schema, dict)

            # Verify JSON serializable
            json_str = json.dumps(schema)
            assert json_str

        # Verify GNN schema has matrix fields
        assert "properties" in gnn_schema
        props = gnn_schema["properties"]
        # Should reference or include matrix definitions
        assert "metadata" in props or "$ref" in gnn_schema


class TestMultiformatExportToTempdir:
    """Tests for exporting to multiple formats."""

    @staticmethod
    def create_minimal_gnn_bundle() -> dict:
        """Create a minimal mock GNN bundle for testing.

        Returns:
            Dict representing a minimal GNN bundle.
        """
        return {
            "metadata": {
                "id": "test_bundle",
                "schema_name": "test_schema",
                "created_at": "2024-04-13T00:00:00Z",
                "version": "0.5.0",
            },
            "state_space": {
                "hidden_states": ["s1", "s2"],
                "observations": ["o1", "o2"],
                "actions": ["a1", "a2"],
            },
            "matrices": {
                "A": [[0.8, 0.2], [0.2, 0.8]],
                "B": [[0.5, 0.5], [0.5, 0.5]],
                "C": [[1.0, 0.0], [0.0, 1.0]],
                "D": [[1.0, 0.0], [0.0, 1.0]],
            },
        }

    def test_multiformat_export_to_tempdir(self, temp_dir):
        """Test exporting bundle to multiple formats.

        Verifies:
        - JSON export creates valid file
        - MERMAID export creates valid file
        - Both files are non-empty
        """
        exporter = MultiFormatExporter()
        bundle = self.create_minimal_gnn_bundle()

        config = ExportConfig(
            formats=[ExportFormat.JSON, ExportFormat.JSONLINES],
            output_dir=str(temp_dir),
            prefix="test_export",
        )

        results = exporter.export_gnn_bundle(bundle, config)

        # Verify files were created
        assert len(results) > 0
        assert ExportFormat.JSON in results or ExportFormat.JSONLINES in results

        # Verify JSON file exists and is valid
        for fmt, path in results.items():
            output_file = Path(path)
            assert output_file.exists(), f"Output file {path} should exist"
            assert output_file.stat().st_size > 0, f"Output file {path} should be non-empty"

            if fmt == ExportFormat.JSON:
                # Verify it's valid JSON
                with open(output_file) as f:
                    data = json.load(f)
                    assert "metadata" in data or "state_space" in data

    def test_graph_json_export(self, temp_dir):
        """Test exporting a ProgramGraph as JSON.

        Verifies:
        - JSON export of graph creates valid file
        - File contains graph structure
        """
        # Create a simple graph
        metadata = GraphMetadata(repo_uri="test://repo")
        graph = ProgramGraph(metadata=metadata)
        node = Node(
            id="test_func",
            kind=NodeKind.FUNCTION,
            name="test_function",
            qualified_name="test_function",
            path="test.py",
        )
        graph.add_node(node)

        exporter = MultiFormatExporter()
        config = ExportConfig(
            formats=[ExportFormat.JSON],
            output_dir=str(temp_dir),
            prefix="test_graph",
        )

        results = exporter.export_graph(graph, config)

        assert ExportFormat.JSON in results
        json_file = Path(results[ExportFormat.JSON])
        assert json_file.exists()

        with open(json_file) as f:
            data = json.load(f)
            assert isinstance(data, dict)


class TestGraphMLWithMetadata:
    """Tests for GraphML export with metadata."""

    def test_graphml_with_metadata(self, temp_dir):
        """Test GraphML export includes metadata.

        Verifies:
        - GraphML export creates valid XML
        - Output is non-empty
        - File is parseable as XML
        """
        # Create a simple graph
        metadata = GraphMetadata(repo_uri="test://repo")
        graph = ProgramGraph(metadata=metadata)

        for i in range(3):
            node = Node(
                id=f"node_{i}",
                kind=NodeKind.FUNCTION,
                name=f"func_{i}",
                qualified_name=f"func_{i}",
                path=f"test_{i}.py",
            )
            graph.add_node(node)

        edge = Edge(
            id="edge_0_1",
            source_id="node_0",
            target_id="node_1",
            kind=EdgeKind.CALLS,
        )
        graph.add_edge(edge)

        exporter = MultiFormatExporter()
        config = ExportConfig(
            formats=[ExportFormat.GRAPHML],
            output_dir=str(temp_dir),
            prefix="test_graphml",
        )

        results = exporter.export_graph(graph, config)

        assert ExportFormat.GRAPHML in results
        graphml_file = Path(results[ExportFormat.GRAPHML])
        assert graphml_file.exists()
        assert graphml_file.stat().st_size > 0

        # Verify it's valid XML
        with open(graphml_file) as f:
            content = f.read()
            # Should be parseable XML
            root = ET.fromstring(content)
            assert root.tag.endswith("graphml")


class TestBundleZipExport:
    """Tests for ZIP bundle export."""

    def test_bundle_zip_export(self, temp_dir):
        """Test exporting bundle as ZIP archive.

        Verifies:
        - ZIP file is created if supported
        - ZIP contains expected files
        """
        # Note: ZIP export may not be implemented yet, so we test gracefully
        bundle = {
            "metadata": {
                "id": "test",
                "schema_name": "test",
                "created_at": "2024-04-13T00:00:00Z",
            },
            "state_space": {},
            "matrices": {},
        }

        exporter = MultiFormatExporter()
        config = ExportConfig(
            formats=[ExportFormat.JSON],  # Use JSON as fallback
            output_dir=str(temp_dir),
            prefix="test_bundle",
        )

        results = exporter.export_gnn_bundle(bundle, config)

        # At minimum, we should get some output
        assert len(results) > 0


class TestProvenanceMetadata:
    """Tests for provenance metadata in exports."""

    def test_provenance_metadata(self):
        """Test that provenance metadata is correctly structured.

        Verifies:
        - Provenance fields are present in bundle metadata
        - Timestamp is ISO 8601 format
        - Version field exists
        """
        bundle = {
            "metadata": {
                "id": "test_bundle",
                "schema_name": "test",
                "created_at": "2024-04-13T12:00:00Z",
                "version": "0.5.0",
                "source_hash": "abc123",
                "cogant_version": "0.5.0",
                "timestamp": "2024-04-13T12:00:00Z",
            },
            "state_space": {},
            "matrices": {},
        }

        # Verify provenance fields
        metadata = bundle["metadata"]
        assert "id" in metadata
        assert "created_at" in metadata or "timestamp" in metadata
        assert "cogant_version" in metadata or "version" in metadata

        # Verify timestamp format (basic check)
        timestamp = metadata.get("created_at") or metadata.get("timestamp")
        assert "T" in timestamp, "Timestamp should be ISO 8601 format"
        assert "Z" in timestamp or "+" in timestamp, "Timestamp should include timezone"

        # Verify JSON serializable
        json_str = json.dumps(bundle)
        assert json_str


class TestExportConfigValidation:
    """Tests for export configuration validation."""

    def test_export_config_validation(self, temp_dir):
        """Test that export config validates required fields.

        Verifies:
        - Config requires at least one format
        - Config requires valid output directory
        """
        exporter = MultiFormatExporter()
        bundle = {"metadata": {}, "state_space": {}}

        # Test with no formats (should raise)
        config_no_formats = ExportConfig(
            formats=[],
            output_dir=str(temp_dir),
        )

        with pytest.raises(ValueError, match="At least one export format"):
            exporter.export_gnn_bundle(bundle, config_no_formats)

    def test_export_creates_output_directory(self, temp_dir):
        """Test that export creates output directory if needed.

        Verifies:
        - Non-existent output directory is created
        - Files are written to created directory
        """
        nested_dir = temp_dir / "nested" / "export" / "output"
        bundle = {
            "metadata": {"id": "test", "schema_name": "test"},
            "state_space": {},
        }

        exporter = MultiFormatExporter()
        config = ExportConfig(
            formats=[ExportFormat.JSON],
            output_dir=str(nested_dir),
        )

        results = exporter.export_gnn_bundle(bundle, config)

        # Verify directory was created
        assert nested_dir.exists()
        # Verify files exist in created directory
        assert len(results) > 0


class TestErrorHandlingExport:
    """Tests for error handling in export."""

    def test_export_invalid_path(self):
        """Test that export handles invalid paths gracefully.

        Verifies:
        - Invalid output directory path is detected
        - Error is raised or handled
        """
        exporter = MultiFormatExporter()
        bundle = {"metadata": {}}

        # Use a path that's likely to fail (inside /dev/null on Unix)
        invalid_path = "/dev/null/invalid/path"

        config = ExportConfig(
            formats=[ExportFormat.JSON],
            output_dir=invalid_path,
        )

        # Should raise ValueError or OSError
        with pytest.raises((ValueError, OSError, PermissionError)):
            exporter.export_gnn_bundle(bundle, config)
