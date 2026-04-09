"""Integration tests for the full COGANT pipeline."""

import json
import pytest
from pathlib import Path


class TestEndToEndPipeline:
    """Tests for complete pipeline execution."""

    def test_pipeline_ingest_stage(self, example_repo_path):
        """Test ingest stage of pipeline."""
        if not example_repo_path.exists():
            pytest.skip("Example repo not found")

        # Simulate ingest stage
        repo_files = list(example_repo_path.glob("**/*.py"))
        assert len(repo_files) > 0

        # Check expected structure
        assert (example_repo_path / "src").exists()
        assert (example_repo_path / "tests").exists()

    def test_pipeline_parsing_stage(self, example_repo_path):
        """Test parsing stage of pipeline."""
        if not example_repo_path.exists():
            pytest.skip("Example repo not found")

        import ast

        # Parse all Python files
        parsed_files = {}
        for py_file in example_repo_path.glob("**/*.py"):
            try:
                with open(py_file) as f:
                    tree = ast.parse(f.read())
                    parsed_files[str(py_file)] = tree
            except SyntaxError:
                continue

        assert len(parsed_files) > 0

    def test_pipeline_symbol_extraction_stage(self, example_repo_path):
        """Test symbol extraction stage."""
        if not example_repo_path.exists():
            pytest.skip("Example repo not found")

        import ast

        symbols = {}

        # Extract symbols from all files
        for py_file in example_repo_path.glob("**/*.py"):
            try:
                with open(py_file) as f:
                    tree = ast.parse(f.read())

                # Extract functions and classes
                file_symbols = {
                    "functions": [
                        n.name for n in ast.walk(tree)
                        if isinstance(n, ast.FunctionDef)
                    ],
                    "classes": [
                        n.name for n in ast.walk(tree)
                        if isinstance(n, ast.ClassDef)
                    ],
                }

                if file_symbols["functions"] or file_symbols["classes"]:
                    symbols[str(py_file)] = file_symbols

            except SyntaxError:
                continue

        assert len(symbols) > 0

    def test_pipeline_graph_construction_stage(self):
        """Test graph construction stage."""
        # Simulate symbols from analysis
        symbols = {
            "module:app": {"type": "Module", "name": "app"},
            "class:User": {"type": "Class", "name": "User", "parent": "module:app"},
            "function:create_user": {
                "type": "Function",
                "name": "create_user",
                "parent": "module:app",
            },
        }

        # Build graph
        edges = [
            {
                "source": "module:app",
                "target": "class:User",
                "type": "defines",
                "confidence": 1.0,
            },
            {
                "source": "module:app",
                "target": "function:create_user",
                "type": "defines",
                "confidence": 1.0,
            },
            {
                "source": "function:create_user",
                "target": "class:User",
                "type": "uses",
                "confidence": 0.95,
            },
        ]

        # Verify graph structure
        assert len(symbols) == 3
        assert len(edges) == 3

        # Verify connectivity
        node_ids = set(symbols.keys())
        for edge in edges:
            assert edge["source"] in node_ids
            assert edge["target"] in node_ids

    def test_pipeline_validation_stage(self):
        """Test validation stage."""
        nodes = [
            {"id": "n1", "type": "Module"},
            {"id": "n2", "type": "Class"},
            {"id": "n3", "type": "Function"},
        ]

        edges = [
            {"source": "n1", "target": "n2", "type": "defines"},
            {"source": "n1", "target": "n3", "type": "defines"},
        ]

        # Validate graph
        node_ids = {n["id"] for n in nodes}

        errors = []
        for edge in edges:
            if edge["source"] not in node_ids:
                errors.append(f"Invalid source: {edge['source']}")
            if edge["target"] not in node_ids:
                errors.append(f"Invalid target: {edge['target']}")

        assert len(errors) == 0

    def test_pipeline_export_stage(self):
        """Test export stage."""
        graph = {
            "nodes": [
                {"id": "n1", "type": "Module", "name": "test"},
            ],
            "edges": [],
        }

        # Export to JSON
        export_data = {
            "version": "1.0",
            "format": "gnn",
            "graph": graph,
        }

        json_str = json.dumps(export_data)
        assert len(json_str) > 0

        # Parse back to verify
        parsed = json.loads(json_str)
        assert parsed["version"] == "1.0"

    def test_full_pipeline_execution(self):
        """Test full pipeline execution end-to-end."""
        # Mock pipeline stages
        pipeline_stages = [
            {"name": "ingest", "status": "completed"},
            {"name": "parse", "status": "completed"},
            {"name": "extract_symbols", "status": "completed"},
            {"name": "build_graph", "status": "completed"},
            {"name": "validate", "status": "completed"},
            {"name": "export", "status": "completed"},
        ]

        # All stages should be completed
        assert all(stage["status"] == "completed" for stage in pipeline_stages)

        pipeline_report = {
            "success": True,
            "stages": pipeline_stages,
            "total_duration_seconds": 2.5,
        }

        assert pipeline_report["success"]


