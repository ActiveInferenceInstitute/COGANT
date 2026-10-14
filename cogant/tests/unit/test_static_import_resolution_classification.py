"""ImportAnalyzer resolves imports to the module file Python would load.

Relative imports resolve against the importing package (walking up one
directory per extra leading dot), dotted standard-library imports are
classified by their top-level package, and absolute imports of in-repo
modules resolve against ``repo_root`` instead of being called third-party.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cogant.static.imports import ImportAnalyzer, ImportEdge


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    pkg = tmp_path / "pkg"
    (pkg / "sub").mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "sibling.py").write_text("def helper():\n    return 1\n")
    (pkg / "sub" / "__init__.py").write_text("")
    (pkg / "user.py").write_text(
        "import os.path\n"
        "import collections.abc\n"
        "from concurrent.futures import ThreadPoolExecutor\n"
        "import pkg.sibling\n"
        "from .sibling import helper\n"
        "from . import sibling\n"
        "from .os import thing\n"
        "import requests\n"
    )
    (pkg / "sub" / "deep.py").write_text(
        "from ..sibling import helper\nfrom .. import user\nfrom . import not_a_module\n"
    )
    return tmp_path


def _by_line(edges: list[ImportEdge]) -> dict[int, ImportEdge]:
    return {e.line_num: e for e in edges}


@pytest.mark.unit
def test_dotted_stdlib_imports_are_stdlib(repo: Path) -> None:
    edges = _by_line(ImportAnalyzer(repo_root=repo).analyze_file(repo / "pkg" / "user.py"))

    for line in (1, 2, 3):
        assert edges[line].is_stdlib is True, edges[line].module_name
        assert edges[line].is_third_party is False
        assert edges[line].is_local is False


@pytest.mark.unit
def test_relative_imports_resolve_to_the_named_module(repo: Path) -> None:
    edges = _by_line(ImportAnalyzer(repo_root=repo).analyze_file(repo / "pkg" / "user.py"))

    assert edges[5].resolved_file == repo / "pkg" / "sibling.py"
    assert edges[6].resolved_file == repo / "pkg" / "sibling.py"
    # A relative module that happens to share a stdlib name is not stdlib.
    assert edges[7].is_stdlib is False
    assert edges[7].is_third_party is False


@pytest.mark.unit
def test_parent_relative_imports_walk_up_one_package_per_dot(repo: Path) -> None:
    analyzer = ImportAnalyzer(repo_root=repo)
    edges = _by_line(analyzer.analyze_file(repo / "pkg" / "sub" / "deep.py"))

    assert edges[1].resolved_file == repo / "pkg" / "sibling.py"
    assert edges[2].resolved_file == repo / "pkg" / "user.py"
    # ``from . import name`` without a submodule falls back to the package.
    assert edges[3].resolved_file == repo / "pkg" / "sub" / "__init__.py"
    assert all(edge.is_local for edge in edges.values())


@pytest.mark.unit
def test_absolute_in_repo_import_is_local_not_third_party(repo: Path) -> None:
    edges = _by_line(ImportAnalyzer(repo_root=repo).analyze_file(repo / "pkg" / "user.py"))

    assert edges[4].is_local is True
    assert edges[4].is_third_party is False
    assert edges[4].resolved_file == repo / "pkg" / "sibling.py"
    assert edges[8].is_third_party is True
    assert edges[8].is_local is False
