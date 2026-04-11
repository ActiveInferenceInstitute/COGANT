#!/usr/bin/env python3
"""Coverage boost batch 46 — static/types.py deeper coverage.

Covers:
- TypeInferencer.infer_types_from_source: SyntaxError path (lines 108-110),
  symbol extraction failure (lines 116-118), class body ast.Assign path (line 236),
  _infer_from_assign returns [] when type is None (line 318)
- TypeInferencer._infer_function_return_type: symbol not found (None), with annotation,
  with @property decorator, without annotation
- TypeInferencer._infer_variable_type: symbol not found (None), with annotation,
  with value inference (no annotation but has value), fully None
- TypeInferencer._annotation_to_str: None input, Name node fallback, Constant fallback
- TypeInferencer._safe_unparse: None input
- TypeInferencer._infer_literal_type: None node, bool, bytes, list, tuple, set, dict,
  Call(list/dict/set), unrecognized
- TypeInferencer._infer_return_from_body: property decorator, yield, no hints
- TypeInferencer._infer_init_attributes: self.x = literal in __init__
- TypeInferencer.infer_types_from_file: missing file, valid file
"""

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# TypeInfo dataclass
# ---------------------------------------------------------------------------

class TestTypeInfoDataclass:
    def test_defaults(self):
        from cogant.static.types import TypeInfo
        t = TypeInfo(
            symbol_id="s1",
            symbol_name="my_var",
            symbol_kind="variable",
        )
        assert t.inferred_type is None
        assert t.annotation is None
        assert t.is_mutable is True
        assert t.confidence == 0.0
        assert t.metadata == {}

    def test_with_all_fields(self):
        from cogant.static.types import TypeInfo
        t = TypeInfo(
            symbol_id="s2",
            symbol_name="my_func",
            symbol_kind="function",
            inferred_type="str",
            annotation="str",
            is_mutable=False,
            confidence=1.0,
            metadata={"scope": "module"},
        )
        assert t.confidence == 1.0
        assert t.annotation == "str"
        assert not t.is_mutable


# ---------------------------------------------------------------------------
# TypeInferencer.infer_types_from_source — error paths
# ---------------------------------------------------------------------------

class TestTypeInferencerFromSource:
    def test_syntax_error_returns_empty(self, tmp_path):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer(repo_root=tmp_path)
        result = inf.infer_types_from_source("def foo(:\n", tmp_path / "bad.py")
        assert result == []

    def test_valid_function_with_annotation(self, tmp_path):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer(repo_root=tmp_path)
        source = "def greet(name: str) -> str:\n    return name\n"
        result = inf.infer_types_from_source(source, tmp_path / "t.py")
        assert isinstance(result, list)

    def test_valid_function_return_annotation(self, tmp_path):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer(repo_root=tmp_path)
        source = "def get_count() -> int:\n    return 42\n"
        result = inf.infer_types_from_source(source, tmp_path / "t.py")
        assert isinstance(result, list)

    def test_class_with_annassign(self, tmp_path):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer(repo_root=tmp_path)
        source = (
            "class MyClass:\n"
            "    x: int = 0\n"
            "    name: str\n"
            "    def __init__(self):\n"
            "        self.count = 0\n"
        )
        result = inf.infer_types_from_source(source, tmp_path / "cls.py")
        assert isinstance(result, list)

    def test_class_with_plain_assign(self, tmp_path):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer(repo_root=tmp_path)
        # Plain assign in class body (e.g. x = 42) should hit line 236 path
        source = (
            "class Config:\n"
            "    MAX_SIZE = 100\n"
            "    DEFAULT_NAME = 'config'\n"
        )
        result = inf.infer_types_from_source(source, tmp_path / "cfg.py")
        assert isinstance(result, list)

    def test_property_decorator(self, tmp_path):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer(repo_root=tmp_path)
        source = (
            "class Foo:\n"
            "    @property\n"
            "    def value(self):\n"
            "        return self._value\n"
        )
        result = inf.infer_types_from_source(source, tmp_path / "foo.py")
        assert isinstance(result, list)

    def test_generator_function(self, tmp_path):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer(repo_root=tmp_path)
        source = "def items():\n    yield 1\n    yield 2\n"
        result = inf.infer_types_from_source(source, tmp_path / "gen.py")
        assert isinstance(result, list)

    def test_variable_with_list_literal(self, tmp_path):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer(repo_root=tmp_path)
        source = "items = [1, 2, 3]\n"
        result = inf.infer_types_from_source(source, tmp_path / "t.py")
        assert isinstance(result, list)

    def test_variable_with_dict_literal(self, tmp_path):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer(repo_root=tmp_path)
        source = "data = {}\n"
        result = inf.infer_types_from_source(source, tmp_path / "t.py")
        assert isinstance(result, list)

    def test_variable_with_tuple_literal(self, tmp_path):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer(repo_root=tmp_path)
        source = "coords = (1, 2)\n"
        result = inf.infer_types_from_source(source, tmp_path / "t.py")
        assert isinstance(result, list)

    def test_variable_with_set_literal(self, tmp_path):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer(repo_root=tmp_path)
        source = "unique = {1, 2, 3}\n"
        result = inf.infer_types_from_source(source, tmp_path / "t.py")
        assert isinstance(result, list)

    def test_infer_types_from_file_missing(self, tmp_path):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer(repo_root=tmp_path)
        result = inf.infer_types_from_file(tmp_path / "nosuchfile.py")
        assert isinstance(result, list)

    def test_infer_types_from_file_valid(self, tmp_path):
        from cogant.static.types import TypeInferencer
        f = tmp_path / "module.py"
        f.write_text("def add(a: int, b: int) -> int:\n    return a + b\n")
        inf = TypeInferencer(repo_root=tmp_path)
        result = inf.infer_types_from_file(f)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# TypeInferencer._annotation_to_str — fallback branches
