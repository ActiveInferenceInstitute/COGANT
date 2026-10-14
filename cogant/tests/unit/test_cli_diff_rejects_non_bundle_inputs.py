"""``cogant diff`` reports unusable inputs instead of crashing.

Two files that are not JSON objects, or a directory compared with a file,
must produce a clear message and exit code 2 (the code ``diff`` already uses
for a missing path) rather than a raw traceback.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cogant.cli.main import app


@pytest.mark.parametrize(
    "content",
    ["not json\n", json.dumps(["a", "b"]), json.dumps(42)],
)
def test_diff_of_non_bundle_files_exits_2(tmp_path: Path, content: str) -> None:
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps({"target": "a", "errors": []}), encoding="utf-8")
    b.write_text(content, encoding="utf-8")

    result = CliRunner().invoke(app, ["diff", str(a), str(b)])

    assert result.exit_code == 2, result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert "Not a bundle JSON object" in result.output
    assert "b.json" in result.output


def test_diff_of_directory_and_file_exits_2(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    bundle = tmp_path / "bundle.json"
    bundle.write_text(json.dumps({"target": "x"}), encoding="utf-8")

    result = CliRunner().invoke(app, ["diff", str(run_dir), str(bundle)])

    assert result.exit_code == 2, result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert "two run directories or two bundle JSON files" in result.output.replace("\n", " ")
