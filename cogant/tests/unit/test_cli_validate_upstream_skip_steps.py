"""``cogant validate --upstream-gnn-skip-steps ''`` runs every upstream step.

The flag's help (shared with translate/analyze and ``cogant upstream-gnn``)
says an empty value means "skip nothing"; validate must not fall back to the
default ``[11, 12]`` skip list in that case.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from typer.testing import CliRunner

from cogant.api.pipeline import PipelineConfig, PipelineRunner
from cogant.cli.main import app


@pytest.fixture()
def run_dir(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "counter.py").write_text(
        "class Counter:\n"
        "    def __init__(self):\n"
        "        self.n = 0\n"
        "    def inc(self):\n"
        "        self.n += 1\n",
        encoding="utf-8",
    )
    out = tmp_path / "run"
    PipelineRunner().run(
        str(repo),
        PipelineConfig(output_dir=str(out), render_visualizations=False, skip_dynamic=True),
    )
    assert (out / "gnn_package" / "manifest.json").is_file()
    return out


@pytest.fixture()
def captured(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    from cogant.gnn.upstream_bridge import pipeline as upstream_pipeline

    configs: list[Any] = []

    def fake_run(cfg: Any) -> Any:
        configs.append(cfg)
        return SimpleNamespace(available=False, error="stubbed for test")

    monkeypatch.setattr(upstream_pipeline, "run_upstream_pipeline", fake_run)
    return configs


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["--upstream-gnn-skip-steps", ""], []),
        (["--upstream-gnn-skip-steps", "3,4"], [3, 4]),
        ([], [11, 12]),
    ],
)
def test_validate_skip_steps_flag(
    run_dir: Path, captured: list[Any], argv: list[str], expected: list[int]
) -> None:
    result = CliRunner().invoke(
        app,
        ["validate", str(run_dir), "--no-upstream-gnn", "--upstream-gnn-pipeline", *argv],
    )

    assert result.exit_code in (0, 1), result.output
    assert len(captured) == 1, result.output
    assert list(captured[0].skip_steps) == expected
