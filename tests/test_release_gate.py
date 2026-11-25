from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from run_gate import Step, make_step


def _module():
    path = Path(__file__).resolve().parents[1] / "tools" / "release_gate.py"
    spec = importlib.util.spec_from_file_location("release_gate_tests", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_root_steps_use_the_installable_package_environment() -> None:
    module = _module()
    step = make_step(
        "environment",
        ("uv", "run", "python", "-c", "import cogant; print(cogant.__file__)"),
        cwd=module.ROOT,
    )
    result = module._run_step("environment", step)
    assert result.status == "passed", result.output_tail
    assert str(module.INNER / "py" / "cogant" / "__init__.py") in result.output_tail
    assert step.cwd == module.ROOT


def test_nonzero_process_is_a_failed_gate() -> None:
    module = _module()
    step = Step(
        "negative-control",
        (sys.executable, "-c", "import sys; print('required failure'); sys.exit(3)"),
    )
    result = module._run_step("negative-control", step)
    assert result.status == "failed"
    assert result.returncode == 3
    assert result.output_tail == "required failure"


def test_skipped_package_suite_is_recorded() -> None:
    module = _module()
    results, passed = module.run_gate(include_tests=False, dry_run=True)
    assert results[0].name == "package-tests"
    assert results[0].status == "skipped"
    assert results[0].output_tail == "--skip-tests"
    assert passed is False


def test_skipping_required_suite_cannot_produce_a_passing_release(
    tmp_path, monkeypatch
) -> None:
    import json

    module = _module()
    marker = tmp_path / "executed"
    step = Step(
        "bounded-real-check",
        (
            sys.executable,
            "-c",
            f"from pathlib import Path; Path({str(marker)!r}).write_text('yes')",
        ),
        cwd=tmp_path,
    )
    monkeypatch.setattr(
        module, "build_release_steps", lambda **_: [("bounded-real-check", step)]
    )
    monkeypatch.setattr(module, "REPORT_PATH", tmp_path / "report.json")
    assert module.main(["--skip-tests"]) == 1
    assert marker.read_text() == "yes"
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["overall"] == "incomplete"
    assert report["results"][0]["status"] == "skipped"


def test_dry_run_reports_no_executed_success(tmp_path, monkeypatch) -> None:
    import json

    module = _module()
    marker = tmp_path / "must-not-run"
    step = Step(
        "bounded-real-check",
        (
            sys.executable,
            "-c",
            f"from pathlib import Path; Path({str(marker)!r}).touch()",
        ),
        cwd=tmp_path,
    )
    monkeypatch.setattr(
        module, "build_release_steps", lambda **_: [("bounded-real-check", step)]
    )
    monkeypatch.setattr(module, "REPORT_PATH", tmp_path / "report.json")
    assert module.main(["--dry-run"]) == 0
    assert not marker.exists()
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["overall"] == "dry_run"
    assert all(result["status"] == "skipped" for result in report["results"])
