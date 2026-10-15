from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_all_runner import DEFAULT_CONFIG, _write_cross_target_summary


def config(path: Path, output: Path, *, layout: bool = True) -> Path:
    steps = {
        key: False
        for key, value in DEFAULT_CONFIG["steps"].items()
        if isinstance(value, bool)
    }
    steps.update(translate=True, inference=True, layout_output=layout, no_dynamic=True)
    value = {
        "package_root": str(ROOT / "cogant"),
        "output_root": str(output),
        "targets": [
            {"id": "calculator", "path": "examples/control_positive/calculator"}
        ],
        "steps": steps,
    }
    path.write_text(json.dumps(value))
    return path


def run(path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "run_all.py"), "--config", str(path), *extra],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize("fail_fast", [False, True])
def test_failed_translation_never_infers_from_previous_artifacts(
    tmp_path: Path, fail_fast: bool
) -> None:
    settings = config(tmp_path / "config.json", tmp_path / "output")
    first = run(settings)
    assert first.returncode == 0, first.stdout + first.stderr
    target = tmp_path / "output" / "calculator"
    trace = target / "data" / "inference_trace.json"
    before = hashlib.sha256(trace.read_bytes()).hexdigest()
    (target / "bundle.json").mkdir()

    failed = run(settings, *(["--fail-fast"] if fail_fast else []))

    assert failed.returncode != 0
    manifest = json.loads((tmp_path / "output" / "run_manifest.json").read_text())
    result = manifest["targets"][0]
    assert any(
        command["step"] == "translate:calculator" and command["exit"] != 0
        for command in result["commands"]
    )
    assert not any(
        command["step"] == "inference:calculator" for command in result["commands"]
    )
    assert result["status"] == "failed"
    assert result["source_admitted"] is False
    assert result["artifact_presence"]["inference_trace"] is False
    assert hashlib.sha256(trace.read_bytes()).hexdigest() == before
    summary = json.loads((tmp_path / "output" / "summary.json").read_text())
    assert summary["rows"][0]["status"] == "failed"
    assert summary["rows"][0]["validator_result"] is None


def test_success_records_verified_inference_identity(tmp_path: Path) -> None:
    settings = config(tmp_path / "config.json", tmp_path / "output")
    completed = run(settings)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    manifest = json.loads((tmp_path / "output" / "run_manifest.json").read_text())
    target = manifest["targets"][0]
    source = tmp_path / "output" / "calculator" / "gnn_package" / "model.gnn.md"
    trace = json.loads(
        (source.parent.parent / "data" / "inference_trace.json").read_text()
    )
    assert (
        target["inference"]["source_sha256"]
        == hashlib.sha256(source.read_bytes()).hexdigest()
    )
    assert target["inference"]["matrices_sha256"] == trace["matrices_sha256"]
    assert target["inference"]["steps"] == 8
    assert target["artifact_presence"]["inference_trace"] is True
    summary = json.loads((tmp_path / "output" / "summary.json").read_text())
    assert summary["rows"][0]["inference"] == target["inference"]


def test_summary_rejects_trace_bound_to_previous_source(tmp_path: Path) -> None:
    settings = config(tmp_path / "config.json", tmp_path / "output")
    completed = run(settings)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    output = tmp_path / "output"
    manifest = json.loads((output / "run_manifest.json").read_text())
    source = output / "calculator" / "gnn_package" / "model.gnn.md"
    source.write_text(source.read_text() + "\n")

    failures = _write_cross_target_summary(
        output, manifest, package_root=ROOT / "cogant", log_fp=sys.stdout
    )

    assert "summary_inference:calculator" in failures
    summary = json.loads((output / "summary.json").read_text())
    assert summary["rows"][0]["status"] == "failed"
    assert summary["rows"][0]["artifact_presence"]["inference_trace"] is False
    assert "stale" in summary["rows"][0]["inference_error"]


def test_flat_batch_keeps_inference_beside_flat_bundle(tmp_path: Path) -> None:
    settings = config(tmp_path / "config.json", tmp_path / "output", layout=False)
    completed = run(settings)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    target = tmp_path / "output" / "calculator"
    assert (target / "bundle.json").is_file()
    assert (target / "inference_trace.json").is_file()
    assert not (target / "data").exists()
    manifest = json.loads((target.parent / "run_manifest.json").read_text())
    assert manifest["targets"][0]["artifact_presence"]["inference_trace"] is True
    assert manifest["targets"][0]["inference"]["steps"] == 8
