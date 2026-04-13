"""Behavioral tests for the incremental pipeline mode.

These tests exercise the ``--incremental`` CLI wiring, the
``PipelineConfig.incremental_since`` field, the ``PipelineRunner``
cache hit / miss / partial flow, and the public
``get_changed_files`` / ``apply_incremental_patch`` helpers.

Per the project no-mocks policy, every test uses a real git
repository created on-disk with subprocess and drives the real
``PipelineRunner`` against it. Cache state is isolated to per-test
``tmp_path / "cache"`` directories so runs never touch the user's
``~/.cache/cogant``.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from cogant.api.pipeline import PipelineConfig, PipelineRunner
from cogant.ingest.incremental import (
    apply_incremental_patch,
    get_changed_files,
)

pytestmark = pytest.mark.unit


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command inside ``repo`` with deterministic author env."""
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
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=check,
        env=env,
    )


@pytest.fixture
def py_repo(tmp_path: Path) -> Path:
    """A small git-tracked Python "repo" with a stable initial commit."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("def alpha():\n    return 1\n")
    (repo / "b.py").write_text(
        "class B:\n"
        "    def __init__(self):\n"
        "        self.x = 0\n"
        "    def bump(self):\n"
        "        self.x += 1\n"
    )
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "initial")
    return repo


# =====================================================================
# get_changed_files
# =====================================================================


class TestGetChangedFiles:
    def test_returns_empty_on_non_git_path(self, tmp_path: Path):
        result = get_changed_files(tmp_path, "HEAD~1")
        assert result == []

    def test_returns_modified_files_after_new_commit(self, py_repo: Path):
        (py_repo / "a.py").write_text("def alpha():\n    return 2\n")
        _git(py_repo, "add", "-A")
        _git(py_repo, "commit", "-q", "-m", "change alpha")

        changed = get_changed_files(py_repo, "HEAD~1", extensions={".py"})
        names = {p.name for p in changed}
        assert names == {"a.py"}

    def test_extensions_filter_restricts_to_py(self, py_repo: Path):
        (py_repo / "README.md").write_text("# hello\n")
        (py_repo / "c.py").write_text("C = 3\n")
        _git(py_repo, "add", "-A")
        _git(py_repo, "commit", "-q", "-m", "docs and c")

        changed = get_changed_files(py_repo, "HEAD~1", extensions={".py"})
        names = {p.name for p in changed}
        assert "c.py" in names
        assert "README.md" not in names


# =====================================================================
# apply_incremental_patch
# =====================================================================


class TestApplyIncrementalPatch:
    def test_merges_fresh_over_cached(self):
        cached = {"ingest": {"file_count": 10}, "static": {"modules": 10}}
        fresh = {"ingest": {"file_count": 2}, "graph": {"nodes": 5}}
        merged = apply_incremental_patch(cached, fresh, [Path("a.py")])
        assert merged["ingest"] == {"file_count": 2}  # fresh wins
        assert merged["static"] == {"modules": 10}  # cached carried over
        assert merged["graph"] == {"nodes": 5}  # new key added
        assert merged["_incremental_patch"]["changed_count"] == 1

    def test_inputs_not_mutated(self):
        cached = {"ingest": {"file_count": 10}}
        fresh = {"ingest": {"file_count": 2}}
        _ = apply_incremental_patch(cached, fresh, [])
        assert cached == {"ingest": {"file_count": 10}}
        assert fresh == {"ingest": {"file_count": 2}}


# =====================================================================
# PipelineConfig / PipelineRunner incremental wiring
# =====================================================================


class TestPipelineConfigField:
    def test_default_incremental_since_is_none(self):
        cfg = PipelineConfig()
        assert cfg.incremental_since is None
        assert cfg.cache_dir is None

    def test_incremental_since_is_carried_to_bundle_metadata(self, py_repo, tmp_path):
        cache = tmp_path / "cache"
        cfg = PipelineConfig(
            incremental_since="HEAD~1",
            cache_dir=str(cache),
            output_dir=str(tmp_path / "out"),
            skip_stages=["dynamic", "export", "validate"],
        )
        runner = PipelineRunner()
        bundle = runner.run(str(py_repo), cfg)
        stats = bundle.metadata.get("incremental_stats")
        assert stats is not None
        assert stats["enabled"] is True
        assert stats["since"] == "HEAD~1"


class TestIncrementalPreflight:
    def test_non_git_target_records_miss(self, tmp_path: Path):
        # A directory with no git metadata.
        target = tmp_path / "plain"
        target.mkdir()
        (target / "x.py").write_text("pass\n")

        cfg = PipelineConfig(
            incremental_since="HEAD~1",
            cache_dir=str(tmp_path / "cache"),
            output_dir=str(tmp_path / "out"),
            skip_stages=["dynamic", "export", "validate"],
        )
        runner = PipelineRunner()
        bundle = runner.run(str(target), cfg)
        stats = bundle.metadata["incremental_stats"]
        assert stats["cache_hit"] is False
        assert stats["reason"] == "target is not a git repository"

    def test_first_run_miss_then_full_cache_hit(self, py_repo, tmp_path):
        cache = tmp_path / "cache"
        out = tmp_path / "out"
        cfg = PipelineConfig(
            incremental_since="HEAD",
            cache_dir=str(cache),
            output_dir=str(out),
            skip_stages=["dynamic", "export", "validate"],
        )
        runner = PipelineRunner()

        # First run: no cache yet → miss, stats.cache_hit False.
        b1 = runner.run(str(py_repo), cfg)
        assert b1.metadata["incremental_stats"]["cache_hit"] is False
        assert "ingest" in b1.stage_results

        # Second run, no code changes → cache HIT (full).
        b2 = runner.run(str(py_repo), cfg)
        assert b2.metadata["incremental_stats"]["cache_hit"] is True
        assert b2.metadata["incremental_stats"]["files_reparsed"] == 0
        # The cached bundle's stage_results are restored.
        assert "ingest" in b2.stage_results

    def test_partial_hit_reparses_only_changed_files(self, py_repo, tmp_path):
        cache = tmp_path / "cache"
        out = tmp_path / "out"
        cfg = PipelineConfig(
            incremental_since="HEAD~1",
            cache_dir=str(cache),
            output_dir=str(out),
            skip_stages=["dynamic", "export", "validate"],
        )
        runner = PipelineRunner()

        # Seed the cache with a full run against the initial commit.
        runner.run(str(py_repo), cfg)

        # Modify only a.py and commit → exactly one file should be reparsed.
        (py_repo / "a.py").write_text("def alpha():\n    return 99\n")
        _git(py_repo, "add", "-A")
        _git(py_repo, "commit", "-q", "-m", "alpha=99")

        b = runner.run(str(py_repo), cfg)
        stats = b.metadata["incremental_stats"]
        assert stats["cache_hit"] is True
        assert stats["files_reparsed"] == 1
        # The ingest stage should report the filtered subset, not the
        # full repo file count.
        ingest = b.stage_results["ingest"]
        assert ingest["file_count"] == 1
        assert "incremental" in ingest
        assert ingest["incremental"]["changed_count"] == 1


class TestIncrementalOff:
    def test_no_cache_read_or_write_when_disabled(self, py_repo, tmp_path):
        cache = tmp_path / "cache"
        cfg = PipelineConfig(
            incremental_since=None,
            cache_dir=str(cache),
            output_dir=str(tmp_path / "out"),
            skip_stages=["dynamic", "export", "validate"],
        )
        runner = PipelineRunner()
        bundle = runner.run(str(py_repo), cfg)
        # No incremental stats because the feature was off.
        assert "incremental_stats" not in bundle.metadata
        # And the cache directory is untouched.
        if cache.exists():
            assert not any(cache.rglob("*.json"))


class TestOrchestrationFilter:
    def test_ingest_honors_incremental_metadata(self, py_repo, tmp_path):
        """Directly invoke ``run_ingest`` with a pre-populated incremental
        metadata block to confirm the filter runs."""
        from cogant.api.bundle import Bundle
        from cogant.api.orchestration import run_ingest

        bundle = Bundle(target=str(py_repo))
        bundle.metadata["_incremental"] = {
            "changed_files": [str(py_repo / "a.py")],
            "changed_count": 1,
        }
        result = run_ingest(str(py_repo), bundle)
        assert result["file_count"] == 1
        # b.py must have been filtered out
        snapshot = bundle.artifacts["repo_snapshot"]
        remaining = {Path(f.path).name for f in snapshot.files}
        assert remaining == {"a.py"}
