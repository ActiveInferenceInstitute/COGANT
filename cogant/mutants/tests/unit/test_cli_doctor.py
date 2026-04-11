"""Smoke tests for the ergonomic CLI surface: ``doctor`` and ``init``.

These tests intentionally avoid mocking: they run the real Typer app
in a :class:`typer.testing.CliRunner` against real filesystem paths.
The doctor command inspects the *actual* interpreter, so we assert
only on stable substrings (``Python``) and exit codes.

The tests also verify that the enhanced ``init`` command still
creates the legacy ``.cogant/config.json`` layout (backward
compatibility with ``test_cli.py::TestInitCommand``).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cogant.cli.doctor import (
    DoctorCheck,
    DoctorReport,
    _check_external_tool,
    _check_mermaid_cli,
    _check_mypy,
    _check_ruff,
    _check_tree_sitter_node_types,
    doctor_command,
    run_doctor,
)
from cogant.cli.main import app


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------- doctor --


class TestDoctorCommand:
    def test_doctor_runs_without_error(self, runner: CliRunner) -> None:
        """``cogant doctor`` exits with a zero status on a healthy dev env."""
        result = runner.invoke(app, ["doctor"])
        # The test environment runs with cogant installed, so all required
        # checks should pass; optional warnings may still be present.
        assert result.exit_code == 0, result.stdout
        assert "COGANT Environment Diagnostics" in result.stdout

    def test_doctor_output_contains_python_version(self, runner: CliRunner) -> None:
        """Output must surface the word 'Python' so users can spot it."""
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "Python" in result.stdout

    def test_doctor_output_contains_overall_verdict(
        self, runner: CliRunner
    ) -> None:
        """The panel's subtitle always includes an Overall verdict."""
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "Overall" in result.stdout

    def test_doctor_help_lists_description(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["doctor", "--help"])
        assert result.exit_code == 0
        assert "Diagnose" in result.stdout or "diagnostic" in result.stdout.lower()

    def test_run_doctor_returns_structured_report(self) -> None:
        """The programmatic API returns a :class:`DoctorReport` with checks."""
        report = run_doctor()
        assert isinstance(report, DoctorReport)
        assert len(report.checks) >= 4  # python + core deps + rust + git
        # All checks are DoctorCheck dataclasses with valid statuses.
        for check in report.checks:
            assert isinstance(check, DoctorCheck)
            assert check.status in {"ok", "warn", "fail"}
            assert check.name  # non-empty name

        # Python check should always be present and passing (tests need 3.11+).
        python_checks = [c for c in report.checks if c.name == "Python"]
        assert len(python_checks) == 1
        assert python_checks[0].status == "ok"

    def test_doctor_command_returns_exit_code(self) -> None:
        """``doctor_command`` returns 0 on success for in-process callers."""
        code = doctor_command()
        assert code == 0


# ------------------------------------------------------------------ init --