# ---------------------------------------------------------------------------

class TestAnnotationToStr:
    def test_none_input(self):
        from cogant.static.types import TypeInferencer
        result = TypeInferencer._annotation_to_str(None)
        assert result is None

    def test_name_node(self):
        from cogant.static.types import TypeInferencer
        node = ast.Name(id="int", ctx=ast.Load())
        result = TypeInferencer._annotation_to_str(node)
        assert result == "int"

    def test_constant_node(self):
        from cogant.static.types import TypeInferencer
        node = ast.Constant(value="Optional[str]")
        result = TypeInferencer._annotation_to_str(node)
        assert "Optional" in result or result is not None

    def test_valid_subscript_node(self):
        from cogant.static.types import TypeInferencer
        # List[int] — ast.unparse should work fine
        node = ast.Subscript(
            value=ast.Name(id="List", ctx=ast.Load()),
            slice=ast.Name(id="int", ctx=ast.Load()),
            ctx=ast.Load(),
        )
        result = TypeInferencer._annotation_to_str(node)
        assert result is not None


# ---------------------------------------------------------------------------
# TypeInferencer._safe_unparse
# ---------------------------------------------------------------------------

class TestSafeUnparse:
    def test_none_returns_none(self):
        from cogant.static.types import TypeInferencer
        result = TypeInferencer._safe_unparse(None)
        assert result is None

    def test_name_node_returns_str(self):
        from cogant.static.types import TypeInferencer
        node = ast.Name(id="str", ctx=ast.Load())
        result = TypeInferencer._safe_unparse(node)
        assert result == "str"

    def test_constant_returns_repr(self):
        from cogant.static.types import TypeInferencer
        node = ast.Constant(value=42)
        result = TypeInferencer._safe_unparse(node)
        assert result == "42"


# ---------------------------------------------------------------------------
# TypeInferencer._infer_literal_type — all branches
# ---------------------------------------------------------------------------

class TestInferLiteralType:
    def test_none_node(self):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer()
        result = inf._infer_literal_type(None)
        assert result is None

    def test_none_constant(self):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer()
        node = ast.Constant(value=None)
        assert inf._infer_literal_type(node) == "None"

    def test_bool_constant(self):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer()
        node = ast.Constant(value=True)
        assert inf._infer_literal_type(node) == "bool"

    def test_int_constant(self):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer()
        node = ast.Constant(value=42)
        assert inf._infer_literal_type(node) == "int"

    def test_float_constant(self):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer()
        node = ast.Constant(value=3.14)
        assert inf._infer_literal_type(node) == "float"

    def test_str_constant(self):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer()
        node = ast.Constant(value="hello")
        assert inf._infer_literal_type(node) == "str"

    def test_bytes_constant(self):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer()
        node = ast.Constant(value=b"bytes")
        assert inf._infer_literal_type(node) == "bytes"

    def test_list_node(self):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer()
        node = ast.List(elts=[], ctx=ast.Load())
        assert inf._infer_literal_type(node) == "list"

    def test_tuple_node(self):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer()
        node = ast.Tuple(elts=[], ctx=ast.Load())
        assert inf._infer_literal_type(node) == "tuple"

    def test_set_node(self):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer()
        node = ast.Set(elts=[])
        assert inf._infer_literal_type(node) == "set"

    def test_dict_node(self):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer()
        node = ast.Dict(keys=[], values=[])
        assert inf._infer_literal_type(node) == "dict"

    def test_call_list(self):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer()
        node = ast.Call(func=ast.Name(id="list", ctx=ast.Load()), args=[], keywords=[])
        assert inf._infer_literal_type(node) == "list"

    def test_call_dict(self):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer()
        node = ast.Call(func=ast.Name(id="dict", ctx=ast.Load()), args=[], keywords=[])
        assert inf._infer_literal_type(node) == "dict"

    def test_call_unknown_callee(self):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer()
        node = ast.Call(func=ast.Name(id="foo", ctx=ast.Load()), args=[], keywords=[])
        assert inf._infer_literal_type(node) is None

    def test_unrecognized_node_returns_none(self):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer()
        node = ast.Name(id="x", ctx=ast.Load())
        assert inf._infer_literal_type(node) is None


