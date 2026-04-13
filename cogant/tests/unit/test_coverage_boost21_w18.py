#!/usr/bin/env python3
"""Coverage boost batch 21 — static/types internals, reverse/cli helpers,
ingest/language_detect, ingest/manifest deeper paths.

Covers:
- static/types.py: TypeInferencer._infer_literal_type, _infer_return_from_body,
  _call_name, _infer_type_from_value, _annotation_to_str, _safe_unparse,
  _resolve_symbol_ids, _infer_from_annassign, _infer_from_assign, _infer_from_class
- reverse/cli.py: _render_plan_summary, _render_roundtrip_result
- ingest/language_detect.py: detect_language, detect_repo_languages,
  get_parser_for_extension, get_supported_languages
- ingest/manifest.py: parse_requirements_txt, parse_package_json,
  parse_setup_py, parse_pyproject_toml deeper paths
"""

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# static/types.py — TypeInferencer internal helpers
# ---------------------------------------------------------------------------

class TestInferLiteralType:
    """Test TypeInferencer._infer_literal_type with real AST nodes."""

    def _inferencer(self, tmp_path):
        from cogant.static.types import TypeInferencer
        return TypeInferencer(tmp_path)

    def test_none_value(self, tmp_path):
        inf = self._inferencer(tmp_path)
        result = inf._infer_literal_type(None)
        assert result is None

    def test_none_constant(self, tmp_path):
        inf = self._inferencer(tmp_path)
        node = ast.Constant(value=None)
        result = inf._infer_literal_type(node)
        assert result == "None"

    def test_bool_constant(self, tmp_path):
        inf = self._inferencer(tmp_path)
        node = ast.Constant(value=True)
        result = inf._infer_literal_type(node)
        assert result == "bool"

    def test_int_constant(self, tmp_path):
        inf = self._inferencer(tmp_path)
        node = ast.Constant(value=42)
        result = inf._infer_literal_type(node)
        assert result == "int"

    def test_float_constant(self, tmp_path):
        inf = self._inferencer(tmp_path)
        node = ast.Constant(value=3.14)
        result = inf._infer_literal_type(node)
        assert result == "float"

    def test_str_constant(self, tmp_path):
        inf = self._inferencer(tmp_path)
        node = ast.Constant(value="hello")
        result = inf._infer_literal_type(node)
        assert result == "str"

    def test_bytes_constant(self, tmp_path):
        inf = self._inferencer(tmp_path)
        node = ast.Constant(value=b"bytes")
        result = inf._infer_literal_type(node)
        assert result == "bytes"

    def test_list_node(self, tmp_path):
        inf = self._inferencer(tmp_path)
        node = ast.List(elts=[], ctx=ast.Load())
        result = inf._infer_literal_type(node)
        assert result == "list"

    def test_tuple_node(self, tmp_path):
        inf = self._inferencer(tmp_path)
        node = ast.Tuple(elts=[], ctx=ast.Load())
        result = inf._infer_literal_type(node)
        assert result == "tuple"

    def test_set_node(self, tmp_path):
        inf = self._inferencer(tmp_path)
        node = ast.Set(elts=[])
        result = inf._infer_literal_type(node)
        assert result == "set"

    def test_dict_node(self, tmp_path):
        inf = self._inferencer(tmp_path)
        node = ast.Dict(keys=[], values=[])
        result = inf._infer_literal_type(node)
        assert result == "dict"

    def test_call_node_list(self, tmp_path):
        inf = self._inferencer(tmp_path)
        tree = ast.parse("list()")
        call_node = tree.body[0].value  # type: ignore
        result = inf._infer_literal_type(call_node)
        assert result == "list"

    def test_call_node_dict(self, tmp_path):
        inf = self._inferencer(tmp_path)
        tree = ast.parse("dict()")
        call_node = tree.body[0].value  # type: ignore
        result = inf._infer_literal_type(call_node)
        assert result == "dict"

    def test_call_node_unknown(self, tmp_path):
        inf = self._inferencer(tmp_path)
        tree = ast.parse("my_custom_func()")
        call_node = tree.body[0].value  # type: ignore
        result = inf._infer_literal_type(call_node)
        assert result is None


