#!/usr/bin/env python3
"""Coverage boost batch 89 — static/parser.py additional paths,
static/types.py TypeInferencer, export/bundle.py helpers.

Covers:
- static/parser.py: PythonASTParser._extract_imports, _extract_assignment,
  _ast_to_str fallback paths, parse_string edge cases
- static/types.py: TypeInfo dataclass, TypeInferencer (infer_types_from_source,
  _infer_from_class, _infer_from_assign, _infer_from_annassign,
  _annotation_to_str, _safe_unparse, _infer_literal_type, _infer_type_from_value,
  _call_name, _infer_function_return_type, _infer_return_from_body)
- export/bundle.py: BundleManifest, BundleExporter (_manifest_to_dict,
  _compute_checksum, _generate_html, _create_manifest), FORMATS list
"""

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# static/parser.py — additional path coverage
# ---------------------------------------------------------------------------


class TestPythonASTParserAdditional:
    def _make_parser(self):
        from cogant.static.parser import PythonASTParser

        return PythonASTParser()

    def test_parse_string_empty(self):
        parser = self._make_parser()
        result = parser.parse_string("", Path("empty.py"))
        assert result is not None

    def test_parse_string_with_imports(self):
        parser = self._make_parser()
        src = "import os\nimport sys\nfrom pathlib import Path\n"
        result = parser.parse_string(src, Path("imports.py"))
        assert result is not None
        assert len(result.imports) >= 2

    def test_parse_string_with_relative_import(self):
        parser = self._make_parser()
        src = "from .utils import helper\nfrom ..base import Base\n"
        result = parser.parse_string(src, Path("module.py"))
        assert result is not None

    def test_parse_string_with_assignments(self):
        parser = self._make_parser()
        src = "MAX_RETRIES = 3\nDEFAULT_TIMEOUT = 30\n"
        result = parser.parse_string(src, Path("constants.py"))
        assert result is not None

    def test_parse_string_with_annotated_assignment(self):
        parser = self._make_parser()
        src = "count: int = 5\nname: str\nvalue: float = 3.14\n"
        result = parser.parse_string(src, Path("ann.py"))
        assert result is not None

    def test_parse_string_invalid_syntax_returns_gracefully(self):
        parser = self._make_parser()
        result = parser.parse_string("def broken(:\n    pass", Path("bad.py"))
        # Should return a PythonModule with empty collections
        assert result is not None

    def test_extract_imports_plain_import(self):
        parser = self._make_parser()
        node = ast.parse("import os\n").body[0]
        imports = parser._extract_imports(node)
        assert len(imports) == 1
        assert imports[0].module_name == "os"
        assert imports[0].is_relative is False

    def test_extract_imports_from_import(self):
        parser = self._make_parser()
        node = ast.parse("from pathlib import Path\n").body[0]
        imports = parser._extract_imports(node)
        assert len(imports) == 1
        assert imports[0].module_name == "pathlib"

    def test_extract_imports_relative(self):
        parser = self._make_parser()
        node = ast.parse("from .utils import helper\n").body[0]
        imports = parser._extract_imports(node)
        assert len(imports) == 1
        assert imports[0].is_relative is True

    def test_extract_assignment_simple(self):
        parser = self._make_parser()
        node = ast.parse("x = 42\n").body[0]
        result = parser._extract_assignment(node)
        assert result is not None
        assert result.target_name == "x"

    def test_extract_assignment_annotated(self):
        parser = self._make_parser()
        node = ast.parse("count: int = 5\n").body[0]
        result = parser._extract_assignment(node)
        assert result is not None
        assert result.target_name == "count"
        assert result.annotation is not None

    def test_extract_assignment_annotated_no_value(self):
        parser = self._make_parser()
        node = ast.parse("name: str\n").body[0]
        result = parser._extract_assignment(node)
        assert result is not None
        assert result.target_name == "name"

    def test_ast_to_str_name_node(self):
        from cogant.static.parser import PythonASTParser

        node = ast.Name(id="my_var", ctx=ast.Load())
        result = PythonASTParser._ast_to_str(node)
        assert "my_var" in result

    def test_ast_to_str_constant_node(self):
        from cogant.static.parser import PythonASTParser

        node = ast.Constant(value=42)
        result = PythonASTParser._ast_to_str(node)
        assert isinstance(result, str)

    def test_ast_to_str_attribute_node(self):
        from cogant.static.parser import PythonASTParser

        value = ast.Name(id="self", ctx=ast.Load())
        node = ast.Attribute(value=value, attr="data", ctx=ast.Load())
        result = PythonASTParser._ast_to_str(node)
        assert "data" in result

    def test_parse_file_nonexistent(self):
        parser = self._make_parser()
        result = parser.parse_file(Path("/nonexistent/path/missing.py"))
        assert result is not None

    def test_parse_string_with_function(self):
        parser = self._make_parser()
        src = "def process(data: list) -> dict:\n    return {}\n"
        result = parser.parse_string(src, Path("proc.py"))
        assert result is not None
        assert len(result.functions) >= 1

    def test_parse_string_with_class(self):
        parser = self._make_parser()
        src = (
            "class MyClass:\n    value: int = 0\n    def method(self):\n        return self.value\n"
        )
        result = parser.parse_string(src, Path("cls.py"))
        assert result is not None
        assert len(result.classes) >= 1


