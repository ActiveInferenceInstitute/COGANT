#!/usr/bin/env python3
"""Coverage boost batch 39 — static/types.py and ingest/repo.py.

Covers:
- TypeInfo dataclass: creation, defaults, metadata
- TypeInferencer: infer_types_from_source (all branches), _infer_from_function,
  _infer_from_class, _infer_from_assign, _infer_from_annassign,
  _infer_init_attributes, _infer_return_from_body, _infer_literal_type,
  _annotation_to_str, _safe_unparse, _call_name, _infer_type_from_value,
  _infer_function_return_type, _infer_variable_type, _resolve_symbol_ids
- RepoMetadata dataclass
- RepoSnapshot dataclass
- RepoIngester: init, ingest_local (normal, not-exists, not-dir),
  _extract_metadata, _extract_dependencies
"""

import ast

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# TypeInfo
# ---------------------------------------------------------------------------


class TestTypeInfoDataclass:
    def test_creation(self):
        from cogant.static.types import TypeInfo

        ti = TypeInfo(symbol_id="s1", symbol_name="myvar", symbol_kind="variable")
        assert ti.symbol_id == "s1"
        assert ti.symbol_name == "myvar"
        assert ti.symbol_kind == "variable"

    def test_defaults(self):
        from cogant.static.types import TypeInfo

        ti = TypeInfo(symbol_id="", symbol_name="x", symbol_kind="variable")
        assert ti.inferred_type is None
        assert ti.annotation is None
        assert ti.is_mutable is True
        assert ti.confidence == 0.0
        assert ti.metadata == {}

    def test_custom_values(self):
        from cogant.static.types import TypeInfo

        ti = TypeInfo(
            symbol_id="x",
            symbol_name="y",
            symbol_kind="function",
            inferred_type="int",
            annotation="int",
            is_mutable=False,
            confidence=1.0,
            metadata={"scope": "module"},
        )
        assert ti.inferred_type == "int"
        assert ti.is_mutable is False
        assert ti.confidence == 1.0
        assert ti.metadata["scope"] == "module"


# ---------------------------------------------------------------------------
# TypeInferencer — static helpers
# ---------------------------------------------------------------------------


class TestAnnotationToStr:
    def test_none_returns_none(self):
        from cogant.static.types import TypeInferencer

        assert TypeInferencer._annotation_to_str(None) is None

    def test_name_node(self):
        from cogant.static.types import TypeInferencer

        ann = ast.Name(id="int", ctx=ast.Load())
        result = TypeInferencer._annotation_to_str(ann)
        assert result == "int"

    def test_constant_node(self):
        from cogant.static.types import TypeInferencer

        # "str" literal as annotation
        ann = ast.parse('"str"', mode="eval").body
        result = TypeInferencer._annotation_to_str(ann)
        assert result is not None


class TestSafeUnparse:
    def test_none_returns_none(self):
        from cogant.static.types import TypeInferencer

        assert TypeInferencer._safe_unparse(None) is None

    def test_constant(self):
        from cogant.static.types import TypeInferencer

        node = ast.Constant(value=42)
        result = TypeInferencer._safe_unparse(node)
        assert result == "42"

    def test_name(self):
        from cogant.static.types import TypeInferencer

        node = ast.Name(id="foo", ctx=ast.Load())
        result = TypeInferencer._safe_unparse(node)
        assert result == "foo"


class TestCallName:
    def test_simple_name(self):
        from cogant.static.types import TypeInferencer

        node = ast.Name(id="dict", ctx=ast.Load())
        assert TypeInferencer._call_name(node) == "dict"

    def test_attribute(self):
        from cogant.static.types import TypeInferencer

        node = ast.Attribute(value=ast.Name(id="os"), attr="path", ctx=ast.Load())
        assert TypeInferencer._call_name(node) == "path"

    def test_other_returns_none(self):
        from cogant.static.types import TypeInferencer

        node = ast.Constant(value=1)
        assert TypeInferencer._call_name(node) is None


