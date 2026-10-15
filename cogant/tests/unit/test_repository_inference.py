from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from cogant.reverse.idempotency import RoundtripResult
from cogant.runtime.inference import load_inference_trace

PACKAGE = Path(__file__).resolve().parents[2]
SCRIPT = PACKAGE / "scripts" / "repository_inference.py"


@pytest.mark.parametrize(
    "status,preserved,errors,expected",
    [
        ("unknown", False, [], False),
        ("DRIFT", False, [], False),
        ("STRUCTURALLY_ISOMORPHIC", True, [], True),
        ("DRIFT", True, [], False),
        ("STRUCTURALLY_ISOMORPHIC", True, ["missing comparison"], False),
    ],
)
def test_structure_verdict_requires_explicit_error_free_result(
    status: str, preserved: bool, errors: list[str], expected: bool
) -> None:
    spec = importlib.util.spec_from_file_location("repository_inference", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = RoundtripResult(
        roundtrip_status=status, structurally_isomorphic=preserved, errors=errors
    )
    verdict = module.roundtrip_structure_verdict(result)
    assert verdict.startswith("Structure preserved:") is expected
    assert result.roundtrip_status in verdict


def test_real_repository_export_inference_and_roundtrip(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "counter.py").write_text(
        "class Counter:\n"
        "    def __init__(self):\n        self.value = 0\n"
        "    def increment(self):\n        self.value += 1\n"
        "    def observe(self):\n        return self.value\n"
    )
    output = tmp_path / "result"

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(source), "--output", str(output), "--steps", "3"],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
        cwd=PACKAGE,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    trace = load_inference_trace(output / "forward")
    gnn = output / "forward" / "gnn_package" / "model.gnn.md"
    assert trace.source_sha256 == hashlib.sha256(gnn.read_bytes()).hexdigest()
    assert trace.matrices_sha256 == trace.matrices.digest()
    assert len(trace.trace) == 3
    assert trace.mode == "model_rollout"
    roundtrip = json.loads((output / "roundtrip.json").read_text())
    assert roundtrip["roundtrip_status"] != "FAILED"
    assert (output / "roundtrip").is_dir()
    assert (output / "translate.log").stat().st_size > 0
    report = (output / "report.md").read_text()
    assert "do not establish empirical adequacy" in report
    assert trace.source_sha256 in report
    if not roundtrip["structurally_isomorphic"]:
        assert "Structure preservation not established" in report


def test_missing_repository_fails_without_success_artifacts(tmp_path: Path) -> None:
    output = tmp_path / "result"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path / "missing"), "--output", str(output)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        cwd=PACKAGE,
    )
    assert result.returncode != 0
    assert not output.exists()
    assert "does not exist" in result.stderr


def test_existing_output_is_preserved(tmp_path: Path) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    marker = output / "preserved.txt"
    marker.write_text("existing evidence")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(output)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        cwd=PACKAGE,
    )
    assert result.returncode != 0
    assert marker.read_text() == "existing evidence"
    assert not (output / "report.md").exists()
