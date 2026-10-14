"""``export-gnn`` and ``render`` report unusable bundle paths cleanly.

A missing path, a file that is not JSON, JSON that is not an object, or (for
``render``) a bundle without ``target`` must print a clear error and exit 2
like ``validate`` and ``diff``, instead of a raw traceback.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cogant.cli.main import app


def _assert_clean_exit_2(
    result_output: str, exit_code: int, exception: BaseException | None
) -> None:
    assert exit_code == 2, result_output
    assert exception is None or isinstance(exception, SystemExit), repr(exception)


@pytest.mark.parametrize("command", ["export-gnn", "render"])
def test_missing_bundle_path_exits_2(command: str, tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    result = CliRunner().invoke(app, [command, str(missing), "-o", str(tmp_path / "out")])
    _assert_clean_exit_2(result.output, result.exit_code, result.exception)
    assert "Not found" in result.output


@pytest.mark.parametrize("command", ["export-gnn", "render"])
@pytest.mark.parametrize("content", ["not json\n", json.dumps([1, 2, 3])])
def test_non_bundle_json_exits_2(command: str, content: str, tmp_path: Path) -> None:
    path = tmp_path / "bundle.json"
    path.write_text(content, encoding="utf-8")
    result = CliRunner().invoke(app, [command, str(path), "-o", str(tmp_path / "out")])
    _assert_clean_exit_2(result.output, result.exit_code, result.exception)
    assert "Not a bundle JSON object" in result.output


def test_render_bundle_without_target_exits_2(tmp_path: Path) -> None:
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps({"stage_results": {}}), encoding="utf-8")
    result = CliRunner().invoke(app, ["render", str(path), "-o", str(tmp_path / "out")])
    _assert_clean_exit_2(result.output, result.exit_code, result.exception)
    assert "target" in result.output


def test_export_gnn_still_writes_valid_bundle(tmp_path: Path) -> None:
    path = tmp_path / "in.json"
    path.write_text(
        json.dumps({"target": "t", "stage_results": {}, "errors": [], "artifacts": {}}),
        encoding="utf-8",
    )
    out = tmp_path / "out"
    result = CliRunner().invoke(app, ["export-gnn", str(path), "-o", str(out), "-f", "json"])
    assert result.exit_code == 0, result.output
    assert json.loads((out / "bundle.json").read_text(encoding="utf-8"))["target"] == "t"
