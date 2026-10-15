from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from cogant.runtime.inference_records import InferenceTrace
from tests.gnn_execution_fixture import MODEL


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "cogant.cli.main", *args],
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_real_repository_export_and_inference_preserve_every_matrix(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[2] / "examples/control_positive/calculator"
    run = tmp_path / "run"
    translated = _cli("translate", str(source), "-o", str(run), "--no-dynamic", "--layout-output")
    assert translated.returncode == 0, translated.stderr
    gnn = run / "gnn_package/model.gnn.md"
    trace_path = run / "data/inference_trace.json"
    inferred = _cli("infer", str(gnn), "--steps", "3", "-o", str(trace_path))
    assert inferred.returncode == 0, inferred.stderr
    trace = InferenceTrace.model_validate_json(trace_path.read_bytes())
    exported = json.loads((run / "gnn_package/model.gnn.json").read_text())["matrices"]
    snapshot = trace.matrices.model_dump(mode="json")
    for key in ("A", "B", "C", "D"):
        assert snapshot[key] == exported[key], key
    assert trace.source_sha256 == hashlib.sha256(gnn.read_bytes()).hexdigest()
    assert trace.mode == "model_rollout"
    for record in trace.trace:
        assert record.policy_scores[record.action] == min(record.policy_scores)


def test_supplied_observations_stdout_and_exclusive_output(tmp_path: Path) -> None:
    source = tmp_path / "model.gnn.md"
    source.write_bytes(MODEL.replace("\n", "\r\n").encode())
    observations = tmp_path / "observations.json"
    observations.write_text("[0, 1]")
    result = _cli("infer", str(source), "--observations", str(observations))
    assert result.returncode == 0, result.stderr
    trace = InferenceTrace.model_validate_json(result.stdout)
    assert trace.source_sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert trace.mode == "observations" and len(trace.trace) == 2
    assert trace.trace[0].posterior == pytest.approx((0.675 / 0.725, 0.05 / 0.725))
    output = tmp_path / "trace.json"
    output.write_text("preserve this evidence")
    denied = _cli("infer", str(source), "-o", str(output))
    assert denied.returncode == 2
    assert output.read_text() == "preserve this evidence"
    replaced = _cli("infer", str(source), "-o", str(output), "--overwrite")
    assert replaced.returncode == 0, replaced.stderr
    assert len(InferenceTrace.model_validate_json(output.read_bytes()).trace) == 8


@pytest.mark.parametrize("observations", ["[true]", '["0"]', "[-1]", "[2]", "[]", "{"])
def test_invalid_observations_never_write_success(tmp_path: Path, observations: str) -> None:
    source = tmp_path / "model.gnn.md"
    source.write_text(MODEL)
    observed = tmp_path / "observations.json"
    observed.write_text(observations)
    output = tmp_path / "trace.json"
    result = _cli("infer", str(source), "--observations", str(observed), "-o", str(output))
    assert result.returncode == 2, result.stderr
    assert not output.exists()


def test_missing_and_incomplete_inputs_fail_without_success(tmp_path: Path) -> None:
    source = tmp_path / "missing.gnn.md"
    assert _cli("infer", str(source)).returncode == 2
    source.write_text("## ModelName\nIncomplete\n")
    result = _cli("infer", str(source))
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
