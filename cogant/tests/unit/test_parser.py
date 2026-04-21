"""Unit tests for :class:`cogant.static.parser.PythonASTParser`.

These tests exercise the real parser on in-memory source strings and
on-disk temp files. Every assertion touches a concrete ``PythonModule``
or one of its ``FunctionDef`` / ``ClassDef`` / ``ImportDef`` /
``AssignmentDef`` dataclasses — no raw ``ast`` walking or dict
literals.

The ``PythonLanguageParser.extract_calls`` test class at the bottom is
preserved from the prior version (it already exercised the real
parsers package).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from cogant.static.parser import (
    AssignmentDef,
    ClassDef,
    FunctionDef,
    ImportDef,
    PythonASTParser,
    PythonModule,
)

# Make the ``parsers`` package importable (it lives outside ``py/``).
_PARSERS_ROOT = Path(__file__).resolve().parents[2]
if str(_PARSERS_ROOT) not in sys.path:
    sys.path.insert(0, str(_PARSERS_ROOT))

from parsers.python.parser import PythonLanguageParser  # noqa: E402

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------- fixtures


@pytest.fixture
def parser() -> PythonASTParser:
    """Fresh PythonASTParser instance."""
    return PythonASTParser()


@pytest.fixture
def simple_source() -> str:
    """A small but structurally rich Python source snippet."""
    return '''"""A test module."""

import os
from typing import List, Optional


class User:
    """A user entity."""

    def __init__(self, name: str) -> None:
        self.name = name

    def greet(self) -> str:
        """Return a greeting."""
        return f"Hello {self.name}"


def process(items: List[int]) -> int:
    """Sum a list of integers."""
    return sum(items)


async def fetch(url: str) -> Optional[str]:
    """Async fetch a URL."""
    return None


CONSTANT: int = 42
'''


# --------------------------------------------------------------- parse_string


class TestParseString:
    """Tests for ``PythonASTParser.parse_string``."""

    def test_returns_python_module(self, parser: PythonASTParser, simple_source: str) -> None:
        module = parser.parse_string(simple_source)
        assert isinstance(module, PythonModule)
        assert module.errors == []

    def test_extracts_module_docstring(self, parser: PythonASTParser, simple_source: str) -> None:
        module = parser.parse_string(simple_source)
        assert module.docstring == "A test module."

    def test_extracts_top_level_functions(
        self, parser: PythonASTParser, simple_source: str
    ) -> None:
        module = parser.parse_string(simple_source)
        names = {f.name for f in module.functions}
        assert "process" in names
        assert "fetch" in names
        # Methods live on the class, not at the top level
        assert "greet" not in names

    def test_extracts_async_function_flag(
        self, parser: PythonASTParser, simple_source: str
    ) -> None:
        module = parser.parse_string(simple_source)
        fetch = next(f for f in module.functions if f.name == "fetch")
        assert isinstance(fetch, FunctionDef)
        assert fetch.is_async is True

    def test_extracts_classes_with_methods(
        self, parser: PythonASTParser, simple_source: str
    ) -> None:
        module = parser.parse_string(simple_source)
        assert len(module.classes) == 1
        user = module.classes[0]
        assert isinstance(user, ClassDef)
        assert user.name == "User"
        assert user.docstring == "A user entity."
        method_names = {m.name for m in user.methods}
        assert "__init__" in method_names
        assert "greet" in method_names

    def test_extracts_imports(self, parser: PythonASTParser, simple_source: str) -> None:
        module = parser.parse_string(simple_source)
        assert len(module.imports) >= 2
        for imp in module.imports:
            assert isinstance(imp, ImportDef)
        module_names = {imp.module_name for imp in module.imports}
        # ``import os`` is plain; ``from typing import ...`` is relative=False
        assert any("os" in m for m in module_names)
        assert any("typing" in m for m in module_names)

    def test_extracts_module_level_assignment(
        self, parser: PythonASTParser, simple_source: str
    ) -> None:
        module = parser.parse_string(simple_source)
        names = {a.target_name for a in module.assignments}
        assert "CONSTANT" in names
        constant = next(a for a in module.assignments if a.target_name == "CONSTANT")
        assert isinstance(constant, AssignmentDef)
        assert constant.annotation == "int"


# --------------------------------------------------------------- parse_file


class TestParseFile:
    """Tests for ``PythonASTParser.parse_file``."""

    def test_parse_real_file_on_disk(self, parser: PythonASTParser, tmp_path: Path) -> None:
        path = tmp_path / "sample.py"
        path.write_text('"""On-disk module."""\ndef hello() -> str:\n    return "hi"\n')
        module = parser.parse_file(path)
        assert module.file_path == path
        assert module.docstring == "On-disk module."
        assert len(module.functions) == 1
        assert module.functions[0].name == "hello"

    def test_parse_nonexistent_file_records_error(
        self, parser: PythonASTParser, tmp_path: Path
    ) -> None:
        missing = tmp_path / "does_not_exist.py"
        module = parser.parse_file(missing)
        # Error recorded, no crash
        assert module.errors
        assert module.functions == []

    def test_parse_syntax_error_records_error(
        self, parser: PythonASTParser, tmp_path: Path
    ) -> None:
        path = tmp_path / "broken.py"
        path.write_text("def broken(:\n")
        module = parser.parse_file(path)
        assert any("Syntax error" in e for e in module.errors)


# ----------------------------------------------------------------- edge cases


class TestParserEdgeCases:
    """Tests for empty / trivial / nested sources."""

    def test_empty_source_produces_empty_module(self, parser: PythonASTParser) -> None:
        module = parser.parse_string("")
        assert module.functions == []
        assert module.classes == []
        assert module.imports == []

    def test_nested_class_extracted_as_method(self, parser: PythonASTParser) -> None:
        source = (
            "class Outer:\n"
            "    class Inner:\n"
            "        pass\n"
            "    def outer_method(self):\n"
            "        pass\n"
        )
        module = parser.parse_string(source)
        assert len(module.classes) == 1
        outer = module.classes[0]
        assert outer.name == "Outer"
        assert any(m.name == "outer_method" for m in outer.methods)


# ------------------------------------------ PythonLanguageParser (preserved)


class TestPythonLanguageParserExtractCalls:
    """Tests for ``PythonLanguageParser.extract_calls``.

    Exercises the delegation to ``CallGraphBuilder`` and the dict
    serialization contract. All tests use real source strings.
    """

    def test_simple_function_call_from_source(self) -> None:
        plp = PythonLanguageParser()
        source = "def foo():\n    bar()\n\ndef bar():\n    pass\n"
        calls = plp.extract_calls(source, file_path=Path("t.py"))
        assert calls, "Expected at least one call edge"
        assert any(c["caller"] == "foo" and c["callee"] == "bar" for c in calls)

    def test_method_call_extracted_with_receiver(self) -> None:
        plp = PythonLanguageParser()
        source = "class C:\n    def a(self):\n        self.b()\n    def b(self):\n        pass\n"
        calls = plp.extract_calls(source, file_path=Path("t.py"))
        method_calls = [c for c in calls if c["is_method"]]
        assert method_calls, "Expected a method call"
        assert any(c["receiver"] == "self" for c in method_calls)
        assert any(c["callee"] == "b" for c in method_calls)

    def test_call_includes_line_number(self) -> None:
        plp = PythonLanguageParser()
        source = "def f():\n    print('hi')\n"
        calls = plp.extract_calls(source, file_path=Path("t.py"))
        assert calls
        assert all(isinstance(c["line"], int) and c["line"] > 0 for c in calls)

    def test_call_arguments_serialized(self) -> None:
        plp = PythonLanguageParser()
        source = "def f(x):\n    print(x, 42)\n"
        calls = plp.extract_calls(source, file_path=Path("t.py"))
        print_call = next((c for c in calls if c["callee"] == "print"), None)
        assert print_call is not None
        assert isinstance(print_call["args"], list)
        assert len(print_call["args"]) == 2

    def test_multiple_calls_in_one_function(self) -> None:
        plp = PythonLanguageParser()
        source = "def f():\n    a()\n    b()\n    c()\n"
        calls = plp.extract_calls(source, file_path=Path("t.py"))
        callees = {c["callee"] for c in calls}
        assert {"a", "b", "c"}.issubset(callees)

    def test_extract_calls_from_real_file(self, tmp_path: Path) -> None:
        plp = PythonLanguageParser()
        f = tmp_path / "m.py"
        f.write_text("def f():\n    print('hi')\n")
        calls = plp.extract_calls(f)
        assert calls
        assert any(c["callee"] == "print" for c in calls)

    def test_extract_calls_returns_list_not_none(self) -> None:
        plp = PythonLanguageParser()
        calls = plp.extract_calls("def f():\n    pass\n", file_path=Path("t.py"))
        assert isinstance(calls, list)

    def test_extract_calls_handles_syntax_error(self) -> None:
        plp = PythonLanguageParser()
        calls = plp.extract_calls("def broken(:", file_path=Path("t.py"))
        assert calls == []

    def test_extract_calls_with_nonexistent_path(self, tmp_path: Path) -> None:
        plp = PythonLanguageParser()
        missing = tmp_path / "missing.py"
        calls = plp.extract_calls(missing)
        assert calls == []

    def test_call_edge_has_stable_id(self) -> None:
        plp = PythonLanguageParser()
        source = "def f():\n    print('x')\n"
        calls = plp.extract_calls(source, file_path=Path("t.py"))
        assert calls
        ids = [c["id"] for c in calls]
        assert all(isinstance(i, str) and len(i) == 16 for i in ids)