# ---------------------------------------------------------------------------
# static/types.py — TypeInfo and TypeInferencer
# ---------------------------------------------------------------------------


class TestTypeInfo:
    def test_type_info_basic(self):
        from cogant.static.types import TypeInfo

        ti = TypeInfo(
            symbol_id="sym_001",
            symbol_name="my_var",
            symbol_kind="variable",
            inferred_type="int",
        )
        assert ti.symbol_name == "my_var"
        assert ti.inferred_type == "int"
        assert ti.symbol_kind == "variable"

    def test_type_info_optional_fields(self):
        from cogant.static.types import TypeInfo

        ti = TypeInfo(
            symbol_id="sym_002",
            symbol_name="func",
            symbol_kind="function",
            inferred_type="Callable",
            annotation="Callable[[int], str]",
            confidence=0.9,
            is_mutable=False,
        )
        assert ti.annotation == "Callable[[int], str]"
        assert ti.confidence == 0.9
        assert ti.is_mutable is False


class TestTypeInferencer:
    def _make_inferencer(self):
        from cogant.static.types import TypeInferencer

        return TypeInferencer()

    def test_init(self):
        inferencer = self._make_inferencer()
        assert inferencer is not None

    def test_infer_from_source_empty(self, tmp_path):
        inferencer = self._make_inferencer()
        results = inferencer.infer_types_from_source("", tmp_path / "empty.py")
        assert isinstance(results, list)

    def test_infer_from_source_with_function(self, tmp_path):
        inferencer = self._make_inferencer()
        src = "def add(a: int, b: int) -> int:\n    return a + b\n"
        fp = tmp_path / "add.py"
        results = inferencer.infer_types_from_source(src, fp)
        assert isinstance(results, list)

    def test_infer_from_source_with_class(self, tmp_path):
        inferencer = self._make_inferencer()
        src = """
class Counter:
    count: int = 0

    def __init__(self, start: int = 0) -> None:
        self.count = start

    def increment(self) -> None:
        self.count += 1

    def get(self) -> int:
        return self.count
"""
        fp = tmp_path / "counter.py"
        results = inferencer.infer_types_from_source(src, fp)
        assert isinstance(results, list)

    def test_infer_from_source_invalid_syntax(self, tmp_path):
        inferencer = self._make_inferencer()
        results = inferencer.infer_types_from_source("def broken(:", tmp_path / "bad.py")
        assert results == []

    def test_infer_from_file_nonexistent(self, tmp_path):
        inferencer = self._make_inferencer()
        results = inferencer.infer_types_from_file(tmp_path / "missing.py")
        assert isinstance(results, list)
        assert results == []

    def test_annotation_to_str_name(self):
        from cogant.static.types import TypeInferencer

        node = ast.Name(id="int", ctx=ast.Load())
        result = TypeInferencer._annotation_to_str(node)
        assert result == "int"

    def test_annotation_to_str_none(self):
        from cogant.static.types import TypeInferencer

        result = TypeInferencer._annotation_to_str(None)
        assert result is None

    def test_safe_unparse_name(self):
        from cogant.static.types import TypeInferencer

        node = ast.Name(id="my_var", ctx=ast.Load())
        result = TypeInferencer._safe_unparse(node)
        assert "my_var" in (result or "")

    def test_safe_unparse_none(self):
        from cogant.static.types import TypeInferencer

        result = TypeInferencer._safe_unparse(None)
        assert result is None

    def test_infer_type_from_value_int(self):
        from cogant.static.types import TypeInferencer

        result = TypeInferencer._infer_type_from_value("42")
        assert result == "int"

    def test_infer_type_from_value_float(self):
        from cogant.static.types import TypeInferencer

        result = TypeInferencer._infer_type_from_value("3.14")
        assert result == "float"

    def test_infer_type_from_value_string(self):
        from cogant.static.types import TypeInferencer

        result = TypeInferencer._infer_type_from_value("'hello'")
        assert result == "str"

    def test_infer_type_from_value_true(self):
        from cogant.static.types import TypeInferencer

        result = TypeInferencer._infer_type_from_value("True")
        assert result == "bool"

    def test_infer_type_from_value_none(self):
        from cogant.static.types import TypeInferencer

        result = TypeInferencer._infer_type_from_value(None)
        assert result is None

    def test_infer_type_from_value_list(self):
        from cogant.static.types import TypeInferencer

        result = TypeInferencer._infer_type_from_value("[1, 2, 3]")
        assert result == "list"

    def test_infer_literal_type_constant_int(self, tmp_path):
        inferencer = self._make_inferencer()
        node = ast.Constant(value=42)
        result = inferencer._infer_literal_type(node)
        assert result == "int"

    def test_infer_literal_type_constant_str(self, tmp_path):
        inferencer = self._make_inferencer()
        node = ast.Constant(value="hello")
        result = inferencer._infer_literal_type(node)
        assert result == "str"

    def test_infer_literal_type_none_node(self, tmp_path):
        inferencer = self._make_inferencer()
        result = inferencer._infer_literal_type(None)
        assert result is None

    def test_infer_from_source_with_assignments(self, tmp_path):
        inferencer = self._make_inferencer()
        src = "MAX: int = 100\nNAME: str = 'test'\nFLAG = True\n"
        fp = tmp_path / "consts.py"
        results = inferencer.infer_types_from_source(src, fp)
        assert isinstance(results, list)