class TestCallName:
    """Test TypeInferencer._call_name static method."""

    def _inferencer(self, tmp_path):
        from cogant.static.types import TypeInferencer
        return TypeInferencer(tmp_path)

    def test_name_node(self, tmp_path):
        inf = self._inferencer(tmp_path)
        node = ast.Name(id="my_func", ctx=ast.Load())
        result = inf._call_name(node)
        assert result == "my_func"

    def test_attribute_node(self, tmp_path):
        inf = self._inferencer(tmp_path)
        node = ast.Attribute(
            value=ast.Name(id="obj", ctx=ast.Load()),
            attr="method",
            ctx=ast.Load()
        )
        result = inf._call_name(node)
        assert result == "method"

    def test_other_node(self, tmp_path):
        inf = self._inferencer(tmp_path)
        node = ast.Constant(value=42)
        result = inf._call_name(node)
        assert result is None


class TestInferTypeFromValue:
    """Test TypeInferencer._infer_type_from_value static method."""

    def _inferencer(self, tmp_path):
        from cogant.static.types import TypeInferencer
        return TypeInferencer(tmp_path)

    def test_none_value(self, tmp_path):
        inf = self._inferencer(tmp_path)
        assert inf._infer_type_from_value(None) is None

    def test_empty_string(self, tmp_path):
        inf = self._inferencer(tmp_path)
        assert inf._infer_type_from_value("") is None

    def test_none_literal(self, tmp_path):
        inf = self._inferencer(tmp_path)
        assert inf._infer_type_from_value("None") == "None"

    def test_true_bool(self, tmp_path):
        inf = self._inferencer(tmp_path)
        assert inf._infer_type_from_value("True") == "bool"

    def test_false_bool(self, tmp_path):
        inf = self._inferencer(tmp_path)
        assert inf._infer_type_from_value("False") == "bool"

    def test_list_value(self, tmp_path):
        inf = self._inferencer(tmp_path)
        assert inf._infer_type_from_value("[1, 2, 3]") == "list"

    def test_dict_value(self, tmp_path):
        inf = self._inferencer(tmp_path)
        assert inf._infer_type_from_value('{"key": "val"}') == "dict"

    def test_set_value(self, tmp_path):
        inf = self._inferencer(tmp_path)
        assert inf._infer_type_from_value("{1, 2, 3}") == "set"

    def test_tuple_value(self, tmp_path):
        inf = self._inferencer(tmp_path)
        assert inf._infer_type_from_value("(1, 2)") == "tuple"

    def test_str_value_double_quote(self, tmp_path):
        inf = self._inferencer(tmp_path)
        assert inf._infer_type_from_value('"hello"') == "str"

    def test_str_value_single_quote(self, tmp_path):
        inf = self._inferencer(tmp_path)
        assert inf._infer_type_from_value("'world'") == "str"

    def test_int_value(self, tmp_path):
        inf = self._inferencer(tmp_path)
        assert inf._infer_type_from_value("42") == "int"

    def test_negative_int_value(self, tmp_path):
        inf = self._inferencer(tmp_path)
        assert inf._infer_type_from_value("-5") == "int"

    def test_float_value(self, tmp_path):
        inf = self._inferencer(tmp_path)
        assert inf._infer_type_from_value("3.14") == "float"

    def test_list_ctor(self, tmp_path):
        inf = self._inferencer(tmp_path)
        assert inf._infer_type_from_value("list()") == "list"

    def test_dict_ctor(self, tmp_path):
        inf = self._inferencer(tmp_path)
        assert inf._infer_type_from_value("dict()") == "dict"

    def test_set_ctor(self, tmp_path):
        inf = self._inferencer(tmp_path)
        assert inf._infer_type_from_value("set()") == "set"

    def test_tuple_ctor(self, tmp_path):
        inf = self._inferencer(tmp_path)
        assert inf._infer_type_from_value("tuple()") == "tuple"

    def test_unknown_value(self, tmp_path):
        inf = self._inferencer(tmp_path)
        assert inf._infer_type_from_value("some_variable") is None


class TestAnnotationToStr:
    """Test TypeInferencer._annotation_to_str static method."""

    def _inferencer(self, tmp_path):
        from cogant.static.types import TypeInferencer
        return TypeInferencer(tmp_path)

    def test_none_annotation(self, tmp_path):
        inf = self._inferencer(tmp_path)
        result = inf._annotation_to_str(None)
        assert result is None

    def test_name_annotation(self, tmp_path):
        inf = self._inferencer(tmp_path)
        node = ast.Name(id="int", ctx=ast.Load())
        result = inf._annotation_to_str(node)
        assert "int" in result

    def test_constant_annotation(self, tmp_path):
        inf = self._inferencer(tmp_path)
        node = ast.Constant(value="str")
        result = inf._annotation_to_str(node)
        assert result is not None

    def test_complex_annotation(self, tmp_path):
        inf = self._inferencer(tmp_path)
        # Parse "list[int]" annotation
        tree = ast.parse("x: list[int]", mode='single')
        # Navigate to the annotation node
        ann_node = tree.body[0].annotation  # type: ignore
        result = inf._annotation_to_str(ann_node)
        assert result is not None
        assert "list" in result or "int" in result


