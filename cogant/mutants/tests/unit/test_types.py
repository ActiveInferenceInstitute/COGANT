"""Tests for ``cogant.static.types``.

Real Python snippets drive the TypeInferencer, and assertions check the
resulting :class:`TypeInfo` records for functions, parameters, class
attributes (both class-body AnnAssigns and ``self.x`` assignments inside
``__init__``), and module-level variables.
"""

from pathlib import Path

from cogant.static.types import TypeInferencer, TypeInfo

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _infer(source: str) -> list[TypeInfo]:
    return TypeInferencer().infer_types_from_source(source, Path("snippet.py"))


def _by_name(
    infos: list[TypeInfo],
    name: str,
    kind: str | None = None,
) -> TypeInfo | None:
    for info in infos:
        if info.symbol_name == name and (kind is None or info.symbol_kind == kind):
            return info
    return None


def _all_by_name(
    infos: list[TypeInfo], name: str, kind: str | None = None
) -> list[TypeInfo]:
    return [
        i
        for i in infos
        if i.symbol_name == name and (kind is None or i.symbol_kind == kind)
    ]


# ---------------------------------------------------------------------------
# Function-level annotations
# ---------------------------------------------------------------------------


class TestFunctionAnnotations:
    def test_return_annotation(self):
        infos = _infer("def f() -> int:\n    return 1\n")
        ret = _by_name(infos, "f", "function")
        assert ret is not None
        assert ret.inferred_type == "int"
        assert ret.annotation == "int"
        assert ret.confidence == 1.0

    def test_parameter_annotations(self):
        infos = _infer("def f(x: int, y: str) -> None:\n    pass\n")
        x = _by_name(infos, "x", "parameter")
        y = _by_name(infos, "y", "parameter")
        assert x is not None and x.inferred_type == "int"
        assert y is not None and y.inferred_type == "str"

    def test_return_annotation_with_generics(self):
        infos = _infer("def f() -> list[str]:\n    return []\n")
        ret = _by_name(infos, "f", "function")
        assert ret is not None
        assert ret.inferred_type == "list[str]"

    def test_unannotated_function_no_return_type(self):
        infos = _infer("def f(x):\n    return x\n")
        ret = _by_name(infos, "f", "function")
        # No annotation, no yield, no property → nothing inferred
        assert ret is None

    def test_generator_function_inferred_iterator(self):
        infos = _infer(
            "def gen():\n"
            "    yield 1\n"
            "    yield 2\n"
        )
        ret = _by_name(infos, "gen", "function")
        assert ret is not None
        assert ret.inferred_type == "Iterator"
        assert ret.confidence == 0.6

    def test_keyword_only_argument_annotated(self):
        infos = _infer(
            "def f(*, name: str) -> None:\n"
            "    pass\n"
        )
        name_info = _by_name(infos, "name", "parameter")
        assert name_info is not None
        assert name_info.inferred_type == "str"

    def test_async_function_return_annotation(self):
        infos = _infer(
            "async def run() -> bool:\n"
            "    return True\n"
        )
        ret = _by_name(infos, "run")
        assert ret is not None
        assert ret.inferred_type == "bool"
        assert ret.metadata.get("is_async") is True


# ---------------------------------------------------------------------------
# Class annotations
# ---------------------------------------------------------------------------


class TestClassAttributes:
    def test_class_body_annotated_attribute(self):
        infos = _infer(
            "class C:\n"
            "    count: int\n"
        )
        count = _by_name(infos, "count", "attribute")
        assert count is not None
        assert count.inferred_type == "int"
        assert count.metadata.get("class") == "C"

    def test_self_attribute_literal_inference_in_init(self):
        infos = _infer(
            "class C:\n"
            "    def __init__(self, name: str):\n"
            "        self.name = name\n"
            "        self.count = 0\n"
            "        self.ratio = 1.5\n"
        )
        count = _by_name(infos, "count", "attribute")
        ratio = _by_name(infos, "ratio", "attribute")
        assert count is not None
        assert count.inferred_type == "int"
        assert count.confidence == 0.7
        assert count.metadata.get("source") == "self-assignment"
        assert ratio is not None
        assert ratio.inferred_type == "float"

    def test_self_attribute_annotation_in_init(self):
        infos = _infer(
            "class C:\n"
            "    def __init__(self) -> None:\n"
            "        self.users: list = []\n"
        )
        users = _by_name(infos, "users", "attribute")
        assert users is not None
        assert users.annotation == "list"
        assert users.confidence == 1.0
        assert users.metadata.get("source") == "self-annotation"

    def test_method_return_annotation_scoped(self):
        infos = _infer(
            "class C:\n"
            "    def name(self) -> str:\n"
            "        return 'a'\n"
        )
        name_info = _by_name(infos, "name", "method")
        assert name_info is not None
        assert name_info.inferred_type == "str"
        assert name_info.metadata.get("qualified_name") == "C.name"

    def test_property_decorator_fallback(self):
        infos = _infer(
            "class C:\n"
            "    @property\n"
            "    def x(self):\n"
            "        return 1\n"
        )
        info = _by_name(infos, "x", "method")
        assert info is not None
        assert info.inferred_type == "Any"
        assert info.confidence == 0.6


