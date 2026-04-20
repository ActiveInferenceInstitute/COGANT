"""End-to-end tests for the ``cogant`` CLI subcommands via subprocess.

Each test invokes the real ``cogant`` console script as a subprocess
(the Typer app registered in :mod:`cogant.cli.main`). We deliberately
exercise the wire-level contract — exit code, stdout parseability,
required keys — rather than the in-process Typer runner so regressions
in entry-point packaging cannot slip through.

The tests are tagged ``@pytest.mark.integration``. They avoid any
network access and use the shipped ``examples/control_positive/calculator``
fixture (with a tiny tmp fallback) as the target repository.

Two tests (``analyze`` and ``version`` subcommands) are marked
``xfail`` because they do not exist in the current CLI surface — the
prompt's ergonomics preview them but they are not yet wired up. They
will flip to green automatically once the subcommands land.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Absolute path to the cogant project root and calculator fixture.
_COGANT_ROOT = Path(__file__).resolve().parents[2]
_CALCULATOR_FIXTURE = (
    _COGANT_ROOT / "examples" / "control_positive" / "calculator"
)


def _cogant_command() -> list[str]:
    """Return the argv prefix that invokes the cogant CLI.

    Prefers ``python -m cogant.cli.main`` so the test runs against the
    same interpreter pytest is using and does not depend on the
    ``cogant`` console script being on ``PATH``. The module has a
    top-level ``if __name__ == "__main__": app()`` guard so this is
    equivalent to the installed entry point.
    """
    return [sys.executable, "-m", "cogant.cli.main"]


def _run_cli(
    *args: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: float = 120.0,
) -> subprocess.CompletedProcess:
    """Run ``cogant <args>`` and return the :class:`CompletedProcess`.

    We force a wide terminal and disable rich's color/markup so the
    stdout we assert against is stable across local/CI environments.
    """
    base_env = os.environ.copy()
    base_env.setdefault("NO_COLOR", "1")
    base_env.setdefault("TERM", "dumb")
    base_env.setdefault("COLUMNS", "200")
    if env:
        base_env.update(env)
    return subprocess.run(
        [*_cogant_command(), *args],
        cwd=str(cwd) if cwd else None,
        env=base_env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


@pytest.fixture()
def calculator_repo(tmp_path: Path) -> Path:
    """Return a usable calculator repo path; fallback to a tiny tmp repo."""
    if _CALCULATOR_FIXTURE.exists() and (_CALCULATOR_FIXTURE / "calculator.py").exists():
        return _CALCULATOR_FIXTURE
    repo = tmp_path / "mini_calculator"
    repo.mkdir(parents=True)
    (repo / "__init__.py").write_text('"""mini calculator."""\n', encoding="utf-8")
    (repo / "calculator.py").write_text(
        "class Calculator:\n"
        "    def __init__(self):\n"
        "        self.display = '0'\n"
        "    def input_digit(self, digit: int) -> str:\n"
        "        self.display = str(digit)\n"
        "        return self.display\n"
        "    def get_display(self) -> str:\n"
        "        return self.display\n",
        encoding="utf-8",
    )
    return repo


@pytest.mark.integration
def test_cli_doctor_exits_zero() -> None:
    """``cogant doctor`` runs without crashing.

    Exit code ``0`` means every required runtime check passed. On a
    minimal CI environment the code may be ``1`` if e.g. ``git`` is
    missing — the contract here is only that the command is reachable,
    completes, and prints diagnostic output. We therefore accept
    ``{0, 1}`` and assert only that stdout is non-empty.
    """
    result = _run_cli("doctor")
    assert result.returncode in (0, 1), (
        f"doctor exited {result.returncode}. stderr: {result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert combined.strip(), "doctor produced no output at all"


@pytest.mark.integration
def test_cli_help_exits_zero_and_lists_commands() -> None:
    """``cogant --help`` must print the subcommand list with exit 0.

    This is the closest stand-in for a dedicated ``cogant version``
    subcommand (which is xfail-gated below) — the help banner is the
    documented discovery surface for the CLI today.
    """
    result = _run_cli("--help")
    assert result.returncode == 0, (
        f"--help exited {result.returncode}. stderr: {result.stderr!r}"
    )
    # The banner should enumerate the core subcommands.
    stdout = result.stdout
    for cmd in ("doctor", "translate", "explain", "scan"):
        assert cmd in stdout, (
            f"Expected to see {cmd!r} in --help output; got: {stdout!r}"
        )


@pytest.mark.integration
def test_cli_scan_json_format(calculator_repo: Path) -> None:
    """``cogant scan <repo> --format json`` exits 0 and prints JSON.

    ``scan`` is the lightweight analysis entry point in the current
    CLI (the analogue of the future ``cogant analyze``). We assert
    that the rendered JSON payload decodes and reports at least one
    parseable Python module.
    """
    result = _run_cli("scan", str(calculator_repo), "--format", "json")
    assert result.returncode == 0, (
        f"scan exited {result.returncode}. stderr: {result.stderr!r}"
    )
    stdout = result.stdout.strip()
    assert stdout, "scan produced no stdout"

    # Rich prints JSON with its own pretty-printer; recover the outer
    # object by slicing from the first ``{`` to the last ``}``.
    start = stdout.find("{")
    end = stdout.rfind("}")
    assert start != -1 and end != -1 and end > start, (
        f"scan output does not contain a JSON object: {stdout!r}"
    )
    try:
        payload = json.loads(stdout[start : end + 1])
    except json.JSONDecodeError as exc:
        pytest.fail(
            f"scan --format json output did not decode as JSON: {exc}. "
            f"Raw slice: {stdout[start : end + 1]!r}"
        )
    assert isinstance(payload, dict), "scan JSON payload should be an object"


@pytest.mark.integration
def test_cli_explain_json_format(calculator_repo: Path) -> None:
    """``cogant explain <repo> <node> --format json`` returns a parseable object.

    Expected schema contract (see :mod:`cogant.cli.explain`):
      * ``node_name`` — the resolved node name
      * ``node_id`` — stable graph id
      * ``rules_fired`` — list of fired rule explanations
      * ``blanket_role`` — Markov blanket role string

    We probe with ``Calculator`` (the top-level class on the fixture),
    which exists on both the shipped and fallback repos.
    """
    result = _run_cli(
        "explain", str(calculator_repo), "Calculator", "--format", "json"
    )
    assert result.returncode == 0, (
        f"explain exited {result.returncode}. "
        f"stdout: {result.stdout!r} stderr: {result.stderr!r}"
    )

    stdout = result.stdout.strip()
    assert stdout, "explain produced no stdout"

    # ``explain`` uses ``print(format_json(result))`` so stdout is plain
    # JSON — no Rich wrapping — and should parse directly. If there is
    # any leading log noise we strip to the first ``{``.
    start = stdout.find("{")
    assert start != -1, f"explain output has no JSON object: {stdout!r}"
    try:
        payload = json.loads(stdout[start:])
    except json.JSONDecodeError as exc:
        pytest.fail(
            f"explain --format json output did not decode as JSON: {exc}. "
            f"Raw: {stdout[start:]!r}"
        )

    assert "node_name" in payload, (
        f"explain JSON missing required 'node_name' key. Keys: {list(payload)}"
    )
    assert payload["node_name"], "node_name should be non-empty"
    # Sanity-check a handful of other documented keys.
    for key in ("node_id", "rules_fired", "rules_considered", "blanket_role"):
        assert key in payload, f"explain JSON missing {key!r}; keys={list(payload)}"


# ---------------------------------------------------------------------------
# `cogant analyze` and `cogant version` — wired in cogant.cli.main.
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_cli_analyze_json_format(calculator_repo: Path) -> None:
    """``cogant analyze <repo> --format json`` prints a JSON summary."""
    result = _run_cli("analyze", str(calculator_repo), "--format", "json")
    assert result.returncode == 0, result.stderr
    stdout = result.stdout.strip()
    start = stdout.find("{")
    end = stdout.rfind("}")
    assert start != -1 and end > start
    payload = json.loads(stdout[start : end + 1])
    for key in ("target", "stages_run", "node_count", "edge_count", "mapping_count"):
        assert key in payload, f"analyze JSON missing {key!r}; keys={list(payload)}"
    assert isinstance(payload["stages_run"], list)


@pytest.mark.integration
def test_cli_version_prints_semver() -> None:
    """``cogant version`` prints the current cogant version (semver)."""
    import re

    from cogant import __version__

    result = _run_cli("version")
    assert result.returncode == 0, result.stderr
    assert __version__ in result.stdout
    assert re.search(r"\b\d+\.\d+\.\d+\b", result.stdout)