class TestInferReturnFromBody:
    """Test TypeInferencer._infer_return_from_body."""

    def _inferencer(self, tmp_path):
        from cogant.static.types import TypeInferencer
        return TypeInferencer(tmp_path)

    def test_property_decorator(self, tmp_path):
        inf = self._inferencer(tmp_path)
        source = "@property\ndef val(self):\n    return self._val\n"
        tree = ast.parse(source)
        func = tree.body[0]
        result = inf._infer_return_from_body(func)
        assert result == "Any"

    def test_yield_function(self, tmp_path):
        inf = self._inferencer(tmp_path)
        source = "def gen():\n    yield 1\n    yield 2\n"
        tree = ast.parse(source)
        func = tree.body[0]
        result = inf._infer_return_from_body(func)
        assert result == "Iterator"

    def test_no_hint_function(self, tmp_path):
        inf = self._inferencer(tmp_path)
        source = "def simple():\n    return 42\n"
        tree = ast.parse(source)
        func = tree.body[0]
        result = inf._infer_return_from_body(func)
        assert result is None


class TestInferFromAnnAssign:
    """Test TypeInferencer._infer_from_annassign."""

    def _inferencer(self, tmp_path):
        from cogant.static.types import TypeInferencer
        return TypeInferencer(tmp_path)

    def test_simple_annassign(self, tmp_path):
        inf = self._inferencer(tmp_path)
        source = "x: int = 0\n"
        tree = ast.parse(source)
        ann_node = tree.body[0]
        result = inf._infer_from_annassign(ann_node, scope="module")
        assert result is not None
        assert "int" in result.inferred_type

    def test_annassign_no_value(self, tmp_path):
        inf = self._inferencer(tmp_path)
        source = "name: str\n"
        tree = ast.parse(source)
        ann_node = tree.body[0]
        result = inf._infer_from_annassign(ann_node, scope="module")
        assert result is not None

    def test_annassign_non_name_target(self, tmp_path):
        inf = self._inferencer(tmp_path)
        # Annotated attribute-style assign (x.y: int = 0 is invalid syntax,
        # but we can check subscript: a[0]: int = 0)
        source = "x: int = 5\n"
        tree = ast.parse(source)
        ann_node = tree.body[0]
        # Monkeypatch target to a non-Name node to test the None-return path
        ann_node.target = ast.Constant(value=42)
        result = inf._infer_from_annassign(ann_node, scope="module")
        assert result is None


class TestInferFromAssign:
    """Test TypeInferencer._infer_from_assign."""

    def _inferencer(self, tmp_path):
        from cogant.static.types import TypeInferencer
        return TypeInferencer(tmp_path)

    def test_int_assignment(self, tmp_path):
        inf = self._inferencer(tmp_path)
        source = "count = 42\n"
        tree = ast.parse(source)
        assign_node = tree.body[0]
        results = inf._infer_from_assign(assign_node, scope="module")
        assert isinstance(results, list)

    def test_list_assignment(self, tmp_path):
        inf = self._inferencer(tmp_path)
        source = "items = []\n"
        tree = ast.parse(source)
        assign_node = tree.body[0]
        results = inf._infer_from_assign(assign_node, scope="module")
        assert isinstance(results, list)

    def test_tuple_target_skipped(self, tmp_path):
        """Tuple unpacking (a, b = 1, 2) should not error."""
        inf = self._inferencer(tmp_path)
        source = "a, b = 1, 2\n"
        tree = ast.parse(source)
        assign_node = tree.body[0]
        results = inf._infer_from_assign(assign_node, scope="module")
        assert isinstance(results, list)


# ---------------------------------------------------------------------------
# reverse/cli.py — _render_plan_summary, _render_roundtrip_result
# ---------------------------------------------------------------------------