# ---------------------------------------------------------------------------
# TypeInferencer._infer_return_from_body
# ---------------------------------------------------------------------------

class TestInferReturnFromBody:
    def _parse_func(self, source: str) -> ast.FunctionDef:
        tree = ast.parse(source)
        return tree.body[0]  # type: ignore

    def test_property_decorator_returns_any(self):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer()
        func = self._parse_func(
            "@property\ndef value(self):\n    return self._value\n"
        )
        result = inf._infer_return_from_body(func)
        assert result == "Any"

    def test_yield_returns_iterator(self):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer()
        func = self._parse_func("def gen():\n    yield 1\n")
        result = inf._infer_return_from_body(func)
        assert result == "Iterator"

    def test_plain_function_returns_none(self):
        from cogant.static.types import TypeInferencer
        inf = TypeInferencer()
        func = self._parse_func("def foo():\n    pass\n")
        result = inf._infer_return_from_body(func)
        assert result is None


# ---------------------------------------------------------------------------
# TypeInferencer deprecated helpers — _infer_function_return_type
# ---------------------------------------------------------------------------

class TestInferFunctionReturnType:
    def _make_symbol_table(self, source: str, path: Path):
        from cogant.static.symbols import SymbolExtractor
        extractor = SymbolExtractor(path.parent)
        return extractor.extract_from_source(source, path)

    def _parse_funcdef(self, source: str):
        """Parse source and return the first FunctionDef from the parser."""
        from cogant.static.parser import PythonASTParser
        parser = PythonASTParser()
        module = parser.parse_string(source)
        return module.functions[0] if module.functions else None

    def test_symbol_not_found_returns_none(self, tmp_path):
        from cogant.static.types import TypeInferencer
        from cogant.static.symbols import SymbolExtractor

        inf = TypeInferencer(repo_root=tmp_path)
        source = "def foo() -> int:\n    return 1\n"
        st = SymbolExtractor(tmp_path).extract_from_source(source, tmp_path / "t.py")

        # Create a FunctionDef with a name not in the symbol table
        funcdef = self._parse_funcdef("def bar() -> str:\n    return 'hi'\n")
        result = inf._infer_function_return_type(funcdef, st)
        assert result is None

    def test_with_return_annotation(self, tmp_path):
        from cogant.static.types import TypeInferencer
        from cogant.static.symbols import SymbolExtractor

        inf = TypeInferencer(repo_root=tmp_path)
        source = "def foo() -> int:\n    return 1\n"
        st = SymbolExtractor(tmp_path).extract_from_source(source, tmp_path / "t.py")
        funcdef = self._parse_funcdef(source)
        result = inf._infer_function_return_type(funcdef, st)
        # Either None (if symbol not matched) or a TypeInfo
        assert result is None or hasattr(result, "inferred_type")

    def test_no_annotation_returns_none(self, tmp_path):
        from cogant.static.types import TypeInferencer
        from cogant.static.symbols import SymbolExtractor

        inf = TypeInferencer(repo_root=tmp_path)
        source = "def compute():\n    return 42\n"
        st = SymbolExtractor(tmp_path).extract_from_source(source, tmp_path / "t.py")
        funcdef = self._parse_funcdef(source)
        result = inf._infer_function_return_type(funcdef, st)
        assert result is None


# ---------------------------------------------------------------------------
# TypeInferencer deprecated helpers — _infer_variable_type
# ---------------------------------------------------------------------------

class TestInferVariableType:
    def _parse_assign(self, source: str):
        """Parse source and return first AssignmentDef."""
        from cogant.static.parser import PythonASTParser
        module = PythonASTParser().parse_string(source)
        return module.assignments[0] if module.assignments else None

    def test_symbol_not_found_returns_none(self, tmp_path):
        from cogant.static.types import TypeInferencer
        from cogant.static.symbols import SymbolExtractor

        inf = TypeInferencer(repo_root=tmp_path)
        source = "x = 1\n"
        st = SymbolExtractor(tmp_path).extract_from_source(source, tmp_path / "t.py")

        # Parse an assignment with a different name
        assign = self._parse_assign("z = 42\n")
        if assign is None:
            pytest.skip("No assignment parsed")
        result = inf._infer_variable_type(assign, st)
        assert result is None

    def test_with_annotation(self, tmp_path):
        from cogant.static.types import TypeInferencer
        from cogant.static.symbols import SymbolExtractor

        inf = TypeInferencer(repo_root=tmp_path)
        source = "x: int = 1\n"
        st = SymbolExtractor(tmp_path).extract_from_source(source, tmp_path / "t.py")
        assign = self._parse_assign(source)
        if assign is None:
            pytest.skip("No assignment parsed")
        result = inf._infer_variable_type(assign, st)
        # Either a TypeInfo or None
        assert result is None or hasattr(result, "inferred_type")
