"""Regression tests for dotted-import package-qualified module keying.

TODO #2 "Improve graph normalization around imports" — the iter-4 review
landed a partial fix (IMPORTS edges no longer read non-existent ``ImportDef``
fields), but the matching heuristic still keyed ``module_nodes`` by bare
file stem, so dotted imports under a multi-package repo under-linked:

    ``from pkg.deep import X``  — fell through because ``module_nodes["pkg"]``
                                  was indexed by stem, not by package path

This module pins the post-fix behaviour with three end-to-end cases:

1. ``from pkg.deep.x import …`` → IMPORTS edge to ``pkg.deep.x``
2. ``import pkg.util as u``    → IMPORTS edge to ``pkg.util``
3. Single-level ``import foo`` → IMPORTS edge to ``foo`` (compatibility path)

The fixture uses a real on-disk repo snapshot via ``RepoIngester`` because the
project's no-mocks policy precludes synthetic ``RepoSnapshot`` objects.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cogant.api.bundle import Bundle
from cogant.api.orchestration import run_graph
from cogant.ingest.repo import RepoIngester


def _write(repo: Path, rel_path: str, body: str) -> None:
    """Write ``body`` to ``repo / rel_path``, creating parents."""
    full = repo / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(body, encoding="utf-8")


@pytest.fixture
def dotted_repo(tmp_path: Path) -> Path:
    """Build a small package layout exercising dotted imports.

    Layout:
        pkg/__init__.py
        pkg/util.py
        pkg/deep/__init__.py
        pkg/deep/x.py
        consumer.py
            from pkg.deep import x
            from pkg.deep.x import value
            import pkg.util
    """
    repo = tmp_path / "dotted_repo"
    _write(repo, "pkg/__init__.py", "")
    _write(repo, "pkg/util.py", "VALUE = 1\n")
    _write(repo, "pkg/deep/__init__.py", "")
    _write(repo, "pkg/deep/x.py", "value = 'hello'\n")
    _write(
        repo,
        "consumer.py",
        "from pkg.deep import x\n"
        "from pkg.deep.x import value\n"
        "import pkg.util as u\n"
        "RESULT = (x, value, u.VALUE)\n",
    )
    return repo


def _build_graph(repo: Path):
    """Ingest + run_graph through the public orchestration API."""
    bundle = Bundle(target=str(repo))
    ingester = RepoIngester()
    snapshot = ingester.ingest_local(repo, include_test_files=False)
    bundle.artifacts["repo_snapshot"] = snapshot
    run_graph(bundle=bundle, target=str(repo))
    return bundle.artifacts["_program_graph"]


def _modules(pg):
    """Return module nodes from a dict-backed ProgramGraph."""
    return [n for n in pg.nodes.values() if getattr(n.kind, "name", None) == "MODULE"]


def _imports_from(pg, source):
    return [
        e
        for e in pg.edges.values()
        if e.source_id == source.id and getattr(e.kind, "name", None) == "IMPORTS"
    ]


def test_dotted_import_resolves_to_inner_package_module(dotted_repo: Path) -> None:
    """``from pkg.deep import x`` must wire ``consumer`` → ``pkg.deep.x``.

    Pre-fix this missed because ``module_nodes`` was keyed by ``file_path.stem``
    only ("x"), and the match heuristic looked at the first dot-segment ("pkg").
    Post-fix the resolver tries the full dotted target first.
    """
    pg = _build_graph(dotted_repo)
    mods = _modules(pg)
    consumer = next(n for n in mods if n.name == "consumer")
    deep_x = next(n for n in mods if n.qualified_name.endswith("pkg.deep.x"))

    targets = {e.target_id for e in _imports_from(pg, consumer)}
    assert deep_x.id in targets, (
        f"Expected IMPORTS edge from consumer to pkg.deep.x; got targets="
        f"{[pg.nodes[t].qualified_name for t in targets]}"
    )


def test_aliased_import_resolves_to_pkg_util(dotted_repo: Path) -> None:
    """``import pkg.util as u`` must wire ``consumer`` → ``pkg.util``."""
    pg = _build_graph(dotted_repo)
    mods = _modules(pg)
    consumer = next(n for n in mods if n.name == "consumer")
    pkg_util = next(n for n in mods if n.qualified_name.endswith("pkg.util"))
    targets = {e.target_id for e in _imports_from(pg, consumer)}
    assert pkg_util.id in targets, (
        f"Expected IMPORTS edge from consumer to pkg.util; got targets="
        f"{[pg.nodes[t].qualified_name for t in targets]}"
    )


def test_no_self_imports_emitted(dotted_repo: Path) -> None:
    """Sanity: a module never emits an IMPORTS edge to itself."""
    pg = _build_graph(dotted_repo)
    for edge in pg.edges.values():
        if getattr(edge.kind, "name", None) == "IMPORTS":
            assert edge.source_id != edge.target_id


def test_module_qualified_name_is_dotted_package_form(dotted_repo: Path) -> None:
    """``module_node.qualified_name`` must be the dotted package form.

    Pre-fix it was the bare file stem; the fix encodes the full repo-relative
    package path (``__init__.py`` collapses to its package).
    """
    pg = _build_graph(dotted_repo)
    qnames = {n.qualified_name for n in _modules(pg)}
    assert any(q.endswith("pkg.deep.x") for q in qnames)
    assert any(q.endswith("pkg.util") for q in qnames)
    # ``__init__`` files should collapse to their package name, not a node
    # named literally ``__init__``.
    assert not any(q.endswith(".__init__") for q in qnames), (
        f"__init__ leaked as a separate module qname: {qnames}"
    )
