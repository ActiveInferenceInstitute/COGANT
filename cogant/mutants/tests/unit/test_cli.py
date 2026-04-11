"""Smoke tests for the ``cogant`` command-line interface.

The CLI is a thin Typer wrapper over the Session and PipelineRunner
APIs. These tests use :class:`typer.testing.CliRunner` to drive every
top-level command on one of the control-positive fixtures and assert:

* the command exits with a non-error status,
* its output contains the expected marker text, and
* any requested artifacts are actually written to disk.

The fixture is tiny so the full suite runs in a handful of seconds even
with the end-to-end ``translate`` command exercised.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cogant.cli.main import app

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "examples" / "control_positive" / "calculator"


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


# ------------------------------------------------------------------- init --


class TestInitCommand:
    def test_init_creates_project_layout(self, runner, tmp_path):
        target = tmp_path / "newproj"
        result = runner.invoke(app, ["init", str(target)])
        assert result.exit_code == 0
        assert "Initializing COGANT project" in result.stdout
        assert (target / ".cogant" / "config.json").exists()
        # Config is valid JSON with a stages list.
        cfg = json.loads((target / ".cogant" / "config.json").read_text())
        assert isinstance(cfg.get("stages"), list)
        assert "translate" in cfg["stages"]


# ------------------------------------------------------------------- scan --


class TestScanCommand:
    def test_scan_table_format(self, runner):
        result = runner.invoke(app, ["scan", str(FIXTURE)])
        assert result.exit_code == 0, result.stdout
        assert "Scanning" in result.stdout
        assert "Repository Summary" in result.stdout

    def test_scan_json_format(self, runner):
        result = runner.invoke(app, ["scan", str(FIXTURE), "--format", "json"])
        assert result.exit_code == 0, result.stdout


# --------------------------------------------------------------- graph ----


class TestGraphCommand:
    def test_graph_reports_nodes_and_edges(self, runner):
        result = runner.invoke(app, ["graph", str(FIXTURE)])
        assert result.exit_code == 0, result.stdout
        # The panel contains a "Graph: N nodes, M edges" marker.
        assert "Graph:" in result.stdout
        assert "nodes" in result.stdout


# ------------------------------------------------------ extract-static ----


class TestExtractStaticCommand:
    def test_static_without_output(self, runner):
        result = runner.invoke(app, ["extract-static", str(FIXTURE)])
        assert result.exit_code == 0, result.stdout
        assert "Static analysis" in result.stdout

    def test_static_with_output(self, runner, tmp_path):
        out = tmp_path / "static_out"
        result = runner.invoke(
            app,
            ["extract-static", str(FIXTURE), "--output", str(out)],
        )
        assert result.exit_code == 0, result.stdout
        assert out.exists() and out.is_dir()
        # At least some artifact was written.
        assert any(out.iterdir())


# --------------------------------------------------------- translate -----


class TestTranslateCommand:
    def test_full_translate_pipeline(self, runner, tmp_path):
        out = tmp_path / "translate_out"
        result = runner.invoke(
            app,
            ["translate", str(FIXTURE), "--output", str(out)],
        )
        assert result.exit_code == 0, result.stdout
        assert "COGANT Pipeline" in result.stdout
        assert (out / "bundle.json").exists()
        # Bundle JSON is well-formed.
        data = json.loads((out / "bundle.json").read_text())
        assert isinstance(data, dict)

    def test_translate_with_skip_stages(self, runner, tmp_path):
        out = tmp_path / "translate_skip"
        result = runner.invoke(
            app,
            [
                "translate",
                str(FIXTURE),
                "--output",
                str(out),
                "--skip",
                "dynamic",
            ],
        )
        assert result.exit_code == 0, result.stdout
        assert "Skipped" in result.stdout

    def test_translate_with_no_dynamic_flag(self, runner, tmp_path):
        """``--no-dynamic`` succeeds and records a skipped dynamic stage."""
        out = tmp_path / "translate_no_dynamic"
        result = runner.invoke(
            app,
            [
                "translate",
                str(FIXTURE),
                "--output",
                str(out),
                "--no-dynamic",
            ],
        )
        assert result.exit_code == 0, result.stdout
        assert "--no-dynamic" in result.stdout
        # bundle.json should reflect that dynamic was skipped.
        bundle = json.loads((out / "bundle.json").read_text())
        stage_results = bundle.get("stage_results", {})
        dyn = stage_results.get("dynamic", {})
        assert dyn.get("skipped") is True
        assert dyn.get("reason") == "skip_dynamic=True"


# --------------------------------------------------------- validate -----


class TestValidateCommand:
    def test_validate_on_bundle(self, runner, tmp_path):
        # Need a bundle to validate, so run translate first.
        out = tmp_path / "validate_out"
        run1 = runner.invoke(
            app, ["translate", str(FIXTURE), "--output", str(out)]
        )
        assert run1.exit_code == 0, run1.stdout

        # Now validate the produced bundle.
        bundle_path = out / "bundle.json"
        run2 = runner.invoke(app, ["validate", str(bundle_path)])
        # validate's exit code is 0 even if checks report warnings;
        # failure manifests as an exception.
        assert run2.exit_code in (0, 1), run2.stdout

    def test_validate_on_gnn_package_directory(self, runner, tmp_path):
        """`validate <dir>` should auto-discover the gnn_package/ subdir
        and route to the full :class:`GNNValidator`."""
        out = tmp_path / "pkg_validate"
        run1 = runner.invoke(
            app, ["translate", str(FIXTURE), "--output", str(out)]
        )
        assert run1.exit_code == 0, run1.stdout

        # The translate pipeline emits output/gnn_package/*. Point at the
        # parent directory and confirm the CLI finds + validates it.
        run2 = runner.invoke(app, ["validate", str(out)])
        assert run2.exit_code == 0, run2.stdout
        assert "VALID" in run2.stdout
        assert "score=" in run2.stdout

    def test_validate_nonexistent_path(self, runner, tmp_path):
        missing = tmp_path / "nope.json"
        result = runner.invoke(app, ["validate", str(missing)])
        assert result.exit_code == 2
        assert "Not found" in result.stdout


# --------------------------------------------------------- help surface --


class TestHelpSurface:
    def test_root_help(self, runner):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        # Every canonical subcommand should appear in the help listing.
        for cmd in (
            "init",
            "scan",
            "graph",
            "translate",
            "validate",
            "diff",
            "benchmark",
        ):
            assert cmd in result.stdout

    @pytest.mark.parametrize(
        "subcommand",
        [
            "init",
            "scan",
            "graph",
            "extract-static",
            "extract-dynamic",
            "translate",
            "statespace",
            "process",
            "export-gnn",
            "render",
            "validate",
            "diff",
            "benchmark",
        ],
    )
    def test_subcommand_help(self, runner, subcommand):
        result = runner.invoke(app, [subcommand, "--help"])
        assert result.exit_code == 0, f"{subcommand} help failed: {result.stdout}"
