"""``RepoIngester.ingest_git_remote`` must never delete directories it did not create.

The clone destination used to be ``work_dir / <last URL component>``. A
pre-existing directory with that name (the user's own checkout when
``work_dir`` is a working directory, or a concurrent ingest of another
repository with the same basename in the shared default work dir) was
removed with ``shutil.rmtree`` before cloning, and again on cleanup.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from cogant.ingest.repo import RepoIngester

pytestmark = pytest.mark.unit


def _git(repo: Path, *args: str) -> None:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        }
    )
    subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True, env=env)


@pytest.fixture
def upstream_repo(tmp_path: Path) -> Path:
    upstream = tmp_path / "remote" / "project"
    upstream.mkdir(parents=True)
    _git(upstream, "init", "-q", "-b", "main")
    (upstream / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    _git(upstream, "add", ".")
    _git(upstream, "commit", "-q", "-m", "initial")
    return upstream


def test_clone_does_not_remove_preexisting_same_named_directory(
    tmp_path: Path, upstream_repo: Path
) -> None:
    work_dir = tmp_path / "work"
    existing = work_dir / "project"
    existing.mkdir(parents=True)
    sentinel = existing / "unsaved_notes.txt"
    sentinel.write_text("keep me", encoding="utf-8")

    snapshot = RepoIngester(work_dir=work_dir).ingest_git_remote(upstream_repo.as_uri())

    assert sentinel.read_text(encoding="utf-8") == "keep me"
    assert [f.relative_path for f in snapshot.files] == ["app.py"]
    assert snapshot.metadata.name == "project"
    assert snapshot.metadata.url == upstream_repo.as_uri()


def test_cleanup_removes_only_the_clone(tmp_path: Path, upstream_repo: Path) -> None:
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    (work_dir / "other.txt").write_text("untouched", encoding="utf-8")

    RepoIngester(work_dir=work_dir).ingest_git_remote(upstream_repo.as_uri(), cleanup=True)

    assert sorted(p.name for p in work_dir.iterdir()) == ["other.txt"]


def test_no_cleanup_keeps_clone_at_snapshot_root(tmp_path: Path, upstream_repo: Path) -> None:
    work_dir = tmp_path / "work"

    snapshot = RepoIngester(work_dir=work_dir).ingest_git_remote(
        upstream_repo.as_uri(), cleanup=False
    )

    assert (snapshot.root_path / "app.py").is_file()
    assert snapshot.root_path.is_relative_to(work_dir.resolve())