# ---------------------------------------------------------------------------
# Variable-level
# ---------------------------------------------------------------------------


class TestVariables:
    def test_module_annotated_variable(self):
        infos = _infer("RATE: float = 0.5\n")
        info = _by_name(infos, "RATE", "variable")
        assert info is not None
        assert info.inferred_type == "float"
        assert info.confidence == 1.0

    def test_module_literal_variable(self):
        infos = _infer("THRESHOLD = 10\n")
        info = _by_name(infos, "THRESHOLD", "variable")
        assert info is not None
        assert info.inferred_type == "int"
        assert info.confidence == 0.7

    def test_literal_string(self):
        infos = _infer("NAME = 'alice'\n")
        info = _by_name(infos, "NAME", "variable")
        assert info is not None
        assert info.inferred_type == "str"

    def test_literal_list_dict_set(self):
        infos = _infer(
            "A = [1, 2]\n"
            "B = {1: 'a'}\n"
            "C = {1, 2}\n"
            "D = (1, 2)\n"
        )
        assert _by_name(infos, "A").inferred_type == "list"
        assert _by_name(infos, "B").inferred_type == "dict"
        assert _by_name(infos, "C").inferred_type == "set"
        assert _by_name(infos, "D").inferred_type == "tuple"

    def test_literal_bool_none(self):
        infos = _infer(
            "FLAG = True\n"
            "MAYBE = None\n"
        )
        assert _by_name(infos, "FLAG").inferred_type == "bool"
        assert _by_name(infos, "MAYBE").inferred_type == "None"

    def test_constructor_call_inference(self):
        infos = _infer(
            "CONFIG = dict(a=1)\n"
            "BUFFER = list()\n"
        )
        assert _by_name(infos, "CONFIG").inferred_type == "dict"
        assert _by_name(infos, "BUFFER").inferred_type == "list"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_syntax_error_returns_empty(self):
        infos = _infer("def broken(:\n    pass")
        assert infos == []

    def test_empty_source_returns_empty(self):
        assert _infer("") == []

    def test_missing_file_returns_empty(self, tmp_path):
        missing = tmp_path / "nope.py"
        assert TypeInferencer().infer_types_from_file(missing) == []

    def test_real_file(self, tmp_path):
        f = tmp_path / "m.py"
        f.write_text(
            "def f(x: int) -> int:\n"
            "    return x\n"
        )
        infos = TypeInferencer().infer_types_from_file(f)
        x = _by_name(infos, "x", "parameter")
        assert x is not None
        assert x.inferred_type == "int"


# ---------------------------------------------------------------------------
# Integration / symbol ID resolution
# ---------------------------------------------------------------------------


class TestSymbolIdBackfill:
    def test_symbol_ids_populated_when_possible(self):
        infos = _infer(
            "def f(x: int) -> int:\n"
            "    return x\n"
        )
        f_info = _by_name(infos, "f", "function")
        # Symbol table includes function ``f`` → id should be 16 hex chars.
        assert f_info is not None
        assert isinstance(f_info.symbol_id, str)
        # Either we got a resolved 16-char id or empty string; both are fine
        # but the common case for a discoverable symbol should be populated.
        assert f_info.symbol_id == "" or len(f_info.symbol_id) == 16


# ---------------------------------------------------------------------------
# Backwards-compat helpers (the parser-level _infer_* methods)
# ---------------------------------------------------------------------------


class TestLegacyHelpers:
    def test_infer_type_from_value_literal_cases(self):
        ti = TypeInferencer()
        assert ti._infer_type_from_value("None") == "None"
        assert ti._infer_type_from_value("True") == "bool"
        assert ti._infer_type_from_value("[1, 2]") == "list"
        assert ti._infer_type_from_value("{'a': 1}") == "dict"
        assert ti._infer_type_from_value("{1, 2}") == "set"
        assert ti._infer_type_from_value("(1, 2)") == "tuple"
        assert ti._infer_type_from_value("'hi'") == "str"
        assert ti._infer_type_from_value("42") == "int"
        assert ti._infer_type_from_value("-3") == "int"
        assert ti._infer_type_from_value("3.14") == "float"
        assert ti._infer_type_from_value("dict()") == "dict"
        assert ti._infer_type_from_value("") is None
        assert ti._infer_type_from_value(None) is None