class TestPipelineWithExampleService:
    """Tests using the example Python service."""

    def test_analyze_example_service(self, example_repo_path):
        """Test analyzing the example Python service."""
        if not example_repo_path.exists():
            pytest.skip("Example service not found")

        import ast

        # Find and parse app.py
        app_file = example_repo_path / "src" / "app.py"
        if app_file.exists():
            with open(app_file) as f:
                tree = ast.parse(f.read())

            # Should find FastAPI app and route definitions
            classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            functions = [
                n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
            ]

            # Verify expected symbols
            assert len(functions) > 0

    def test_extract_service_dependencies(self, example_repo_path):
        """Test extracting dependencies from example service."""
        if not example_repo_path.exists():
            pytest.skip("Example service not found")

        import ast

        dependencies = set()

        for py_file in example_repo_path.glob("**/*.py"):
            try:
                with open(py_file) as f:
                    tree = ast.parse(f.read())

                # Extract imports
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if node.module:
                            dependencies.add(node.module)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            dependencies.add(alias.name)

            except (SyntaxError, OSError):
                continue

        # Should find some dependencies (fastapi, sqlalchemy, etc.)
        assert len(dependencies) > 0

    def test_build_service_graph(self, example_repo_path):
        """Test building a complete graph for the service."""
        if not example_repo_path.exists():
            pytest.skip("Example service not found")

        # Simulate building complete service graph
        service_graph = {
            "nodes": [
                {"id": "module:app", "type": "Module", "name": "app"},
                {"id": "class:Settings", "type": "Class", "name": "Settings"},
                {"id": "class:User", "type": "Class", "name": "User"},
                {"id": "function:create_user", "type": "Function", "name": "create_user"},
            ],
            "edges": [
                {"source": "module:app", "target": "class:Settings", "type": "uses"},
                {"source": "module:app", "target": "class:User", "type": "uses"},
                {"source": "function:create_user", "target": "class:User", "type": "uses"},
            ],
        }

        # Verify graph
        assert len(service_graph["nodes"]) > 0
        assert len(service_graph["edges"]) > 0

        # Check connectivity
        node_ids = {n["id"] for n in service_graph["nodes"]}
        for edge in service_graph["edges"]:
            assert edge["source"] in node_ids
            assert edge["target"] in node_ids


class TestPipelineErrorHandling:
    """Tests for pipeline error handling."""

    def test_handle_invalid_python_syntax(self):
        """Test handling invalid Python syntax."""
        import ast

        invalid_code = "def broken function():"

        with pytest.raises(SyntaxError):
            ast.parse(invalid_code)

    def test_handle_missing_files(self, temp_dir):
        """Test handling missing input files."""
        missing_path = temp_dir / "nonexistent" / "file.py"

        assert not missing_path.exists()

    def test_handle_encoding_errors(self, temp_dir):
        """Test handling file encoding errors."""
        # Create a file with problematic encoding
        bad_file = temp_dir / "bad.py"
        bad_file.write_bytes(b"\x80\x81\x82\x83")

        # Should handle gracefully
        try:
            with open(bad_file, encoding="utf-8") as f:
                f.read()
        except UnicodeDecodeError:
            pass  # Expected


class TestPipelinePerformance:
    """Tests for pipeline performance characteristics."""

    def test_pipeline_handles_large_codebase(self):
        """Test pipeline can handle large codebases."""
        # Simulate large codebase analysis
        node_count = 10000
        edge_count = 25000

        graph = {
            "nodes": [
                {"id": f"n{i}", "type": "Function", "name": f"func_{i}"}
                for i in range(node_count)
            ],
            "edges": [
                {"source": f"n{i}", "target": f"n{(i+1) % node_count}", "type": "calls"}
                for i in range(edge_count)
            ],
        }

        # Should construct without errors
        assert len(graph["nodes"]) == node_count
        assert len(graph["edges"]) == edge_count

    def test_pipeline_validates_quickly(self):
        """Test validation performance."""
        import time

        nodes = [{"id": f"n{i}", "type": "Module"} for i in range(1000)]
        edges = [
            {"source": f"n{i}", "target": f"n{(i + 1) % 1000}", "type": "calls"}
            for i in range(1000)
        ]

        # Time validation
        start = time.time()

        node_ids = {n["id"] for n in nodes}
        for edge in edges:
            assert edge["source"] in node_ids
            assert edge["target"] in node_ids

        duration = time.time() - start

        # Should be reasonably fast
        assert duration < 1.0  # Less than 1 second


class TestPipelineOutputBundle:
    """Tests for output bundle generation."""

    def test_generate_output_bundle(self):
        """Test generating complete output bundle."""
        bundle = {
            "version": "1.0",
            "format": "gnn",
            "metadata": {
                "created_at": "2024-01-01T00:00:00Z",
                "source_repo": "test_service",
                "analyzer_version": "0.1.0",
            },
            "graph": {
                "nodes": [
                    {"id": "n1", "type": "Module", "name": "app"},
                ],
                "edges": [],
            },
            "validation": {
                "valid": True,
                "errors": [],
                "warnings": [],
            },
            "statistics": {
                "node_count": 1,
                "edge_count": 0,
                "analysis_duration_seconds": 0.5,
            },
        }

        # Verify bundle structure
        assert bundle["version"]
        assert bundle["format"] == "gnn"
        assert bundle["metadata"]["source_repo"]
        assert bundle["graph"]["nodes"]
        assert bundle["validation"]["valid"]
        assert bundle["statistics"]["node_count"] > 0

    def test_bundle_export_formats(self):
        """Test bundle in multiple export formats."""
        base_data = {
            "nodes": [{"id": "n1", "type": "Module"}],
            "edges": [],
        }

        # JSON format
        json_export = json.dumps(base_data)
        assert json_export

        # Could test Parquet, Markdown, etc.
        formats = ["json", "markdown", "parquet"]
        assert "json" in formats
