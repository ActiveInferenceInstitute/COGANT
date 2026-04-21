"""Unit tests for JSON schema export module."""

import pytest

from cogant.export.json_schema import JSONSchemaExporter


@pytest.mark.unit
class TestJSONSchemaExporter:
    """Test JSONSchemaExporter."""

    def test_exporter_creation(self) -> None:
        """Test creating a JSONSchemaExporter."""
        exporter = JSONSchemaExporter()
        assert exporter is not None

    def test_export_gnn_bundle_schema(self) -> None:
        """Test exporting GNN bundle schema."""
        exporter = JSONSchemaExporter()
        schema = exporter.export_gnn_bundle_schema()

        assert isinstance(schema, dict)
        assert "$schema" in schema
        assert "http://json-schema.org/draft-07/schema#" == schema["$schema"]
        assert "type" in schema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "metadata" in schema["properties"]
        assert "state_space" in schema["properties"]
        assert "matrices" in schema["properties"]

    def test_gnn_bundle_schema_has_matrices(self) -> None:
        """Test that GNN bundle schema includes all matrix properties."""
        exporter = JSONSchemaExporter()
        schema = exporter.export_gnn_bundle_schema()

        matrices_props = schema["properties"]["matrices"]["properties"]
        assert "A" in matrices_props
        assert "B" in matrices_props
        assert "C" in matrices_props
        assert "D" in matrices_props

    def test_export_program_graph_schema(self) -> None:
        """Test exporting program graph schema."""
        exporter = JSONSchemaExporter()
        schema = exporter.export_program_graph_schema()

        assert isinstance(schema, dict)
        assert "$schema" in schema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "metadata" in schema["properties"]
        assert "nodes" in schema["properties"]
        assert "edges" in schema["properties"]

    def test_program_graph_schema_node_properties(self) -> None:
        """Test that program graph schema includes node properties."""
        exporter = JSONSchemaExporter()
        schema = exporter.export_program_graph_schema()

        nodes_items = schema["properties"]["nodes"]["items"]
        assert "required" in nodes_items
        assert "id" in nodes_items["required"]
        assert "kind" in nodes_items["required"]

    def test_program_graph_schema_edge_properties(self) -> None:
        """Test that program graph schema includes edge properties."""
        exporter = JSONSchemaExporter()
        schema = exporter.export_program_graph_schema()

        edges_items = schema["properties"]["edges"]["items"]
        assert "required" in edges_items
        assert "id" in edges_items["required"]
        assert "source_id" in edges_items["required"]
        assert "target_id" in edges_items["required"]

    def test_export_semantic_mappings_schema(self) -> None:
        """Test exporting semantic mappings schema."""
        exporter = JSONSchemaExporter()
        schema = exporter.export_semantic_mappings_schema()

        assert isinstance(schema, dict)
        assert "$schema" in schema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "mappings" in schema["properties"]

    def test_semantic_mappings_schema_structure(self) -> None:
        """Test semantic mappings schema structure."""
        exporter = JSONSchemaExporter()
        schema = exporter.export_semantic_mappings_schema()

        mappings_props = schema["properties"]["mappings"]
        assert "additionalProperties" in mappings_props
        assert mappings_props["additionalProperties"]["required"]

    def test_export_pipeline_result_schema(self) -> None:
        """Test exporting pipeline result schema."""
        exporter = JSONSchemaExporter()
        schema = exporter.export_pipeline_result_schema()

        assert isinstance(schema, dict)
        assert "$schema" in schema
        assert schema["type"] == "object"
        assert "properties" in schema

    def test_all_schemas_are_objects(self) -> None:
        """Test that all exported schemas are objects."""
        exporter = JSONSchemaExporter()

        schemas = [
            exporter.export_gnn_bundle_schema(),
            exporter.export_program_graph_schema(),
            exporter.export_semantic_mappings_schema(),
            exporter.export_pipeline_result_schema(),
        ]

        for schema in schemas:
            assert schema["type"] == "object"

    def test_all_schemas_have_schema_field(self) -> None:
        """Test that all schemas declare their JSON Schema version."""
        exporter = JSONSchemaExporter()

        schemas = [
            exporter.export_gnn_bundle_schema(),
            exporter.export_program_graph_schema(),
            exporter.export_semantic_mappings_schema(),
            exporter.export_pipeline_result_schema(),
        ]

        for schema in schemas:
            assert "$schema" in schema
            assert "http://json-schema.org/draft-07/schema#" == schema["$schema"]

    def test_gnn_bundle_schema_example(self) -> None:
        """Test that GNN bundle schema includes example."""
        exporter = JSONSchemaExporter()
        schema = exporter.export_gnn_bundle_schema()

        assert "example" in schema
        assert "metadata" in schema["example"]
        assert "state_space" in schema["example"]
        assert "matrices" in schema["example"]

    def test_semantic_mappings_schema_example(self) -> None:
        """Test that semantic mappings schema includes example."""
        exporter = JSONSchemaExporter()
        schema = exporter.export_semantic_mappings_schema()

        assert "example" in schema
        assert "mappings" in schema["example"]
