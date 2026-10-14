"""An incremental run after a source edit must still describe the whole repo.

The incremental cache stores JSON stage results only, so there is no
per-file merge of the program graph, mappings, or state space. A partial
cache hit (some files changed since the cached snapshot) therefore has to
re-analyse the full snapshot; restricting ingest to the changed subset used
to rebuild every downstream stage from that subset alone, silently dropping
every unchanged file from the model and then caching the reduced bundle as
the next run's "full hit".

Every test drives the real ``PipelineRunner`` against a real on-disk git
repository; cache state is isolated under ``tmp_path``.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from cogant.api.bundle import Bundle
from cogant.api.orchestration import run_ingest
from cogant.api.pipeline import PipelineConfig, PipelineRunner

pytestmark = pytest.mark.unit

_STAGEFUL_CLASS = (
    "class Agent{index}:\n"
    "    def __init__(self):\n"
    "        self.belief = 0\n"
    "\n"
    "    def step(self, observation):\n"
    "        self.belief = observation\n"
    "        return self.belief\n"
)


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
def four_module_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    for index in range(4):
        (repo / f"agent{index}.py").write_text(_STAGEFUL_CLASS.format(index=index))
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "initial")
    return repo


def _config(tmp_path: Path, since: str) -> PipelineConfig:
    return PipelineConfig(
        incremental_since=since,
        cache_dir=str(tmp_path / "cache"),
        output_dir=str(tmp_path / "out"),
        skip_stages=["dynamic", "export", "validate"],
    )


def _graph_paths(bundle: Bundle) -> set[str]:
    return {node["path"] for node in bundle.stage_results["graph"]["nodes"].values()}


def _edit_and_commit(repo: Path) -> None:
    target = repo / "agent0.py"
    target.write_text(target.read_text() + "\n\ndef helper():\n    return 1\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "edit agent0")


def test_partial_change_rebuilds_model_over_every_file(
    four_module_repo: Path, tmp_path: Path
) -> None:
    runner = PipelineRunner()
    cold = runner.run(str(four_module_repo), _config(tmp_path, "HEAD"))
    assert cold.stage_results["ingest"]["file_count"] == 4

    _edit_and_commit(four_module_repo)
    partial = runner.run(str(four_module_repo), _config(tmp_path, "HEAD~1"))
    fresh = PipelineRunner().run(
        str(four_module_repo),
        PipelineConfig(
            output_dir=str(tmp_path / "out_fresh"),
            skip_stages=["dynamic", "export", "validate"],
        ),
    )

    assert partial.stage_results["ingest"]["file_count"] == 4
    assert _graph_paths(partial) == {f"agent{index}.py" for index in range(4)}
    assert len(partial.stage_results["graph"]["nodes"]) == len(
        fresh.stage_results["graph"]["nodes"]
    )
    assert (
        partial.stage_results["translate"]["mapping_count"]
        == fresh.stage_results["translate"]["mapping_count"]
    )
    # The edit added a function, so the model grew relative to the cold run.
    assert len(partial.stage_results["graph"]["nodes"]) > len(cold.stage_results["graph"]["nodes"])

    stats = partial.metadata["incremental_stats"]
    assert stats["files_changed"] == 1
    # Nothing from the cached bundle is reused on a partial change, and every
    # file is re-analysed; the stats must say so rather than claim a hit.
    assert stats["cache_hit"] is False
    assert stats["files_reparsed"] == stats["files_total"] == 4


def test_full_hit_after_partial_change_returns_whole_model(
    four_module_repo: Path, tmp_path: Path
) -> None:
    runner = PipelineRunner()
    runner.run(str(four_module_repo), _config(tmp_path, "HEAD"))
    _edit_and_commit(four_module_repo)
    runner.run(str(four_module_repo), _config(tmp_path, "HEAD~1"))

    warm = runner.run(str(four_module_repo), _config(tmp_path, "HEAD"))

    assert warm.metadata["incremental_stats"]["cache_hit"] is True
    assert warm.stage_results["ingest"]["file_count"] == 4
    assert _graph_paths(warm) == {f"agent{index}.py" for index in range(4)}


def test_partial_change_does_not_carry_cached_errors(
    four_module_repo: Path, tmp_path: Path
) -> None:
    runner = PipelineRunner()
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory\n")
    failing = PipelineConfig(
        incremental_since="HEAD",
        cache_dir=str(tmp_path / "cache"),
        output_dir=str(blocker),
        skip_stages=["dynamic", "validate"],
        render_visualizations=False,
    )
    first = runner.run(str(four_module_repo), failing)
    assert any("Stage export failed" in error for error in first.errors)

    _edit_and_commit(four_module_repo)
    healthy = failing.model_copy(
        update={"incremental_since": "HEAD~1", "output_dir": str(tmp_path / "out2")}
    )
    second = runner.run(str(four_module_repo), healthy)

    assert second.stage_outcomes["export"].value == "success"
    assert second.errors == []


def test_run_ingest_keeps_every_file_when_change_records_are_present(
    four_module_repo: Path,
) -> None:
    bundle = Bundle(target=str(four_module_repo))
    bundle.metadata["_incremental"] = {
        "changed_files": [str(four_module_repo / "agent0.py")],
        "changed_count": 1,
    }

    result = run_ingest(str(four_module_repo), bundle)

    assert result["file_count"] == 4
    assert result["incremental"]["changed_count"] == 1
    remaining = {Path(f.path).name for f in bundle.artifacts["repo_snapshot"].files}
    assert remaining == {f"agent{index}.py" for index in range(4)}
