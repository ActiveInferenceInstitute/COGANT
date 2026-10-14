"""``translate`` / ``analyze`` report real stage outcomes and fail on failure.

The results table must render ``bundle.stage_outcomes`` (a skipped dynamic
stage or a validate stage that returned ``passed=False`` is not a success),
and a run with failed stages must exit non-zero after still writing the
bundle for post-mortem.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cogant.api.bundle import Bundle, StageOutcome
from cogant.cli.main import app


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    (path / "calc.py").write_text(
        "class Calc:\n"
        "    def __init__(self):\n"
        "        self.total = 0\n"
        "    def add(self, x):\n"
        "        self.total += x\n"
        "    def value(self):\n"
        "        return self.total\n",
        encoding="utf-8",
    )
    return path


def _row_status(output: str, stage: str) -> str:
    match = re.search(rf"│ {stage}\s+│ ([^│]+?)\s+│", output)
    assert match, f"no table row for {stage!r} in:\n{output}"
    return match.group(1)


@pytest.mark.parametrize("command", ["translate", "analyze"])
def test_failed_stages_are_reported_and_exit_non_zero(
    command: str, repo: Path, tmp_path: Path
) -> None:
    out = tmp_path / f"{command}_out"
    result = CliRunner().invoke(
        app,
        [command, str(repo), "-o", str(out), "--skip", "graph", "--no-dynamic"],
        terminal_width=200,
    )

    assert result.exit_code == 1, result.output
    assert _row_status(result.output, "graph") == "⊘ Skipped"
    assert _row_status(result.output, "dynamic") == "⊘ Skipped"
    assert _row_status(result.output, "translate") == "✗ Failed"
    # validate returns passed=False without a program graph.
    assert _row_status(result.output, "validate") == "✗ Failed"
    assert "complete" not in result.output.split("Errors:", 1)[-1].lower()
    # The bundle is still written so the failure can be inspected.
    saved = json.loads((out / "bundle.json").read_text(encoding="utf-8"))
    assert saved["stage_outcomes"]["validate"] == "failed"


def test_analyze_json_mode_exits_non_zero_on_failed_stages(repo: Path, tmp_path: Path) -> None:
    out = tmp_path / "json_out"
    result = CliRunner().invoke(
        app,
        [
            "analyze",
            str(repo),
            "-o",
            str(out),
            "--skip",
            "graph",
            "--no-dynamic",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 1, result.output
    payload = json.loads(result.output[result.output.index("{") :])
    assert payload["errors"]


def test_partial_and_unavailable_outcomes_are_not_success(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from cogant.cli.commands import translate_cmd

    def fake_run(runner: Any, target: str, config: Any, description_prefix: str) -> Bundle:
        bundle = Bundle(target=target)
        for stage in config.stages:
            bundle.stage_results[stage] = {}
            bundle.stage_outcomes[stage] = StageOutcome.SUCCESS
        bundle.stage_outcomes["static"] = StageOutcome.PARTIAL
        bundle.stage_outcomes["validate"] = StageOutcome.UNAVAILABLE
        return bundle

    monkeypatch.setattr(translate_cmd, "_run_pipeline_with_progress", fake_run)
    result = CliRunner().invoke(
        app, ["translate", str(repo), "-o", str(tmp_path / "o")], terminal_width=200
    )

    assert result.exit_code == 0, result.output
    assert _row_status(result.output, "ingest") == "✓ Success"
    assert _row_status(result.output, "static") == "◐ Partial"
    assert _row_status(result.output, "validate") == "⊘ Unavailable"
    assert "Translation complete" in result.output


def test_successful_translate_still_exits_zero(repo: Path, tmp_path: Path) -> None:
    out = tmp_path / "ok_out"
    result = CliRunner().invoke(
        app,
        ["translate", str(repo), "-o", str(out), "--no-dynamic", "--skip", "export"],
        terminal_width=200,
    )
    assert result.exit_code == 0, result.output
    assert _row_status(result.output, "translate") == "✓ Success"
    assert _row_status(result.output, "export") == "⊘ Skipped"
    assert "Translation complete" in result.output
