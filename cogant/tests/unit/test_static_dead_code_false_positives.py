"""DeadCodeAnalyzer does not report live code as dead, and finds unreachable code.

Python binds ``import a.b`` to the name ``a``; ``from __future__`` imports
are compiler directives; dunder methods are called by the runtime; and a
private method called as ``self._helper()`` is used through an attribute.
None of these are dead. Statements after ``return``/``raise``/``break``/
``continue`` in the same block are, and the analyzer's docstring and report
fields promise to count them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cogant.static.dead_code import DeadCodeAnalyzer

_LIVE_SOURCE = """\
from __future__ import annotations
import os.path
import xml.etree.ElementTree as ET
from json import *

__all__ = ["User"]
_REGISTRY = {}


class User:
    _cache = {}

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self._fmt()

    def _fmt(self):
        return os.path.join(self.name, str(len(self._cache)))

    def parse(self, text):
        return ET.fromstring(text)


def lookup(key):
    return _REGISTRY.get(key)
"""


def _entries(source: str) -> list[tuple[str, str]]:
    report = DeadCodeAnalyzer().analyze(source, Path("user.py"))
    return [(e.kind, e.symbol_name) for e in report.entries]


@pytest.mark.unit
def test_live_imports_dunders_and_attribute_calls_are_not_dead() -> None:
    assert _entries(_LIVE_SOURCE) == []


@pytest.mark.unit
def test_unused_dotted_import_is_reported_by_its_bound_name() -> None:
    """``import os.path`` binds ``os``; unused, it is reported under that name."""
    assert _entries("import os.path\nx = 1\n") == [("UNUSED_IMPORT", "os")]


@pytest.mark.unit
def test_uncalled_private_method_is_still_reported() -> None:
    source = "class A:\n    def _never(self):\n        return 1\n\n    def run(self):\n        return 2\n"
    assert _entries(source) == [("UNUSED_FUNCTION", "_never")]


@pytest.mark.unit
def test_statements_after_a_terminator_are_reported_unreachable() -> None:
    source = """\
def f(items):
    for item in items:
        if item:
            continue
            print("skipped")
    return 1
    x = 2
    y = 3


def g():
    raise ValueError("boom")
"""
    report = DeadCodeAnalyzer().analyze(source, Path("flow.py"))

    unreachable = [(e.line_num, e.scope) for e in report.entries if e.kind == "UNREACHABLE"]
    assert unreachable == [(5, "function:f"), (7, "function:f")]
    assert report.unreachable_statements == 3
