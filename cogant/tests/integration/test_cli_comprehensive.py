"""Comprehensive CLI subcommand validation via subprocess.

Tests every registered subcommand in ``cogant.cli.main`` with at least a
``--help`` invocation (which must always exit 0 and produce output), plus
functional tests for commands that can run without complex setup.

Uses ``python -m cogant.cli.main`` so no installed entry point is needed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
CALCULATOR_FIXTURE = REPO_ROOT / "examples" / "control_positive" / "calculator"

_ENV = {
    **os.environ,
    "NO_COLOR": "1",
    "TERM": "dumb",
    "COLUMNS": "200",
    "PYTHONPATH": str(REPO_ROOT / "py"),
}


def _run(*args: str, timeout: float = 60.0) -> subprocess.CompletedProcess:
    """Run ``python -m cogant.cli.main <args>``."""
    return subprocess.run(
        [sys.executable, "-m", "cogant.cli.main", *args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=_ENV,
        timeout=timeout,
        check=False,
    )


# ===================================================================
# Root help
# ===================================================================


@pytest.mark.integration
def test_root_help():
    """``cogant --help`` exits 0 and lists subcommands."""
    result = _run("--help")
    assert result.returncode == 0
    assert len(result.stdout) > 10
    # Should mention at least a few core commands
    for cmd in ("doctor", "scan", "translate"):
        assert cmd in result.stdout.lower(), f"{cmd} not in root --help"


# ===================================================================
# --help tests for every subcommand
# ===================================================================


@pytest.mark.integration
def test_doctor_help():
    result = _run("doctor", "--help")
    assert result.returncode == 0
    assert len(result.stdout) > 10


@pytest.mark.integration
def test_scan_help():
    result = _run("scan", "--help")
    assert result.returncode == 0
    assert "scan" in result.stdout.lower() or len(result.stdout) > 10


@pytest.mark.integration
def test_init_help():
    result = _run("init", "--help")
    assert result.returncode == 0
    assert "init" in result.stdout.lower() or len(result.stdout) > 10


@pytest.mark.integration
def test_translate_help():
    result = _run("translate", "--help")
    assert result.returncode == 0
    assert len(result.stdout) > 10


@pytest.mark.integration
def test_explain_help():
    result = _run("explain", "--help")
    assert result.returncode == 0
    assert len(result.stdout) > 10


@pytest.mark.integration
def test_reverse_help():
    result = _run("reverse", "--help")
    assert result.returncode == 0
    assert len(result.stdout) > 10


@pytest.mark.integration
def test_roundtrip_help():
    result = _run("roundtrip", "--help")
    assert result.returncode == 0
    assert len(result.stdout) > 10


@pytest.mark.integration
def test_validate_help():
    result = _run("validate", "--help")
    assert result.returncode == 0
    assert len(result.stdout) > 10


@pytest.mark.integration
def test_export_gnn_help():
    result = _run("export-gnn", "--help")
    assert result.returncode == 0
    assert len(result.stdout) > 10


@pytest.mark.integration
def test_render_help():
    result = _run("render", "--help")
    assert result.returncode == 0
    assert len(result.stdout) > 10


@pytest.mark.integration
def test_viz_help():
    result = _run("viz", "--help")
    assert result.returncode == 0
    assert len(result.stdout) > 10


@pytest.mark.integration
def test_graph_help():
    result = _run("graph", "--help")
    assert result.returncode == 0
    assert len(result.stdout) > 10


@pytest.mark.integration
def test_statespace_help():
    result = _run("statespace", "--help")
    assert result.returncode == 0
    assert len(result.stdout) > 10


@pytest.mark.integration
def test_process_help():
    result = _run("process", "--help")
    assert result.returncode == 0
    assert len(result.stdout) > 10


@pytest.mark.integration
def test_extract_static_help():
    result = _run("extract-static", "--help")
    assert result.returncode == 0
    assert len(result.stdout) > 10


@pytest.mark.integration
def test_extract_dynamic_help():
    result = _run("extract-dynamic", "--help")
    assert result.returncode == 0
    assert len(result.stdout) > 10


@pytest.mark.integration
def test_diff_help():
    result = _run("diff", "--help")
    assert result.returncode == 0
    assert len(result.stdout) > 10


@pytest.mark.integration
def test_changed_help():
    result = _run("changed", "--help")
    assert result.returncode == 0
    assert len(result.stdout) > 10


@pytest.mark.integration
def test_benchmark_help():
    result = _run("benchmark", "--help")
    assert result.returncode == 0
    assert len(result.stdout) > 10


@pytest.mark.integration
def test_plugin_list_help():
    result = _run("plugin", "list", "--help")
    assert result.returncode == 0
    assert len(result.stdout) > 10


@pytest.mark.integration
def test_plugin_info_help():
    result = _run("plugin", "info", "--help")
    assert result.returncode == 0
    assert len(result.stdout) > 10


@pytest.mark.integration
def test_migrate_help():
    result = _run("migrate", "--help")
    assert result.returncode == 0
    assert len(result.stdout) > 10


# ===================================================================
# Functional tests (commands that can actually run)
# ===================================================================


@pytest.mark.integration
def test_doctor_functional():
    """``cogant doctor`` should exit 0 or 1 and print diagnostics."""
    result = _run("doctor")
    assert result.returncode in (0, 1), (
        f"doctor exited {result.returncode}; stderr: {result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert len(combined.strip()) > 0, "doctor produced no output"


@pytest.mark.integration
def test_plugin_list_functional():
    """``cogant plugin list`` returns exit 0 (even if empty list)."""
    result = _run("plugin", "list")
    assert result.returncode == 0, (
        f"plugin list exited {result.returncode}; stderr: {result.stderr!r}"
    )


@pytest.mark.integration
def test_scan_calculator_fixture():
    """``cogant scan`` on the calculator fixture exits 0 with output."""
    if not CALCULATOR_FIXTURE.exists():
        pytest.skip("calculator fixture not found")
    result = _run("scan", str(CALCULATOR_FIXTURE), "--format", "json")
    assert result.returncode == 0, f"scan exited {result.returncode}; stderr: {result.stderr!r}"
    stdout = result.stdout.strip()
    assert stdout, "scan produced no stdout"
    # Extract JSON from potential Rich wrapping
    start = stdout.find("{")
    end = stdout.rfind("}")
    if start != -1 and end > start:
        payload = json.loads(stdout[start : end + 1])
        assert isinstance(payload, dict)


@pytest.mark.integration
def test_explain_calculator_fixture():
    """``cogant explain`` on Calculator class exits 0 with JSON."""
    if not CALCULATOR_FIXTURE.exists():
        pytest.skip("calculator fixture not found")
    result = _run("explain", str(CALCULATOR_FIXTURE), "Calculator", "--format", "json")
    assert result.returncode == 0, f"explain exited {result.returncode}; stderr: {result.stderr!r}"
    stdout = result.stdout.strip()
    start = stdout.find("{")
    if start != -1:
        payload = json.loads(stdout[start:])
        assert "node_name" in payload


@pytest.mark.integration
def test_init_creates_config(tmp_path: Path):
    """``cogant init`` scaffolds a .cogant/config.json."""
    target = tmp_path / "test_project"
    result = _run("init", str(target), "--quiet")
    assert result.returncode == 0, f"init exited {result.returncode}; stderr: {result.stderr!r}"
    config = target / ".cogant" / "config.json"
    assert config.exists(), "init did not create .cogant/config.json"
    data = json.loads(config.read_text())
    assert "version" in data
    assert "stages" in data


@pytest.mark.integration
def test_init_idempotent(tmp_path: Path):
    """Running ``cogant init`` twice does not clobber config."""
    target = tmp_path / "idem_project"
    result1 = _run("init", str(target), "--quiet")
    assert result1.returncode == 0
    config = target / ".cogant" / "config.json"
    original = config.read_text()

    result2 = _run("init", str(target), "--quiet")
    assert result2.returncode == 0
    assert config.read_text() == original, "init clobbered existing config"


@pytest.mark.integration
def test_validate_on_nonexistent_path():
    """``cogant validate`` on a missing path should exit non-zero."""
    result = _run("validate", "/tmp/cogant_does_not_exist_12345")
    assert result.returncode != 0
