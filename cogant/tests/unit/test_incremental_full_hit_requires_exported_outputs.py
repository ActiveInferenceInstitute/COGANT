"""A no-change incremental run may only short-circuit when its outputs exist.

``output_dir`` is deliberately excluded from the incremental cache key, and
a full cache hit returns the cached bundle without running any stage. That
is only sound when the cached export already wrote its artifacts into the
requested output directory and the cached run did not record stage
exceptions. Otherwise ``--incremental HEAD -o newdir`` produced no
artifacts, deleted outputs were never regenerated, and a transient failure
(for example an unwritable output path) was replayed from the cache on
every later run instead of being retried.

Every test drives the real ``PipelineRunner`` against a real on-disk git
repository; cache state is isolated under ``tmp_path``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from cogant.api.bundle import StageOutcome
from cogant.api.pipeline import PipelineConfig, PipelineRunner

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
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, env=env)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "agent.py").write_text(
        "class Agent:\n"
        "    def __init__(self):\n"
        "        self.belief = 0\n"
        "\n"
        "    def step(self, observation):\n"
        "        self.belief = observation\n"
        "        return self.belief\n"
    )
    _git(root, "init", "-q", "-b", "main")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "initial")
    return root


def _config(tmp_path: Path, output_dir: Path) -> PipelineConfig:
    return PipelineConfig(
        incremental_since="HEAD",
        cache_dir=str(tmp_path / "cache"),
        output_dir=str(output_dir),
        skip_stages=["dynamic", "validate"],
        render_visualizations=False,
    )


def test_no_change_run_into_new_output_dir_exports_artifacts(repo: Path, tmp_path: Path) -> None:
    runner = PipelineRunner()
    runner.run(str(repo), _config(tmp_path, tmp_path / "out1"))

    second = runner.run(str(repo), _config(tmp_path, tmp_path / "out2"))

    assert (tmp_path / "out2" / "program_graph.json").is_file()
    assert (tmp_path / "out2" / "gnn_package").is_dir()
    assert second.stage_outcomes["export"] is StageOutcome.SUCCESS
    assert second.stage_results["export"]["output_dir"] == str(tmp_path / "out2")


def test_no_change_run_regenerates_deleted_outputs(repo: Path, tmp_path: Path) -> None:
    runner = PipelineRunner()
    out = tmp_path / "out"
    runner.run(str(repo), _config(tmp_path, out))
    shutil.rmtree(out)

    runner.run(str(repo), _config(tmp_path, out))

    assert (out / "program_graph.json").is_file()


def test_no_change_run_retries_a_cached_stage_failure(repo: Path, tmp_path: Path) -> None:
    runner = PipelineRunner()
    blocker = tmp_path / "blocker"
    blocker.write_text("a file where the output directory should be\n")
    first = runner.run(str(repo), _config(tmp_path, blocker))
    assert first.stage_outcomes["export"] is StageOutcome.FAILED

    out = tmp_path / "out"
    second = runner.run(str(repo), _config(tmp_path, out))

    assert second.errors == []
    assert second.stage_outcomes["export"] is StageOutcome.SUCCESS
    assert (out / "program_graph.json").is_file()


def test_no_change_run_with_existing_outputs_is_still_a_full_hit(
    repo: Path, tmp_path: Path
) -> None:
    runner = PipelineRunner()
    out = tmp_path / "out"
    runner.run(str(repo), _config(tmp_path, out))

    second = runner.run(str(repo), _config(tmp_path, out))

    stats = second.metadata["incremental_stats"]
    assert stats["cache_hit"] is True
    assert stats["files_reparsed"] == 0
    assert second.stage_outcomes["export"] is StageOutcome.SUCCESS


def test_no_change_run_accepts_outputs_relocated_by_layout_output(
    repo: Path, tmp_path: Path
) -> None:
    runner = PipelineRunner()
    out = tmp_path / "out"
    config = _config(tmp_path, out).model_copy(update={"layout_output": True})
    runner.run(str(repo), config)
    assert (out / "data" / "program_graph.json").is_file()

    second = runner.run(str(repo), config)

    assert second.metadata["incremental_stats"]["cache_hit"] is True
