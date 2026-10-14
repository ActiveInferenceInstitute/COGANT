"""``cogant validate`` reports unreadable bundle files instead of crashing.

A path that is not JSON, or JSON that is not a bundle object, must produce a
clear message and exit code 2 (the same code as a missing path), not a raw
``JSONDecodeError`` / ``AttributeError`` traceback.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cogant.cli.main import app


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("notes.txt", "not json at all\n"),
        ("list.json", json.dumps(["target", "errors"])),
        ("binary.json", b"\xff\xfe\x00garbage"),
    ],
)
def test_validate_non_bundle_file_exits_2_with_message(
    tmp_path: Path, name: str, content: str | bytes
) -> None:
    path = tmp_path / name
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")

    result = CliRunner().invoke(app, ["validate", str(path)])

    assert result.exit_code == 2, result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert "Not a bundle JSON object" in result.output


def test_validate_run_dir_with_corrupt_bundle_exits_2(tmp_path: Path) -> None:
    (tmp_path / "bundle.json").write_text("{truncated", encoding="utf-8")
    result = CliRunner().invoke(app, ["validate", str(tmp_path)])
    assert result.exit_code == 2, result.output
    assert "Not a bundle JSON object" in result.output


def test_validate_bundle_object_still_checked(tmp_path: Path) -> None:
    path = tmp_path / "bundle.json"
    path.write_text(
        json.dumps(
            {"target": "t", "artifacts": {"a": 1}, "stage_results": {"s": {}}, "errors": []}
        ),
        encoding="utf-8",
    )
    result = CliRunner().invoke(app, ["validate", str(path)])
    assert result.exit_code == 0, result.output
    assert "All checks passed" in result.output