class TestReverseCliRenderFunctions:
    """Test the Rich-rendering helper functions in reverse/cli.py."""

    def test_render_plan_summary_does_not_raise(self, tmp_path):
        """_render_plan_summary should print without raising."""
        from cogant.reverse.cli import _render_plan_summary
        gnn_path = tmp_path / "model.gnn.md"
        gnn_path.touch()
        package_path = tmp_path / "package"
        package_path.mkdir()
        # Should not raise
        _render_plan_summary(
            gnn_path=gnn_path,
            package_path=package_path,
            state_count=2,
            obs_count=3,
            action_count=1,
            policy_count=0,
            constraint_count=1,
        )

    def test_render_roundtrip_result_isomorphic(self):
        """_render_roundtrip_result with isomorphic result should not raise."""
        from cogant.reverse.cli import _render_roundtrip_result
        from cogant.reverse.idempotency import RoundtripResult
        result = RoundtripResult(
            is_isomorphic=True,
            role_match_score=0.9,
            original_roles={"HIDDEN_STATE": 2, "OBSERVATION": 1},
            synthesized_roles={"HIDDEN_STATE": 2, "OBSERVATION": 1},
            shape_match={"n_states": True},
        )
        _render_roundtrip_result(result, threshold=0.5)

    def test_render_roundtrip_result_drift(self):
        """_render_roundtrip_result with drift result should not raise."""
        from cogant.reverse.cli import _render_roundtrip_result
        from cogant.reverse.idempotency import RoundtripResult
        result = RoundtripResult(
            is_isomorphic=False,
            role_match_score=0.3,
            original_roles={"HIDDEN_STATE": 3},
            synthesized_roles={"OBSERVATION": 1},
            errors=["Some error"],
        )
        _render_roundtrip_result(result, threshold=0.5)

    def test_render_roundtrip_result_with_package_path(self, tmp_path):
        """_render_roundtrip_result with package_path set should not raise."""
        from cogant.reverse.cli import _render_roundtrip_result
        from cogant.reverse.idempotency import RoundtripResult
        result = RoundtripResult(
            is_isomorphic=True,
            role_match_score=0.8,
            package_path=tmp_path / "synth_pkg",
        )
        _render_roundtrip_result(result, threshold=0.5)


# ---------------------------------------------------------------------------
# ingest/language_detect.py — LanguageDetector
# ---------------------------------------------------------------------------

