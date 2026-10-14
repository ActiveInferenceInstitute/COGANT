"""Incremental change detection must report real paths below ``repo_path``.

``git diff --name-status`` and ``git status --porcelain`` print paths
relative to the *repository top level* and C-quote names with non-ASCII
bytes. When the analysed directory is a subdirectory of the git work
tree (a package inside a monorepo, e.g. COGANT's own nested ``cogant/``)
joining those strings onto ``repo_path`` produced paths that do not
exist, and quoted names lost their source suffix, so incremental runs
silently dropped changed files.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from cogant.ingest.incremental import IncrementalIngester, get_changed_files

pytestmark = pytest.mark.unit


def _git(repo: Path, *args: str) -> str:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        }
    )
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True, env=env
    ).stdout


@pytest.fixture
def monorepo(tmp_path: Path) -> Path:
    """A git work tree whose analysable package lives in ``packages/core``."""
    _git(tmp_path, "init", "-q", "-b", "main")
    pkg = tmp_path / "packages" / "core"
    pkg.mkdir(parents=True)
    (pkg / "engine.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "tooling.py").write_text("y = 1\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "initial")
    return tmp_path


def test_changed_since_in_subdirectory_reports_existing_paths_below_it(monorepo: Path) -> None:
    pkg = monorepo / "packages" / "core"
    (pkg / "engine.py").write_text("x = 2\n", encoding="utf-8")
    (monorepo / "tooling.py").write_text("y = 2\n", encoding="utf-8")
    _git(monorepo, "commit", "-q", "-am", "edit")

    changes = IncrementalIngester(pkg).changed_since("HEAD~1")

    assert [(c.path, c.change_type) for c in changes] == [(pkg / "engine.py", "M")]
    assert all(c.path.exists() for c in changes)
    assert get_changed_files(pkg, "HEAD~1") == [pkg / "engine.py"]


def test_working_tree_changes_in_subdirectory_reports_existing_paths(monorepo: Path) -> None:
    pkg = monorepo / "packages" / "core"
    (pkg / "engine.py").write_text("x = 3\n", encoding="utf-8")
    (monorepo / "tooling.py").write_text("y = 3\n", encoding="utf-8")

    changes = IncrementalIngester(pkg).working_tree_changes()

    assert [(c.path, c.change_type) for c in changes] == [(pkg / "engine.py", "M")]


def test_non_ascii_source_names_keep_their_suffix(monorepo: Path) -> None:
    pkg = monorepo / "packages" / "core"
    (pkg / "café.py").write_text("z = 1\n", encoding="utf-8")
    _git(monorepo, "add", ".")
    _git(monorepo, "commit", "-q", "-m", "add non-ascii module")

    changed = IncrementalIngester(pkg).source_files_changed_since("HEAD~1")

    assert changed == [pkg / "café.py"]
    assert changed[0].exists()


def test_repository_root_paths_are_unchanged(monorepo: Path) -> None:
    (monorepo / "tooling.py").write_text("y = 4\n", encoding="utf-8")
    _git(monorepo, "commit", "-q", "-am", "edit root")

    changes = IncrementalIngester(monorepo).changed_since("HEAD~1")

    assert [(c.path, c.change_type) for c in changes] == [(monorepo / "tooling.py", "M")]
