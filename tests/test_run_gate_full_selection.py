"""The actual full/fast selections execute distinct, real miniature test suites."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_gate import ARMS, Step, build_release_steps


def _workspace(root: Path, *, failing_slow: bool, ini_filter: bool) -> None:
    (root / "tests/property").mkdir(parents=True)
    (root / "cogant").mkdir()
    (root / "cogant/__init__.py").write_text(
        "def compute():\n    return 1\n", encoding="utf-8"
    )
    (root / "pytest.ini").write_text(
        "[pytest]\nmarkers = slow: bounded slow invariant\n"
        + ('addopts = -m "not slow"\n' if ini_filter else ""),
        encoding="utf-8",
    )
    (root / "tests/test_ordinary.py").write_text(
        "from pathlib import Path\nfrom cogant import compute\n"
        "def test_ordinary():\n"
        "    Path('ordinary-ran').write_text('yes')\n"
        "    assert compute() == 1\n",
        encoding="utf-8",
    )
    (root / "tests/test_slow.py").write_text(
        "from pathlib import Path\nimport pytest\n@pytest.mark.slow\n"
        "def test_slow():\n    Path('slow-ran').write_text('yes')\n"
        + (
            "    assert False, 'slow invariant executed'\n"
            if failing_slow
            else "    assert 1 == 1\n"
        ),
        encoding="utf-8",
    )
    (root / "tests/property/test_property.py").write_text(
        "from pathlib import Path\ndef test_property():\n"
        "    Path('property-ran').write_text('yes')\n    assert 2 + 2 == 4\n",
        encoding="utf-8",
    )


def _local_step(step: Step, root: Path, *, env_filter: bool) -> Step:
    # Substitute only the launcher, workspace and output destination. The
    # production pytest selection/coverage options reach the real subprocess.
    tail = [
        f"--cov-report=json:{root / 'coverage.json'}"
        if arg.startswith("--cov-report=json:")
        else arg
        for arg in step.argv[3:]
    ]
    environment = {
        "PYTHONPATH": str(root),
        "PYTEST_ADDOPTS": '-m "not slow"' if env_filter else "",
    }
    return replace(
        step, argv=(sys.executable, "-m", "pytest", *tail), cwd=root, env=environment
    )


def _execute(step: Step):
    environment = os.environ.copy()
    environment.update(step.env)
    return subprocess.run(
        step.argv,
        cwd=step.cwd,
        env=environment,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(
    "ini_filter,env_filter",
    [(False, False), (True, False), (False, True), (True, True)],
)
def test_full_runs_failing_slow_and_property_tests(tmp_path, ini_filter, env_filter):
    _workspace(tmp_path, failing_slow=True, ini_filter=ini_filter)
    result = _execute(
        _local_step(ARMS["test-full"].steps[0], tmp_path, env_filter=env_filter)
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "slow invariant executed" in result.stdout
    assert (tmp_path / "ordinary-ran").read_text() == "yes"
    assert (tmp_path / "slow-ran").read_text() == "yes"
    assert (tmp_path / "property-ran").read_text() == "yes"


def test_full_passing_suite_meets_coverage_gate(tmp_path):
    _workspace(tmp_path, failing_slow=False, ini_filter=True)
    result = _execute(
        _local_step(ARMS["test-full"].steps[0], tmp_path, env_filter=True)
    )
    assert result.returncode == 0, result.stdout + result.stderr
    coverage = json.loads((tmp_path / "coverage.json").read_text())
    assert coverage["totals"]["percent_covered"] == 100
    assert (tmp_path / "slow-ran").is_file()
    assert (tmp_path / "property-ran").is_file()


def test_fast_intentionally_deselects_slow_and_property(tmp_path):
    _workspace(tmp_path, failing_slow=True, ini_filter=False)
    result = _execute(
        _local_step(ARMS["test-fast"].steps[0], tmp_path, env_filter=False)
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "ordinary-ran").is_file()
    assert not (tmp_path / "slow-ran").exists()
    assert not (tmp_path / "property-ran").exists()


def test_release_executes_full_failure_stops_and_records_failed_report(
    tmp_path, monkeypatch
):
    _workspace(tmp_path, failing_slow=True, ini_filter=True)
    spec = importlib.util.spec_from_file_location(
        "release_selection_tests", ROOT / "tools/release_gate.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    package = dict(build_release_steps())["package-tests"]
    failing = _local_step(package, tmp_path, env_filter=True)
    later = Step(
        "later",
        (
            sys.executable,
            "-c",
            "from pathlib import Path; Path('later-ran').write_text('yes')",
        ),
        cwd=tmp_path,
    )
    # The command under test comes from the release projection. Limit only
    # the surrounding plan to bounded commands; do not fake process results.
    monkeypatch.setattr(
        module,
        "build_release_steps",
        lambda **_: [("package-tests", failing), ("later", later)],
    )
    monkeypatch.setattr(module, "REPORT_PATH", tmp_path / "report.json")
    results, passed = module.run_gate()
    module._write_report(results, passed)
    assert passed is False
    assert results[0].name == "package-tests"
    assert results[0].status == "failed"
    assert results[0].returncode == 1
    assert "slow invariant executed" in results[0].output_tail
    assert not (tmp_path / "later-ran").exists()
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["overall"] == "failed"
    assert report["results"][0]["status"] == "failed"
