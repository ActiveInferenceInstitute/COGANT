"""Tests for the tree-sitter universal parser substrate.

These tests assume the ``multilang`` optional extras may or may not be
installed and gate themselves on ``tree_sitter`` importability. The
incremental ingester tests are always active because they exercise the
non-git fallback path with no external dependencies.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

try:
    import tree_sitter  # noqa: F401

    HAS_TREE_SITTER = True
except ImportError:  # pragma: no cover - exercised only without the dep
    HAS_TREE_SITTER = False


# ---------------------------------------------------------------------------
# Tree-sitter parser
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_TREE_SITTER, reason="tree-sitter not installed")
def test_parser_loads_available_languages():
    from cogant.parsers.tree_sitter_base import get_tree_sitter_parser

    parser = get_tree_sitter_parser()
    available = parser.available_languages()
    # At least one grammar must be loaded in the CI/dev environment for
    # the multilang pathway to be meaningful.
    assert available  # at least one grammar loaded
    assert parser.supported_extensions()  # derived mapping non-empty


@pytest.mark.skipif(not HAS_TREE_SITTER, reason="tree-sitter not installed")
def test_python_parse_simple_function():
    from cogant.parsers.tree_sitter_base import get_tree_sitter_parser

    parser = get_tree_sitter_parser()
    if "python" not in parser.available_languages():
        pytest.skip("tree_sitter_python grammar not available")
    result = parser.parse_source("def foo(x):\n    return x + 1\n", "python", "foo.py")
    assert result is not None
    assert any(s.name == "foo" and s.kind == "function" for s in result.symbols)


@pytest.mark.skipif(not HAS_TREE_SITTER, reason="tree-sitter not installed")
def test_python_parse_class_and_method():
    from cogant.parsers.tree_sitter_base import get_tree_sitter_parser

    parser = get_tree_sitter_parser()
    if "python" not in parser.available_languages():
        pytest.skip("tree_sitter_python grammar not available")
    source = "class MyClass:\n    def method(self):\n        return helper()\n"
    result = parser.parse_source(source, "python", "m.py")
    kinds = {s.kind for s in result.symbols}
    assert "class" in kinds
    assert "method" in kinds
    qnames = {s.qualified_name for s in result.symbols}
    assert "MyClass.method" in qnames


@pytest.mark.skipif(not HAS_TREE_SITTER, reason="tree-sitter not installed")
def test_python_extract_imports_and_calls():
    from cogant.parsers.tree_sitter_base import get_tree_sitter_parser

    parser = get_tree_sitter_parser()
    if "python" not in parser.available_languages():
        pytest.skip("tree_sitter_python grammar not available")
    source = "import os\nfrom typing import List\ndef f():\n    return os.path.join('a', 'b')\n"
    result = parser.parse_source(source, "python", "f.py")
    assert any("import os" in imp["raw"] for imp in result.imports)
    assert any("typing" in imp["raw"] for imp in result.imports)
    assert any("os.path.join" in call["callee"] for call in result.calls)


@pytest.mark.skipif(not HAS_TREE_SITTER, reason="tree-sitter not installed")
def test_parse_file_roundtrip(tmp_path):
    from cogant.parsers.tree_sitter_base import get_tree_sitter_parser

    parser = get_tree_sitter_parser()
    if "python" not in parser.available_languages():
        pytest.skip("tree_sitter_python grammar not available")
    file_path = tmp_path / "example.py"
    file_path.write_text("def hi():\n    return 1\n", encoding="utf-8")
    result = parser.parse_file(file_path)
    assert result is not None
    assert result.language == "python"
    assert any(s.name == "hi" for s in result.symbols)


@pytest.mark.skipif(not HAS_TREE_SITTER, reason="tree-sitter not installed")
def test_parse_file_unknown_language(tmp_path):
    from cogant.parsers.tree_sitter_base import get_tree_sitter_parser

    parser = get_tree_sitter_parser()
    unknown = tmp_path / "script.xyz"
    unknown.write_text("ignored", encoding="utf-8")
    assert parser.parse_file(unknown) is None


@pytest.mark.skipif(not HAS_TREE_SITTER, reason="tree-sitter not installed")
def test_parse_source_unknown_language_returns_none():
    from cogant.parsers.tree_sitter_base import get_tree_sitter_parser

    parser = get_tree_sitter_parser()
    assert parser.parse_source("whatever", "klingon", "k.kg") is None


# ---------------------------------------------------------------------------
# Incremental ingester — git-free paths
# ---------------------------------------------------------------------------


def test_incremental_ingester_not_git_repo(tmp_path):
    from cogant.ingest.incremental import IncrementalIngester

    ingester = IncrementalIngester(tmp_path)
    assert ingester.is_git_repo() is False
    assert ingester.changed_since("HEAD~1") == []
    assert ingester.changed_since_commit("abc123") == []


def test_incremental_ingester_working_tree_non_git(tmp_path):
    from cogant.ingest.incremental import IncrementalIngester

    ingester = IncrementalIngester(tmp_path)
    assert ingester.working_tree_changes() == []


def test_incremental_ingester_python_files_non_git(tmp_path):
    from cogant.ingest.incremental import IncrementalIngester

    ingester = IncrementalIngester(tmp_path)
    assert ingester.python_files_changed_since("HEAD~1") == []
    assert ingester.source_files_changed_since("HEAD~1") == []


def test_incremental_ingester_missing_path():
    from cogant.ingest.incremental import IncrementalIngester

    ingester = IncrementalIngester(Path("/definitely/not/a/real/path/for/cogant"))
    assert ingester.is_git_repo() is False
    assert ingester.changed_since() == []


# ---------------------------------------------------------------------------
# Incremental ingester — real git repo
# ---------------------------------------------------------------------------


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


def _have_git() -> bool:
    try:
        subprocess.run(["git", "--version"], capture_output=True, text=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


HAS_GIT = _have_git()


@pytest.mark.skipif(not HAS_GIT, reason="git CLI not available")
def test_incremental_ingester_real_git_repo(tmp_path):
    from cogant.ingest.incremental import ChangedFile, IncrementalIngester

    repo = tmp_path / "demo"
    repo.mkdir()
    _git("init", "-q", cwd=repo)
    _git("config", "user.email", "t@t.t", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)
    # Deterministic default branch regardless of git version defaults
    _git("checkout", "-q", "-b", "main", cwd=repo)

    (repo / "a.py").write_text("def a(): return 1\n", encoding="utf-8")
    _git("add", "a.py", cwd=repo)
    _git("commit", "-q", "-m", "first", cwd=repo)

    (repo / "b.py").write_text("def b(): return 2\n", encoding="utf-8")
    (repo / "a.py").write_text("def a(): return 99\n", encoding="utf-8")
    _git("add", "a.py", "b.py", cwd=repo)
    _git("commit", "-q", "-m", "second", cwd=repo)

    ingester = IncrementalIngester(repo)
    assert ingester.is_git_repo()

    changes = ingester.changed_since("HEAD~1")
    assert isinstance(changes, list)
    change_paths = {c.path.name for c in changes}
    assert "b.py" in change_paths
    assert "a.py" in change_paths
    for c in changes:
        assert isinstance(c, ChangedFile)
        assert c.change_type in {"A", "M", "D", "R", "C", "T", "U"}

    pyfiles = ingester.python_files_changed_since("HEAD~1")
    assert any(p.name == "a.py" for p in pyfiles)
    assert any(p.name == "b.py" for p in pyfiles)

    # Working tree changes: add an unstaged modification and see it.
    (repo / "a.py").write_text("def a(): return 123\n", encoding="utf-8")
    wt = ingester.working_tree_changes()
    assert any(c.path.name == "a.py" for c in wt)