class TestInitCommand:
    """Tests for the enhanced ``init`` command.

    The legacy ``test_cli.py::TestInitCommand::test_init_creates_project_layout``
    already covers the default-path scaffold behaviour; these tests
    extend coverage to the new flags (``--check``, ``--run``,
    ``--yes``) and the friendly error surface.
    """

    def test_init_reports_file_count(self, runner: CliRunner, tmp_path: Path) -> None:
        """Init surfaces the source file count it discovered."""
        # Create a tiny repo with one python file.
        repo = tmp_path / "mini_repo"
        repo.mkdir()
        (repo / "main.py").write_text("print('hello')\n")

        result = runner.invoke(app, ["init", str(repo)])
        assert result.exit_code == 0, result.stdout
        assert "Initializing COGANT project" in result.stdout
        # File count is reported as a cyan number in the Rich panel.
        assert "Source files detected" in result.stdout
        # The scaffolded config is still created for backward compat.
        assert (repo / ".cogant" / "config.json").exists()
        cfg = json.loads((repo / ".cogant" / "config.json").read_text())
        assert "translate" in cfg["stages"]

    def test_init_warns_when_no_source_files(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Empty repos trigger a friendly warning rather than an error."""
        empty = tmp_path / "empty_repo"
        empty.mkdir()
        (empty / "README.md").write_text("no code here\n")

        result = runner.invoke(app, ["init", str(empty)])
        assert result.exit_code == 0
        assert "No .py/.js/.ts files found" in result.stdout

    def test_init_with_check_runs_doctor(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """``--check`` runs doctor before scaffolding."""
        repo = tmp_path / "checked_repo"
        repo.mkdir()
        (repo / "main.py").write_text("x = 1\n")

        result = runner.invoke(app, ["init", str(repo), "--check"])
        assert result.exit_code == 0, result.stdout
        assert "Environment diagnostics" in result.stdout
        assert "COGANT Environment Diagnostics" in result.stdout

    def test_init_idempotent_on_existing_config(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Running init twice does not clobber an existing config."""
        repo = tmp_path / "rerun_repo"
        repo.mkdir()
        (repo / "main.py").write_text("pass\n")

        first = runner.invoke(app, ["init", str(repo)])
        assert first.exit_code == 0
        cfg_path = repo / ".cogant" / "config.json"
        original = cfg_path.read_text()

        # Mutate the config so we can detect clobber.
        cfg_path.write_text(original.replace("untitled", "custom-name"))

        second = runner.invoke(app, ["init", str(repo)])
        assert second.exit_code == 0
        assert "custom-name" in cfg_path.read_text()

    def test_init_shows_estimated_duration(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Init prints a wall-clock estimate when source files exist."""
        repo = tmp_path / "estimated_repo"
        repo.mkdir()
        for i in range(5):
            (repo / f"mod_{i}.py").write_text(f"VAR = {i}\n")

        result = runner.invoke(app, ["init", str(repo)])
        assert result.exit_code == 0
        assert "Estimated" in result.stdout


# ---------------------------------------------------- friendly errors ----


class TestFriendlyErrors:
    def test_scan_missing_path_gives_friendly_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """``cogant scan`` on a nonexistent path prints a friendly error."""
        missing = tmp_path / "does_not_exist"
        result = runner.invoke(app, ["scan", str(missing)])
        # Exit is non-zero but not a crash traceback.
        assert result.exit_code != 0
        # Either our friendly handler kicked in, or the underlying
        # Session raised something we wrapped — either way, we should
        # not see a raw Python traceback header.
        assert "Traceback" not in result.stdout

    def test_translate_missing_path_gives_friendly_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """``cogant translate`` wraps FileNotFoundError with guidance."""
        missing = tmp_path / "no_repo_here"
        out = tmp_path / "out"
        result = runner.invoke(
            app,
            ["translate", str(missing), "--output", str(out)],
        )
        assert result.exit_code != 0
        assert "Traceback" not in result.stdout


# ---------------------------------------------- extended doctor checks --


class TestExtendedDoctorChecks:
    """Behavioural tests for the mypy / ruff / mmdc / tree-sitter probes.

    These tests run the real probes (no mocks) and assert only on the
    stable contract: every check returns a :class:`DoctorCheck` with a
    known status domain. They are resilient to environments where the
    optional tool is or is not installed — the check result shape must
    be valid either way.
    """

    def test_check_mypy_returns_known_status(self) -> None:
        check = _check_mypy()
        assert isinstance(check, DoctorCheck)
        assert check.name == "mypy"
        assert check.status in {"ok", "warn", "fail"}
        assert check.detail  # always has some detail

    def test_check_ruff_returns_known_status(self) -> None:
        check = _check_ruff()
        assert isinstance(check, DoctorCheck)
        assert check.name == "ruff"
        assert check.status in {"ok", "warn", "fail"}
        assert check.detail

    def test_check_mermaid_cli_returns_known_status(self) -> None:
        check = _check_mermaid_cli()
        assert isinstance(check, DoctorCheck)
        assert "mermaid" in check.name.lower() or "mmdc" in check.name.lower()
        # mmdc is optional, so it must never hard-fail the gate.
        assert check.status in {"ok", "warn"}

    def test_check_tree_sitter_node_types_returns_known_status(self) -> None:
        check = _check_tree_sitter_node_types()
        assert isinstance(check, DoctorCheck)
        assert "tree-sitter" in check.name
        assert check.status in {"ok", "warn"}

    def test_missing_external_tool_marked_warn(self) -> None:
        """Nonexistent binaries are reported as warnings (not crashes)."""
        check = _check_external_tool(
            "definitely_not_a_real_binary_xyz",
            "fake-tool",
            required=False,
        )
        assert check.status == "warn"
        assert check.name == "fake-tool"
        assert "not on PATH" in check.detail

    def test_missing_required_external_tool_marked_fail(self) -> None:
        """Required tools fail hard so CI can gate on them."""
        check = _check_external_tool(
            "definitely_not_a_real_binary_xyz",
            "fake-required-tool",
            required=True,
        )
        assert check.status == "fail"

    def test_run_doctor_includes_extended_checks(self) -> None:
        """The extended checks are wired into the full doctor report."""
        report = run_doctor()
        names = {c.name for c in report.checks}
        assert "mypy" in names
        assert "ruff" in names
        # Mermaid is labelled with the binary name for grep-ability.
        assert any("mmdc" in n or "mermaid" in n.lower() for n in names)
        assert any("tree-sitter" in n for n in names)

    def test_extended_checks_do_not_downgrade_healthy_env(
        self, runner: CliRunner
    ) -> None:
        """Adding warn-level checks must not turn a green run into red."""
        result = runner.invoke(app, ["doctor"])
        # ``cogant doctor`` only fails when a *required* check fails.
        # The extended checks are all warn-level, so exit must stay 0.
        assert result.exit_code == 0, result.stdout


# ------------------------------------------------------------- help ----


class TestHelpSurface:
    def test_doctor_appears_in_root_help(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "doctor" in result.stdout

    @pytest.mark.parametrize(
        "subcommand",
        ["doctor", "init", "translate", "scan", "process", "benchmark"],
    )
    def test_subcommand_help_has_description(
        self, runner: CliRunner, subcommand: str
    ) -> None:
        """Each subcommand exposes a non-trivial ``--help``."""
        result = runner.invoke(app, [subcommand, "--help"])
        assert result.exit_code == 0, result.stdout
        # A description line beyond the bare ``Usage:`` header.
        assert "Usage" in result.stdout
        # The docstring body should render somewhere in the help output.
        assert len(result.stdout.strip().splitlines()) > 3