# ---------------------------------------------------------------------------
# export/bundle.py — BundleManifest and helper methods
# ---------------------------------------------------------------------------


class TestBundleManifest:
    def test_basic_creation(self):
        from datetime import datetime

        from cogant.export.bundle import BundleManifest

        manifest = BundleManifest(
            bundle_id="bundle_test",
            schema_name="test_schema",
            created_at=datetime.now(),
            files={"model.json": "GNN JSON model"},
            checksums={"model.json": "abc123"},
            metadata={"node_count": 5},
        )
        assert manifest.bundle_id == "bundle_test"
        assert manifest.schema_name == "test_schema"
        assert "model.json" in manifest.files


class TestBundleExporterHelpers:
    def _make_exporter(self, tmp_path):
        from cogant.export.bundle import BundleExporter
        from cogant.process.extractor import ProcessModel
        from cogant.schemas.graph import GraphMetadata, ProgramGraph
        from cogant.statespace.compiler import StateSpaceModel
        from cogant.statespace.temporal import TimeRegime

        graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///test"))
        ss = StateSpaceModel(
            id="ss1",
            schema_name="test",
            variables={},
            observations={},
            actions={},
            transitions={},
            likelihoods={},
            preferences={},
            time_regime=TimeRegime.SYNCHRONOUS,
        )
        pm = ProcessModel(id="pm1", schema_name="test", stages={}, connections={})
        return BundleExporter(
            program_graph=graph,
            state_space_model=ss,
            process_model=pm,
            semantic_mappings={},
            output_dir=tmp_path,
        )

    def test_formats_list(self):
        from cogant.export.bundle import BundleExporter

        assert "markdown" in BundleExporter.FORMATS
        assert "json" in BundleExporter.FORMATS

    def test_manifest_to_dict(self, tmp_path):
        from datetime import datetime

        from cogant.export.bundle import BundleManifest

        exporter = self._make_exporter(tmp_path)
        manifest = BundleManifest(
            bundle_id="b1",
            schema_name="test",
            created_at=datetime(2024, 1, 1),
            files={"a.json": "description"},
            checksums={"a.json": "hash"},
            metadata={"count": 3},
        )
        d = exporter._manifest_to_dict(manifest)
        assert d["bundle_id"] == "b1"
        assert "files" in d
        assert "checksums" in d
        assert "metadata" in d

    def test_create_manifest(self, tmp_path):
        exporter = self._make_exporter(tmp_path)
        files = {"model.json": "GNN JSON"}
        checksums = {"model.json": "deadbeef"}
        manifest = exporter._create_manifest(files, checksums)
        assert manifest.bundle_id.startswith("bundle_")
        assert manifest.schema_name == "test"
        assert manifest.files == files

    def test_generate_html_returns_string(self, tmp_path):
        exporter = self._make_exporter(tmp_path)
        result = exporter._generate_html()
        assert isinstance(result, str)
        assert "<html>" in result.lower() or "html" in result.lower()

    def test_compute_checksum_basic(self, tmp_path):
        exporter = self._make_exporter(tmp_path)
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        result = exporter._compute_checksum(f)
        assert isinstance(result, str)
        assert len(result) == 64
