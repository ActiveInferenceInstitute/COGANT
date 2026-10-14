"""READS/WRITES and CALLS edges must come from each callable's own body.

The graph stage used to look a method up by bare name anywhere in its file
(``ast.walk`` + first match), so in a module with several classes every
``__init__``/``run``/``update`` after the first inherited the first one's
``self`` reads/writes and call sites, and a module-level function shadowed
a same-named method. The hidden-state rules key off these edges, so the
translation depended on class order.

Fixtures are real on-disk files driven through the public orchestration
API (no mocks).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cogant.api.bundle import Bundle
from cogant.api.orchestration import run_graph
from cogant.ingest.repo import RepoIngester
from cogant.schemas.core import EdgeKind

pytestmark = pytest.mark.unit

_PASSIVE = (
    "class Passive:\n"
    "    def __init__(self):\n"
    "        pass\n"
    "\n"
    "    def run(self):\n"
    "        return helper()\n"
)
_STATEFUL = (
    "class Stateful:\n"
    "    def __init__(self):\n"
    "        self.belief = 0\n"
    "\n"
    "    def update(self, observation):\n"
    "        self.belief = observation\n"
    "\n"
    "    def run(self):\n"
    "        return other()\n"
)
_HELPERS = "def helper():\n    return 1\n\n\ndef other():\n    return 2\n"


def _graph(tmp_path: Path, source: str):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "agents.py").write_text(source, encoding="utf-8")
    bundle = Bundle(target=str(repo))
    bundle.artifacts["repo_snapshot"] = RepoIngester().ingest_local(repo, include_test_files=False)
    run_graph(bundle, str(repo))
    return bundle.artifacts["_program_graph"]


def _edges(pg, kind: EdgeKind) -> set[tuple[str, str]]:
    return {
        (pg.nodes[e.source_id].qualified_name, pg.nodes[e.target_id].qualified_name)
        for e in pg.edges.values()
        if e.kind == kind
    }


@pytest.mark.parametrize("passive_first", [True, False])
def test_dataflow_edges_do_not_depend_on_class_order(tmp_path: Path, passive_first: bool) -> None:
    body = _PASSIVE + "\n\n" + _STATEFUL if passive_first else _STATEFUL + "\n\n" + _PASSIVE
    pg = _graph(tmp_path, body + "\n\n" + _HELPERS)

    assert _edges(pg, EdgeKind.WRITES) == {
        ("agents.Stateful.__init__", "agents.Stateful"),
        ("agents.Stateful.update", "agents.Stateful"),
    }
    assert _edges(pg, EdgeKind.READS) == set()


@pytest.mark.parametrize("passive_first", [True, False])
def test_call_edges_come_from_the_callers_own_body(tmp_path: Path, passive_first: bool) -> None:
    body = _PASSIVE + "\n\n" + _STATEFUL if passive_first else _STATEFUL + "\n\n" + _PASSIVE
    pg = _graph(tmp_path, body + "\n\n" + _HELPERS)

    assert _edges(pg, EdgeKind.CALLS) == {
        ("agents.Passive.run", "agents.helper"),
        ("agents.Stateful.run", "agents.other"),
    }


def test_module_function_does_not_shadow_same_named_method(tmp_path: Path) -> None:
    source = (
        "def update():\n"
        "    return 0\n"
        "\n\n"
        "class Tracker:\n"
        "    def update(self, value):\n"
        "        self.last = value\n"
        "        return self.last\n"
    )
    pg = _graph(tmp_path, source)

    assert _edges(pg, EdgeKind.WRITES) == {("agents.Tracker.update", "agents.Tracker")}
    assert _edges(pg, EdgeKind.READS) == {("agents.Tracker.update", "agents.Tracker")}