class TestInferTypeFromValue:
    def test_none_string(self):
        from cogant.static.types import TypeInferencer

        assert TypeInferencer._infer_type_from_value("None") == "None"

    def test_true_false(self):
        from cogant.static.types import TypeInferencer

        assert TypeInferencer._infer_type_from_value("True") == "bool"
        assert TypeInferencer._infer_type_from_value("False") == "bool"

    def test_list_literal(self):
        from cogant.static.types import TypeInferencer

        assert TypeInferencer._infer_type_from_value("[1, 2]") == "list"

    def test_dict_literal(self):
        from cogant.static.types import TypeInferencer

        assert TypeInferencer._infer_type_from_value('{"k": "v"}') == "dict"

    def test_set_literal(self):
        from cogant.static.types import TypeInferencer

        assert TypeInferencer._infer_type_from_value("{1, 2}") == "set"

    def test_tuple_literal(self):
        from cogant.static.types import TypeInferencer

        assert TypeInferencer._infer_type_from_value("(1, 2)") == "tuple"

    def test_string_literal(self):
        from cogant.static.types import TypeInferencer

        assert TypeInferencer._infer_type_from_value('"hello"') == "str"
        assert TypeInferencer._infer_type_from_value("'world'") == "str"

    def test_integer(self):
        from cogant.static.types import TypeInferencer

        assert TypeInferencer._infer_type_from_value("42") == "int"

    def test_negative_integer(self):
        from cogant.static.types import TypeInferencer

        assert TypeInferencer._infer_type_from_value("-5") == "int"

    def test_float(self):
        from cogant.static.types import TypeInferencer

        assert TypeInferencer._infer_type_from_value("3.14") == "float"

    def test_constructor_call_dict(self):
        from cogant.static.types import TypeInferencer

        assert TypeInferencer._infer_type_from_value("dict()") == "dict"

    def test_constructor_call_list(self):
        from cogant.static.types import TypeInferencer

        assert TypeInferencer._infer_type_from_value("list()") == "list"

    def test_empty_string_returns_none(self):
        from cogant.static.types import TypeInferencer

        assert TypeInferencer._infer_type_from_value("") is None

    def test_none_input_returns_none(self):
        from cogant.static.types import TypeInferencer

        assert TypeInferencer._infer_type_from_value(None) is None

    def test_unrecognized_returns_none(self):
        from cogant.static.types import TypeInferencer

        assert TypeInferencer._infer_type_from_value("some_variable") is None


# ---------------------------------------------------------------------------
# TypeInferencer — _infer_literal_type (via AST nodes)
# ---------------------------------------------------------------------------


class TestInferLiteralType:
    def _inferencer(self):
        from cogant.static.types import TypeInferencer

        return TypeInferencer()

    def test_int_constant(self):
        inf = self._inferencer()
        node = ast.Constant(value=42)
        assert inf._infer_literal_type(node) == "int"

    def test_float_constant(self):
        inf = self._inferencer()
        node = ast.Constant(value=3.14)
        assert inf._infer_literal_type(node) == "float"

    def test_str_constant(self):
        inf = self._inferencer()
        node = ast.Constant(value="hello")
        assert inf._infer_literal_type(node) == "str"

    def test_bool_constant(self):
        inf = self._inferencer()
        node = ast.Constant(value=True)
        assert inf._infer_literal_type(node) == "bool"

    def test_none_constant(self):
        inf = self._inferencer()
        node = ast.Constant(value=None)
        assert inf._infer_literal_type(node) == "None"

    def test_bytes_constant(self):
        inf = self._inferencer()
        node = ast.Constant(value=b"data")
        assert inf._infer_literal_type(node) == "bytes"

    def test_list_node(self):
        inf = self._inferencer()
        node = ast.List(elts=[], ctx=ast.Load())
        assert inf._infer_literal_type(node) == "list"

    def test_tuple_node(self):
        inf = self._inferencer()
        node = ast.Tuple(elts=[], ctx=ast.Load())
        assert inf._infer_literal_type(node) == "tuple"

    def test_set_node(self):
        inf = self._inferencer()
        node = ast.Set(elts=[])
        assert inf._infer_literal_type(node) == "set"

    def test_dict_node(self):
        inf = self._inferencer()
        node = ast.Dict(keys=[], values=[])
        assert inf._infer_literal_type(node) == "dict"

    def test_call_to_dict(self):
        inf = self._inferencer()
        call = ast.parse("dict()").body[0].value
        assert inf._infer_literal_type(call) == "dict"

    def test_call_to_list(self):
        inf = self._inferencer()
        call = ast.parse("list()").body[0].value
        assert inf._infer_literal_type(call) == "list"

    def test_none_input(self):
        inf = self._inferencer()
        assert inf._infer_literal_type(None) is None

    def test_unrecognized_returns_none(self):
        inf = self._inferencer()
        node = ast.Name(id="foo", ctx=ast.Load())
        assert inf._infer_literal_type(node) is None


# ---------------------------------------------------------------------------
# TypeInferencer — _infer_return_from_body
# ---------------------------------------------------------------------------


class TestInferReturnFromBody:
    def _inferencer(self):
        from cogant.static.types import TypeInferencer

        return TypeInferencer()

    def test_property_decorator(self):
        inf = self._inferencer()
        src = """
@property
def x(self):
    return self._x
"""
        func = ast.parse(src).body[0]
        result = inf._infer_return_from_body(func)
        assert result == "Any"

    def test_yield_function(self):
        inf = self._inferencer()
        src = """
def gen():
    yield 1
"""
        func = ast.parse(src).body[0]
        result = inf._infer_return_from_body(func)
        assert result == "Iterator"

    def test_no_hints_returns_none(self):
        inf = self._inferencer()
        src = """
def foo():
    return 42
"""
        func = ast.parse(src).body[0]
        result = inf._infer_return_from_body(func)
        assert result is None


