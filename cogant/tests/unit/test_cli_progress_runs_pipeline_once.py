"""The progress spinner never re-runs a pipeline that raised.

``run_pipeline_with_progress`` falls back to a spinner-less run only when the
Rich progress display itself cannot start. An exception from the pipeline run
must propagate after a single attempt instead of running the whole pipeline
a second time.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cogant.api.bundle import Bundle
from cogant.api.pipeline import PipelineConfig, PipelineRunner
from cogant.cli import _app
from cogant.cli.main import app


class _CountingRunner(PipelineRunner):
    def __init__(self, error: BaseException | None = None) -> None:
        super().__init__()
        self.calls = 0
        self.error = error

    def run(self, target: str, config: PipelineConfig | None = None) -> Bundle:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return Bundle(target=target)


def test_pipeline_error_propagates_after_one_run() -> None:
    runner = _CountingRunner(RuntimeError("stage blew up"))
    with pytest.raises(RuntimeError, match="stage blew up"):
        _app.run_pipeline_with_progress(runner, "repo", PipelineConfig())
    assert runner.calls == 1


def test_successful_run_happens_once() -> None:
    runner = _CountingRunner()
    bundle = _app.run_pipeline_with_progress(runner, "repo", PipelineConfig())
    assert bundle.target == "repo"
    assert runner.calls == 1


def test_progress_display_failure_falls_back_to_one_plain_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _BrokenProgress:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise OSError("no terminal")

    monkeypatch.setattr(_app, "Progress", _BrokenProgress)
    runner = _CountingRunner()
    bundle = _app.run_pipeline_with_progress(runner, "repo", PipelineConfig())
    assert bundle.target == "repo"
    assert runner.calls == 1


def test_translate_runs_a_failing_pipeline_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def failing_run(self: PipelineRunner, target: str, config: Any = None) -> Bundle:
        calls.append(target)
        raise PermissionError(target)

    monkeypatch.setattr(PipelineRunner, "run", failing_run)
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("x = 1\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["translate", str(repo), "-o", str(tmp_path / "out")])

    assert result.exit_code == 1
    assert "Permission denied" in result.output
    assert calls == [str(repo)]
