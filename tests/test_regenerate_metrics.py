from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _module():
    path = Path(__file__).resolve().parents[1] / "tools" / "regenerate_metrics.py"
    spec = importlib.util.spec_from_file_location("metrics_probe_tests", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "probe",
    [
        "get_test_count_total",
        "get_test_results_and_coverage",
        "get_mypy_errors",
        "get_ruff_violations",
    ],
)
def test_missing_tool_aborts_probe(
    probe: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _module()
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(module.MetricsProbeError, match="Probe exited 127"):
        getattr(module, probe)()


def test_nonzero_command_keeps_stderr() -> None:
    module = _module()
    with pytest.raises(module.MetricsProbeError, match="measurement failed"):
        module._run(
            f"'{sys.executable}' -c \"import sys; sys.stderr.write('measurement failed'); sys.exit(3)\""
        )


def test_timeout_aborts_probe() -> None:
    module = _module()
    with pytest.raises(module.MetricsProbeError, match="timed out"):
        module._run(f"exec '{sys.executable}' -c 'import time; time.sleep(10)'", timeout=0.05)


@pytest.mark.parametrize(
    "probe",
    [
        "get_test_count_total",
        "get_test_results_and_coverage",
        "get_mypy_errors",
        "get_ruff_violations",
    ],
)
def test_success_without_a_measurement_is_rejected(
    probe: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _module()
    executable = tmp_path / "uv"
    executable.write_text("#!/bin/sh\nprintf 'not a measurement\\n'\n")
    executable.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(module.MetricsProbeError, match="Could not parse"):
        getattr(module, probe)()


def test_failed_regeneration_preserves_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    path = module.EVAL_DIR / "METRICS.yaml"
    before = path.read_bytes()
    monkeypatch.setenv("PATH", "")
    with pytest.raises(module.MetricsProbeError):
        module.main()
    assert path.read_bytes() == before


def test_receipt_count_must_match_the_same_run_summary(tmp_path: Path) -> None:
    module = _module()
    receipt = tmp_path / "tests.xml"
    receipt.write_text(
        '<testsuites><testsuite><testcase name="a"/><testcase name="b"><skipped/></testcase></testsuite></testsuites>'
    )
    assert module._test_total_from_report(receipt, {"passing": 1, "skipped": 1}) == 2
    with pytest.raises(module.MetricsProbeError, match="disagrees"):
        module._test_total_from_report(receipt, {"passing": 1})


@pytest.mark.parametrize("contents", ["broken XML", "<testsuites/>"])
def test_invalid_receipt_is_rejected(tmp_path: Path, contents: str) -> None:
    module = _module()
    receipt = tmp_path / "tests.xml"
    receipt.write_text(contents)
    with pytest.raises(module.MetricsProbeError):
        module._test_total_from_report(receipt, {"passing": 1})