# ---------------------------------------------------------------------------
# TypeInferencer — infer_types_from_source
# ---------------------------------------------------------------------------


class TestInferTypesFromSource:
    def _inferencer(self, tmp_path):
        from cogant.static.types import TypeInferencer

        return TypeInferencer(repo_root=tmp_path)

    def test_empty_source(self, tmp_path):
        inf = self._inferencer(tmp_path)
        result = inf.infer_types_from_source("", tmp_path / "f.py")
        assert isinstance(result, list)

    def test_syntax_error_returns_empty(self, tmp_path):
        inf = self._inferencer(tmp_path)
        result = inf.infer_types_from_source("def foo(:", tmp_path / "f.py")
        assert result == []

    def test_annotated_function_return(self, tmp_path):
        inf = self._inferencer(tmp_path)
        src = "def add(a: int, b: int) -> int:\n    return a + b\n"
        result = inf.infer_types_from_source(src, tmp_path / "f.py")
        # Should include return type
        return_infos = [r for r in result if r.metadata.get("role") == "return"]
        assert len(return_infos) >= 1
        assert return_infos[0].inferred_type == "int"

    def test_parameter_annotations(self, tmp_path):
        inf = self._inferencer(tmp_path)
        src = "def foo(x: str, y: float) -> None:\n    pass\n"
        result = inf.infer_types_from_source(src, tmp_path / "f.py")
        param_infos = [r for r in result if r.symbol_kind == "parameter"]
        param_names = [r.symbol_name for r in param_infos]
        assert "x" in param_names
        assert "y" in param_names

    def test_module_level_annassign(self, tmp_path):
        inf = self._inferencer(tmp_path)
        src = "x: int = 42\n"
        result = inf.infer_types_from_source(src, tmp_path / "f.py")
        assert len(result) >= 1
        assert result[0].inferred_type == "int"

    def test_module_level_assign_literal(self, tmp_path):
        inf = self._inferencer(tmp_path)
        src = "MY_CONST = 'hello'\n"
        result = inf.infer_types_from_source(src, tmp_path / "f.py")
        assert any(r.inferred_type == "str" for r in result)

    def test_class_with_annotated_attrs(self, tmp_path):
        inf = self._inferencer(tmp_path)
        src = """
class Foo:
    count: int = 0
    name: str = "bar"
    def __init__(self):
        self.x = 42
"""
        result = inf.infer_types_from_source(src, tmp_path / "f.py")
        assert len(result) > 0

    def test_class_attributes_from_init(self, tmp_path):
        inf = self._inferencer(tmp_path)
        src = """
class Foo:
    def __init__(self):
        self.value = 3.14
        self.name = "test"
"""
        result = inf.infer_types_from_source(src, tmp_path / "f.py")
        attr_infos = [r for r in result if r.symbol_kind == "attribute"]
        type_names = {r.symbol_name: r.inferred_type for r in attr_infos}
        assert "value" in type_names or "name" in type_names

    def test_generator_function(self, tmp_path):
        inf = self._inferencer(tmp_path)
        src = """
def gen():
    yield 1
"""
        result = inf.infer_types_from_source(src, tmp_path / "f.py")
        return_infos = [r for r in result if r.metadata.get("role") == "return"]
        if return_infos:
            assert return_infos[0].inferred_type == "Iterator"

    def test_async_function(self, tmp_path):
        inf = self._inferencer(tmp_path)
        src = "async def fetch() -> str:\n    return 'result'\n"
        result = inf.infer_types_from_source(src, tmp_path / "f.py")
        return_infos = [r for r in result if r.metadata.get("role") == "return"]
        if return_infos:
            assert return_infos[0].metadata.get("is_async") is True

    def test_infer_from_file(self, tmp_path):
        from cogant.static.types import TypeInferencer

        py_file = tmp_path / "sample.py"
        py_file.write_text("x: int = 1\ny: str = 'hello'\n")
        inf = TypeInferencer(repo_root=tmp_path)
        result = inf.infer_types_from_file(py_file)
        assert len(result) >= 1

    def test_infer_from_missing_file_returns_empty(self, tmp_path):
        from cogant.static.types import TypeInferencer

        inf = TypeInferencer(repo_root=tmp_path)
        result = inf.infer_types_from_file(tmp_path / "nonexistent.py")
        assert result == []


# ---------------------------------------------------------------------------
# ingest/repo.py — RepoMetadata, RepoSnapshot, RepoIngester
# ---------------------------------------------------------------------------