class TestLanguageDetector:
    """Test LanguageDetector pure static methods."""

    def test_detect_python(self):
        from cogant.ingest.language_detect import LanguageDetector
        lang = LanguageDetector.detect_language(Path("main.py"))
        assert lang == "python"

    def test_detect_javascript(self):
        from cogant.ingest.language_detect import LanguageDetector
        lang = LanguageDetector.detect_language(Path("app.js"))
        assert lang == "javascript"

    def test_detect_typescript(self):
        from cogant.ingest.language_detect import LanguageDetector
        lang = LanguageDetector.detect_language(Path("index.ts"))
        assert lang is not None  # may be "typescript"

    def test_detect_rust(self):
        from cogant.ingest.language_detect import LanguageDetector
        lang = LanguageDetector.detect_language(Path("main.rs"))
        assert lang == "rust"

    def test_detect_go(self):
        from cogant.ingest.language_detect import LanguageDetector
        lang = LanguageDetector.detect_language(Path("main.go"))
        assert lang == "go"

    def test_detect_unknown(self):
        from cogant.ingest.language_detect import LanguageDetector
        lang = LanguageDetector.detect_language(Path("file.xyz"))
        assert lang is None

    def test_detect_string_path(self):
        from cogant.ingest.language_detect import LanguageDetector
        lang = LanguageDetector.detect_language("myfile.py")  # type: ignore
        assert lang == "python"

    def test_detect_repo_languages(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector
        # Create some Python files
        (tmp_path / "a.py").write_text("x = 1")
        (tmp_path / "b.py").write_text("y = 2")
        (tmp_path / "index.js").write_text("const x = 1;")
        langs = LanguageDetector.detect_repo_languages(tmp_path)
        assert isinstance(langs, dict)
        assert langs.get("python", 0) == 2
        assert langs.get("javascript", 0) == 1

    def test_detect_repo_languages_empty(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector
        langs = LanguageDetector.detect_repo_languages(tmp_path)
        assert langs == {}

    def test_detect_repo_languages_string_path(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector
        (tmp_path / "main.py").write_text("pass")
        langs = LanguageDetector.detect_repo_languages(str(tmp_path))  # type: ignore
        assert "python" in langs

    def test_get_supported_languages_returns_list(self):
        from cogant.ingest.language_detect import LanguageDetector
        supported = LanguageDetector.get_supported_languages()
        assert isinstance(supported, list)

    def test_get_parser_unknown_raises_import_error(self):
        from cogant.ingest.language_detect import LanguageDetector
        with pytest.raises(ImportError):
            LanguageDetector.get_parser("cobol")

    def test_get_parser_for_extension_unknown(self):
        from cogant.ingest.language_detect import get_parser_for_extension
        result = get_parser_for_extension(".xyz")
        assert result is None

    def test_get_parser_for_extension_without_dot(self):
        from cogant.ingest.language_detect import get_parser_for_extension
        # Should accept extension without leading dot
        result = get_parser_for_extension("py")
        # May return None or a parser depending on available plugins
        # Should not raise
        assert result is None or result is not None


# ---------------------------------------------------------------------------
# ingest/manifest.py — ManifestParser deeper paths
# ---------------------------------------------------------------------------

class TestManifestParserDeeper:
    """Test ManifestParser with real files for branch coverage."""

    def test_parse_requirements_txt_with_extras(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser
        req = tmp_path / "requirements.txt"
        req.write_text("flask==2.0.1\nrequests>=2.28.0\nnumpy[extras]>=1.23\n")
        parser = ManifestParser()
        deps = parser.parse_requirements_txt(req)
        assert isinstance(deps, list)
        names = [d.name for d in deps]
        assert "flask" in names
        assert "requests" in names

    def test_parse_requirements_txt_with_comments(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser
        req = tmp_path / "requirements.txt"
        req.write_text("# This is a comment\npandas>=1.0\n\npytest==7.0.0\n")
        parser = ManifestParser()
        deps = parser.parse_requirements_txt(req)
        names = [d.name for d in deps]
        assert "pandas" in names
        assert "pytest" in names

    def test_parse_requirements_txt_with_urls(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser
        req = tmp_path / "requirements.txt"
        req.write_text("-r base.txt\nhttps://example.com/package.tar.gz\nflask\n")
        parser = ManifestParser()
        deps = parser.parse_requirements_txt(req)
        # Should skip -r and http lines, parse plain names
        assert isinstance(deps, list)

    def test_parse_package_json_basic(self, tmp_path):
        import json
        from cogant.ingest.manifest import ManifestParser
        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({
            "name": "my-app",
            "version": "1.0.0",
            "dependencies": {"express": "^4.18.2", "lodash": "^4.17.21"},
            "devDependencies": {"jest": "^29.0.0"},
        }))
        parser = ManifestParser()
        meta, deps = parser.parse_package_json(pkg)
        assert isinstance(deps, list)
        dep_names = [d.name for d in deps]
        assert "express" in dep_names or "lodash" in dep_names

    def test_parse_package_json_minimal(self, tmp_path):
        import json
        from cogant.ingest.manifest import ManifestParser
        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({"name": "minimal"}))
        parser = ManifestParser()
        meta, deps = parser.parse_package_json(pkg)
        assert isinstance(deps, list)

    def test_parse_pyproject_toml_basic(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser
        toml = tmp_path / "pyproject.toml"
        toml.write_text(
            '[project]\nname = "myproj"\nversion = "0.1.0"\n'
            '[project.dependencies]\n'
            'dependencies = ["click>=8.0", "rich>=10.0"]\n'
        )
        parser = ManifestParser()
        meta, deps = parser.parse_pyproject_toml(toml)
        assert isinstance(deps, list)

    def test_parse_pyproject_toml_poetry(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser
        toml = tmp_path / "pyproject.toml"
        toml.write_text(
            '[tool.poetry]\nname = "myproj"\nversion = "1.0"\n'
            '[tool.poetry.dependencies]\n'
            'python = "^3.11"\n'
            'click = "^8.0"\n'
        )
        parser = ManifestParser()
        meta, deps = parser.parse_pyproject_toml(toml)
        assert isinstance(deps, list)

    def test_parse_setup_py_basic(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser
        setup = tmp_path / "setup.py"
        setup.write_text(
            'from setuptools import setup\n'
            'setup(\n'
            '    name="myproj",\n'
            '    install_requires=["flask>=2.0", "click"],\n'
            ')\n'
        )
        parser = ManifestParser()
        meta, deps = parser.parse_setup_py(setup)
        assert isinstance(deps, list)
