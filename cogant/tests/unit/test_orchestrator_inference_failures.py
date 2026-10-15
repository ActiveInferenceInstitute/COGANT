from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests.gnn_execution_fixture import MODEL, package

PACKAGE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PACKAGE / "examples"))

from orchestrate_roundtrip import RoundtripOrchestrator

pytestmark = pytest.mark.unit


def test_required_package_build_failure_propagates_to_run(tmp_path: Path) -> None:
    output = tmp_path / "run"
    output.mkdir()
    (output / "gnn_package").write_text("existing file blocks package creation")
    orchestrator = RoundtripOrchestrator(PACKAGE / "examples/control_positive/calculator", output)

    assert orchestrator.run() is False
    assert not (output / "inference_trace.json").exists()
    assert not (output / "gnn_execution_trace.json").exists()
    assert not (output / "gnn_execution_report.md").exists()


@pytest.mark.parametrize("malformed", [False, True])
def test_unusable_gnn_rejects_required_inference_and_execution(
    tmp_path: Path, malformed: bool
) -> None:
    if malformed:
        package(tmp_path / "gnn_package", MODEL.replace("0.9 0.2", "0.9 0.9"))
    orchestrator = RoundtripOrchestrator(PACKAGE / "examples/control_positive/calculator", tmp_path)

    assert orchestrator._add_inference_trace() is False
    assert orchestrator._run_gnn_model() is False
    assert orchestrator._validate_gnn_package() is False
    assert not (tmp_path / "inference_trace.json").exists()
    assert not (tmp_path / "gnn_execution_trace.json").exists()
    assert not (tmp_path / "gnn_execution_report.md").exists()


def test_formatting_exception_cannot_report_success(tmp_path: Path) -> None:
    orchestrator = RoundtripOrchestrator(PACKAGE / "examples/control_positive/calculator", tmp_path)

    assert orchestrator._format_and_validate(None, None, {}) is False
    assert not (tmp_path / "inference_trace.json").exists()