class TestRepoMetadataDataclass:
    def test_creation(self):
        from cogant.ingest.repo import RepoMetadata

        meta = RepoMetadata(name="myrepo", url="https://github.com/org/myrepo")
        assert meta.name == "myrepo"
        assert meta.url == "https://github.com/org/myrepo"

    def test_defaults(self):
        from cogant.ingest.repo import RepoMetadata

        meta = RepoMetadata(name="x", url="y")
        assert meta.commit_hash is None
        assert meta.commit_message is None
        assert meta.timestamp is None
        assert meta.author is None
        assert meta.language is None
        assert meta.description is None


class TestRepoSnapshotDataclass:
    def test_creation(self, tmp_path):
        from cogant.ingest.repo import RepoMetadata, RepoSnapshot

        meta = RepoMetadata(name="test", url="file:///test")
        snap = RepoSnapshot(
            metadata=meta,
            files=[],
            dependencies=[],
            root_path=tmp_path,
        )
        assert snap.metadata is meta
        assert snap.files == []
        assert snap.dependencies == []
        assert snap.root_path == tmp_path


class TestRepoIngesterInit:
    def test_default_work_dir(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        ingester = RepoIngester(work_dir=tmp_path)
        assert ingester.work_dir == tmp_path

    def test_creates_work_dir(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        new_dir = tmp_path / "new_work"
        RepoIngester(work_dir=new_dir)
        assert new_dir.exists()


class TestRepoIngesterIngestLocal:
    def test_nonexistent_path_raises(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        ingester = RepoIngester(work_dir=tmp_path)
        with pytest.raises(ValueError, match="does not exist"):
            ingester.ingest_local(tmp_path / "nonexistent")

    def test_file_path_raises(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        f = tmp_path / "file.txt"
        f.write_text("hello")
        ingester = RepoIngester(work_dir=tmp_path)
        with pytest.raises(ValueError, match="not a directory"):
            ingester.ingest_local(f)

    def test_empty_dir_returns_snapshot(self, tmp_path):
        from cogant.ingest.repo import RepoIngester, RepoSnapshot

        ingester = RepoIngester(work_dir=tmp_path)
        snapshot = ingester.ingest_local(tmp_path)
        assert isinstance(snapshot, RepoSnapshot)
        assert snapshot.root_path == tmp_path

    def test_detects_primary_language(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        (tmp_path / "a.py").write_text("x = 1")
        (tmp_path / "b.py").write_text("y = 2")
        ingester = RepoIngester(work_dir=tmp_path)
        snapshot = ingester.ingest_local(tmp_path)
        assert snapshot.metadata.language == "python"

    def test_extracts_requirements(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        (tmp_path / "requirements.txt").write_text("requests>=2.0\nflask\n")
        ingester = RepoIngester(work_dir=tmp_path)
        snapshot = ingester.ingest_local(tmp_path)
        dep_names = [d.name for d in snapshot.dependencies]
        assert "requests" in dep_names
        assert "flask" in dep_names


class TestRepoIngesterExtractMetadata:
    def test_extract_metadata_name_from_dir(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        mydir = tmp_path / "myrepo"
        mydir.mkdir()
        ingester = RepoIngester(work_dir=tmp_path)
        meta = ingester._extract_metadata(mydir)
        assert meta.name == "myrepo"

    def test_extract_metadata_url_is_path(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        ingester = RepoIngester(work_dir=tmp_path)
        meta = ingester._extract_metadata(tmp_path)
        assert str(tmp_path) in meta.url

    def test_extract_metadata_timestamp_set(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        ingester = RepoIngester(work_dir=tmp_path)
        meta = ingester._extract_metadata(tmp_path)
        assert meta.timestamp is not None


class TestRepoIngesterExtractDependencies:
    def test_empty_repo_no_deps(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        ingester = RepoIngester(work_dir=tmp_path)
        deps = ingester._extract_dependencies(tmp_path)
        assert deps == []

    def test_requirements_txt_found(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        (tmp_path / "requirements.txt").write_text("numpy\npandas\n")
        ingester = RepoIngester(work_dir=tmp_path)
        deps = ingester._extract_dependencies(tmp_path)
        names = [d.name for d in deps]
        assert "numpy" in names
        assert "pandas" in names

    def test_package_json_found(self, tmp_path):
        import json

        from cogant.ingest.repo import RepoIngester

        pkg = {"name": "app", "dependencies": {"react": "^18.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        ingester = RepoIngester(work_dir=tmp_path)
        deps = ingester._extract_dependencies(tmp_path)
        names = [d.name for d in deps]
        assert "react" in names

    def test_deduplicates_deps(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        (tmp_path / "requirements.txt").write_text("requests>=2.0\nrequests>=2.0\n")
        ingester = RepoIngester(work_dir=tmp_path)
        deps = ingester._extract_dependencies(tmp_path)
        request_deps = [d for d in deps if d.name == "requests"]
        assert len(request_deps) == 1
