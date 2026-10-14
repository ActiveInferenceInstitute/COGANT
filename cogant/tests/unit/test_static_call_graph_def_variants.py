"""CallGraphBuilder extracts each call exactly once, including from async defs.

Two defs can share a name (an ``@property`` getter and its ``@x.setter``,
``@overload`` variants, conditional redefinitions); each def's calls must
be reported once, not once per same-named sibling. ``async def`` functions
and methods are ordinary callers whose calls must not be dropped.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from cogant.static.calls import CallGraphBuilder

_SOURCE = """\
class Box:
    @property
    def value(self):
        return compute_a()

    @value.setter
    def value(self, v):
        compute_b(v)

    async def refresh(self):
        await reload()


async def fetch():
    return await download()


def plain():
    return helper()
"""


def _call_counts(edges: list) -> Counter[tuple[str, str, int]]:
    return Counter((e.caller_name, e.callee_name, e.line_num) for e in edges)


@pytest.mark.unit
@pytest.mark.parametrize("entry", ["source", "file"])
def test_each_call_is_reported_once_including_async_defs(tmp_path: Path, entry: str) -> None:
    path = tmp_path / "box.py"
    path.write_text(_SOURCE, encoding="utf-8")
    builder = CallGraphBuilder(repo_root=tmp_path)

    if entry == "source":
        edges = builder.extract_calls_from_source(_SOURCE, path)
    else:
        edges = builder.extract_calls_from_file(path)

    assert _call_counts(edges) == Counter(
        {
            ("value", "compute_a", 4): 1,
            ("value", "compute_b", 8): 1,
            ("refresh", "reload", 11): 1,
            ("fetch", "download", 15): 1,
            ("plain", "helper", 19): 1,
        }
    )
