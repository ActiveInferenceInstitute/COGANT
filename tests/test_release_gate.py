from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


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
    step = module._step(
        "environment", ("uv", "run", "python", "-c", "import cogant; print(cogant.__file__)")
    )
    result = module._run_step(step)
    assert result.status == "passed", result.output_tail
    assert str(module.INNER / "py" / "cogant" / "__init__.py") in result.output_tail
    assert step.cwd == module.ROOT


def test_nonzero_process_is_a_failed_gate() -> None:
    module = _module()
    step = module._step(
        "negative-control",
        (sys.executable, "-c", "import sys; print('required failure'); sys.exit(3)"),
    )
    result = module._run_step(step)
    assert result.status == "failed"
    assert result.returncode == 3
    assert result.output_tail == "required failure"


def test_gate_references_existing_pytest_files() -> None:
    module = _module()
    referenced = [
        step.cwd / argument
        for step in module.build_steps()
        for argument in step.command
        if argument.startswith("tests/") and argument.endswith(".py")
    ]
    assert referenced
    assert all(path.is_file() for path in referenced), referenced


def test_skipped_package_suite_is_recorded() -> None:
    module = _module()
    results, _ = module.run_gate(include_tests=False, dry_run=True)
    assert results[0].name == "package-tests"
    assert results[0].status == "skipped"
    assert results[0].output_tail == "--skip-tests"
