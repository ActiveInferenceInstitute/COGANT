"""Ignore/skip directory names must be matched below the repository root only.

A repository checked out under a directory that happens to be called
``build``, ``dist``, ``target``, ``venv`` or ``node_modules`` (CI
workspaces such as ``/workspace/build/<repo>`` are common) must still be
ingested. Only directories *inside* the repository with those names are
noise to skip.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cogant.ingest.files import FileEnumerator
from cogant.ingest.repo_sniff import RepoSniffer, count_source_files


def _repo_under(parent_name: str, tmp_path: Path) -> Path:
    repo = tmp_path / parent_name / "project"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg" / "core.py").write_text("x = 1\n", encoding="utf-8")
    # A genuinely ignorable directory *inside* the repository.
    (repo / "build").mkdir()
    (repo / "build" / "generated.py").write_text("y = 2\n", encoding="utf-8")
    return repo


@pytest.mark.parametrize("parent_name", ["build", "dist", "target", "venv", "node_modules"])
def test_file_enumerator_ingests_repo_located_under_ignored_dir_name(
    tmp_path: Path, parent_name: str
) -> None:
    repo = _repo_under(parent_name, tmp_path)

    files = FileEnumerator(repo, respect_gitignore=False).enumerate()

    assert [f.relative_path for f in files] == [str(Path("pkg") / "core.py")]


def test_file_enumerator_ingests_repo_whose_root_is_named_like_ignored_dir(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "dist"
    repo.mkdir()
    (repo / "main.py").write_text("print('hi')\n", encoding="utf-8")

    files = FileEnumerator(repo, respect_gitignore=False).enumerate()

    assert [f.relative_path for f in files] == ["main.py"]


@pytest.mark.parametrize("parent_name", ["build", "dist", "target", "venv", "node_modules"])
def test_repo_sniff_counts_repo_located_under_skip_dir_name(
    tmp_path: Path, parent_name: str
) -> None:
    repo = _repo_under(parent_name, tmp_path)

    assert count_source_files(repo) == 1
    sniff = RepoSniffer(repo).sniff()
    assert sniff["source_file_count"] == 1
    assert sniff["languages"] == {"python": 1}
