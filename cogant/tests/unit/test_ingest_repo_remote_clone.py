"""Targeted unit tests for: exercise cogant.ingest.repo.RepoIngester.ingest_git_remote.

Drives the git-clone path against a local ``file://`` URL created with
real ``git init`` + ``git commit`` — this exercises the happy-path clone
logic, the metadata extraction, and the cleanup/finally block without
needing network access.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from cogant.ingest.repo import RepoIngester


def _make_local_git_repo(dst: Path) -> Path:
    """Initialise a tiny real git repository at ``dst`` and return it."""
    dst.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=dst, check=True, capture_output=True)
    (dst / "README.md").write_text("# hello\n")
    (dst / "main.py").write_text("def main() -> None:\n    return None\n")
    subprocess.run(["git", "add", "."], cwd=dst, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=ci@example.com",
            "-c",
            "user.name=CI",
            "commit",
            "-m",
            "initial commit",
        ],
        cwd=dst,
        check=True,
        capture_output=True,
    )
    return dst


class TestRepoIngesterCloneRemote:
    """Drive RepoIngester.ingest_git_remote against a local file:// URL."""

    def test_ingest_git_remote_clones_local_file_url(self, tmp_path: Path) -> None:
        src_repo = _make_local_git_repo(tmp_path / "src_repo")
        work_dir = tmp_path / "work"
        ingester = RepoIngester(work_dir=work_dir)

        snapshot = ingester.ingest_git_remote(
            f"file://{src_repo}",
            cleanup=True,
        )
        # URL stamped back onto metadata
        assert snapshot.metadata.url == f"file://{src_repo}"
        # main.py got ingested (README.md is skipped by default language filter)
        paths = {str(f.path) for f in snapshot.files}
        assert any(p.endswith("main.py") for p in paths), paths
        # Snapshot carries the temp clone dir path in metadata originally
        # but url is overwritten to the source URL
        assert "file://" in snapshot.metadata.url
        # Cleanup worked — the clone directory is gone
        cloned = work_dir / "src_repo"
        assert not cloned.exists()

    def test_ingest_git_remote_without_cleanup_keeps_clone(self, tmp_path: Path) -> None:
        src_repo = _make_local_git_repo(tmp_path / "src_repo2")
        work_dir = tmp_path / "work2"
        ingester = RepoIngester(work_dir=work_dir)

        snapshot = ingester.ingest_git_remote(
            f"file://{src_repo}",
            cleanup=False,
        )
        assert snapshot.metadata.url == f"file://{src_repo}"
        cloned = work_dir / "src_repo2"
        # Clone is preserved on disk
        assert cloned.exists() and cloned.is_dir()

    def test_ingest_git_remote_reclones_over_existing_dir(self, tmp_path: Path) -> None:
        """If the target clone dir already exists it must be wiped first."""
        src_repo = _make_local_git_repo(tmp_path / "src_repo3")
        work_dir = tmp_path / "work3"
        existing = work_dir / "src_repo3"
        existing.mkdir(parents=True, exist_ok=True)
        # Place a file that must be wiped by the rmtree branch
        sentinel = existing / "old_file.txt"
        sentinel.write_text("old")
        assert sentinel.exists()

        ingester = RepoIngester(work_dir=work_dir)
        snapshot = ingester.ingest_git_remote(
            f"file://{src_repo}",
            cleanup=False,
        )
        assert snapshot.metadata.url == f"file://{src_repo}"
        # After clone the sentinel must be gone (pre-existing dir wiped)
        assert not sentinel.exists()
        # And the cloned README must now be in place
        assert (existing / "README.md").exists()

    def test_ingest_git_remote_on_invalid_url_raises(self, tmp_path: Path) -> None:
        """A non-existent remote URL surfaces as RuntimeError from subprocess."""
        ingester = RepoIngester(work_dir=tmp_path / "work4")
        with pytest.raises(RuntimeError):
            ingester.ingest_git_remote(
                "file:///definitely/not/a/real/repo/anywhere_xyz",
                cleanup=True,
            )
