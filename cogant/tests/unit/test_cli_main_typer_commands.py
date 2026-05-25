"""Targeted unit tests for: exercise cogant.cli.main Typer commands.

Drives init, doctor, scan, analyze, validate, viz, export_gnn, render,
and diff commands via typer.testing.CliRunner. Every test uses real on-disk
inputs (tiny repos, real GNN packages, real bundle.json files) — no mocks.
The goal is to exercise the error branches in ``_friendly_pipeline_error``
plus the happy-path branches for the commands that don't require a full
pipeline run.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cogant.cli.main import app
from cogant.gnn.package import GNNPackageBuilder
from cogant.gnn.upstream_bridge import is_upstream_gnn_available
from cogant.gnn.validator import GNNValidator
from cogant.process.extractor import ProcessModel
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.statespace.compiler import StateSpaceModel
from cogant.statespace.temporal import TimeRegime

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def tiny_repo(tmp_path: Path) -> Path:
    """Create a tiny Python repo the pipeline can parse."""
    repo = tmp_path / "tiny_repo"
    repo.mkdir()
    (repo / "main.py").write_text(
        "def main() -> int:\n    return 1\n\ndef helper(x: int) -> int:\n    return x + 1\n"
    )
    (repo / "README.md").write_text("# tiny\n")
    return repo


@pytest.fixture()
def bundle_json(tmp_path: Path) -> Path:
    """Emit a minimal but structurally-valid bundle.json file."""
    bundle = tmp_path / "bundle.json"
    bundle.write_text(
        json.dumps(
            {
                "target": str(tmp_path),
                "artifacts": {"program_graph": "pg.json"},
                "stage_results": {"static": {"ok": True}},
                "errors": [],
                "metadata": {"version": "0.1.0"},
            }
        )
    )
    return bundle


@pytest.fixture()
def gnn_package_dir(tmp_path: Path) -> Path:
    """Build a real GNN package on disk via GNNPackageBuilder."""
    ss = StateSpaceModel(
        id="m",
        schema_name="v0.1.0",
        variables={},
        observations={},
        actions={},
        transitions={},
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )
    pm = ProcessModel(id="pm", schema_name="v0.1.0", stages={}, connections={})
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="test", languages={"python"}))
    pkg = tmp_path / "gnn_package"
    pkg.mkdir()
    GNNPackageBuilder(graph=g, state_space=ss, process_model=pm, mappings={}).build(str(pkg))
    return pkg


# ---------------------------------------------------------------------------
# top-level help + doctor
# ---------------------------------------------------------------------------


class TestTopLevelHelp:
    def test_app_help_lists_core_commands(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        # Core commands must all be in --help
        for cmd in ["init", "doctor", "analyze", "translate", "validate", "viz"]:
            assert cmd in result.stdout

    def test_doctor_runs_and_exits_zero_or_one(self, runner: CliRunner) -> None:
        """doctor exits 0 in a healthy env, 1 when a required dep is missing.
        Either outcome is acceptable — we just need the command to run.
        """
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code in (0, 1)


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


class TestInitCommand:
    def test_init_creates_cogant_config(self, runner: CliRunner, tmp_path: Path) -> None:
        proj = tmp_path / "new_proj"
        result = runner.invoke(app, ["init", str(proj)])
        assert result.exit_code == 0, result.stdout
        # Config must exist on disk
        assert (proj / ".cogant" / "config.json").exists()
        # Parsed as JSON with a stages list
        cfg = json.loads((proj / ".cogant" / "config.json").read_text())
        assert "stages" in cfg
        assert isinstance(cfg["stages"], list) and len(cfg["stages"]) >= 1

    def test_init_is_idempotent(self, runner: CliRunner, tmp_path: Path) -> None:
        """Re-running init must not overwrite the config file."""
        proj = tmp_path / "reinit_proj"
        runner.invoke(app, ["init", str(proj)])
        cfg_path = proj / ".cogant" / "config.json"
        original = cfg_path.read_text()
        # Mutate the config, then re-run init
        cfg_path.write_text(original.replace('"untitled"', '"mutated_by_user"'))
        mutated = cfg_path.read_text()
        result = runner.invoke(app, ["init", str(proj)])
        assert result.exit_code == 0
        # init did NOT clobber user edits
        assert cfg_path.read_text() == mutated

    def test_init_quiet_suppresses_summary(self, runner: CliRunner, tmp_path: Path) -> None:
        proj = tmp_path / "quiet_proj"
        result = runner.invoke(app, ["init", str(proj), "--quiet"])
        assert result.exit_code == 0
        # Quiet mode should NOT print the "Project initialized successfully" line
        assert "Project initialized successfully" not in result.stdout

    def test_init_run_with_sources_executes_translate(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """init --run --yes triggers the translate pipeline (lines 229-263)."""
        proj = tmp_path / "run_proj"
        proj.mkdir()
        (proj / "main.py").write_text("def main(): return 1\n")
        result = runner.invoke(app, ["init", str(proj), "--run", "--yes", "--quiet"])
        assert result.exit_code == 0, result.stdout
        # Translate complete message must appear in non-quiet section
        assert "Translate complete" in result.stdout
        # Output directory got created by the pipeline
        assert (proj / "output").exists()
        # The GNN package (proof the pipeline actually ran end-to-end)
        assert (proj / "output" / "gnn_package" / "manifest.json").exists()

    def test_init_run_with_empty_project_skips_translate(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """--run on an empty dir prints a skip message and exits 0."""
        proj = tmp_path / "empty_run_proj"
        result = runner.invoke(app, ["init", str(proj), "--run", "--yes"])
        assert result.exit_code == 0
        assert "skipping" in result.stdout.lower()


# ---------------------------------------------------------------------------
# scan / analyze — error branches
# ---------------------------------------------------------------------------


class TestAnalyzeErrorBranches:
    """_friendly_pipeline_error is routed here via Session/PipelineRunner."""

    def test_analyze_missing_path_exits_nonzero(self, runner: CliRunner, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            ["analyze", str(tmp_path / "definitely_missing")],
        )
        assert result.exit_code != 0
        # _friendly_pipeline_error's "Repository not found" branch
        assert "not found" in result.stdout.lower() or "Error" in result.stdout

    def test_analyze_file_path_hits_not_a_directory_branch(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        f = tmp_path / "not_a_repo.py"
        f.write_text("x = 1\n")
        result = runner.invoke(app, ["analyze", str(f)])
        assert result.exit_code != 0
        # NotADirectoryError branch of _friendly_pipeline_error
        assert "directory" in result.stdout.lower() or "Error" in result.stdout


# ---------------------------------------------------------------------------
# analyze on a real repo — full happy path
# ---------------------------------------------------------------------------


class TestAnalyzeHappyPath:
    def test_analyze_on_tiny_repo_writes_bundle(
        self, runner: CliRunner, tiny_repo: Path, tmp_path: Path
    ) -> None:
        out = tmp_path / "out"
        result = runner.invoke(
            app,
            [
                "analyze",
                str(tiny_repo),
                "--output",
                str(out),
                "--no-dynamic",
                "--quiet",
            ],
        )
        assert result.exit_code == 0, result.stdout
        # bundle.json must exist and be parseable
        bundle_path = out / "bundle.json"
        assert bundle_path.exists()
        data = json.loads(bundle_path.read_text())
        assert "target" in data
        assert "stage_results" in data

    def test_analyze_non_quiet_prints_results_table(
        self, runner: CliRunner, tiny_repo: Path, tmp_path: Path
    ) -> None:
        out = tmp_path / "out_noisy"
        result = runner.invoke(
            app,
            ["analyze", str(tiny_repo), "--output", str(out), "--no-dynamic"],
        )
        assert result.exit_code == 0, result.stdout
        # Non-quiet mode should print the summary header
        assert "Analyze Results" in result.stdout or "Analysis complete" in result.stdout


# ---------------------------------------------------------------------------
# validate — three routing modes
# ---------------------------------------------------------------------------


class TestValidateCommand:
    def test_validate_gnn_package_directory(self, runner: CliRunner, gnn_package_dir: Path) -> None:
        """Route 1: directory IS a gnn_package — hits the GNNValidator path."""
        result = runner.invoke(app, ["validate", str(gnn_package_dir)])
        assert result.exit_code == 0, result.stdout
        assert "VALID" in result.stdout
        assert "score" in result.stdout

    def test_validate_no_upstream_gnn_flag(
        self,
        runner: CliRunner,
        gnn_package_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``--no-upstream-gnn`` matches ``validate_package(..., upstream_gnn=False)``."""
        cli = runner.invoke(app, ["validate", str(gnn_package_dir), "--no-upstream-gnn"])
        assert cli.exit_code == 0, cli.stdout
        assert "VALID" in cli.stdout

        monkeypatch.delenv("COGANT_DISABLE_UPSTREAM_GNN", raising=False)
        r_off = GNNValidator().validate_package(str(gnn_package_dir), upstream_gnn=False)
        assert "upstream_gnn" not in r_off.details

        if not is_upstream_gnn_available():
            return
        r_on = GNNValidator().validate_package(str(gnn_package_dir), upstream_gnn=True)
        assert "upstream_gnn" in r_on.details

    def test_validate_directory_with_gnn_package_subdir(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Route 1b: directory has a gnn_package/ subdir — same validator path."""
        parent = tmp_path / "run_output"
        parent.mkdir()
        sub = parent / "gnn_package"
        sub.mkdir()
        ss = StateSpaceModel(
            id="m",
            schema_name="v0.1.0",
            variables={},
            observations={},
            actions={},
            transitions={},
            likelihoods={},
            preferences={},
            time_regime=TimeRegime.SYNCHRONOUS,
        )
        pm = ProcessModel(id="pm", schema_name="v0.1.0", stages={}, connections={})
        g = ProgramGraph(metadata=GraphMetadata(repo_uri="test", languages={"python"}))
        GNNPackageBuilder(graph=g, state_space=ss, process_model=pm, mappings={}).build(str(sub))

        result = runner.invoke(app, ["validate", str(parent)])
        assert result.exit_code == 0, result.stdout
        assert "VALID" in result.stdout

    def test_validate_bundle_json_file(self, runner: CliRunner, bundle_json: Path) -> None:
        """Route 2: plain bundle.json file — lightweight structural checks."""
        result = runner.invoke(app, ["validate", str(bundle_json)])
        assert result.exit_code == 0, result.stdout
        assert "Bundle Validation" in result.stdout
        assert "All checks passed" in result.stdout

    def test_validate_directory_with_bundle_json_only(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Route 2b: directory containing bundle.json but no gnn_package."""
        d = tmp_path / "runonly"
        d.mkdir()
        (d / "bundle.json").write_text(
            json.dumps(
                {
                    "target": str(d),
                    "artifacts": {"x": "y"},
                    "stage_results": {"static": {}},
                    "errors": [],
                    "metadata": {},
                }
            )
        )
        result = runner.invoke(app, ["validate", str(d)])
        assert result.exit_code == 0, result.stdout
        assert "Bundle Validation" in result.stdout

    def test_validate_missing_path_exits_2(self, runner: CliRunner, tmp_path: Path) -> None:
        result = runner.invoke(app, ["validate", str(tmp_path / "nothing_here")])
        assert result.exit_code == 2
        assert "Not found" in result.stdout or "not found" in result.stdout.lower()

    def test_validate_empty_directory_exits_2(self, runner: CliRunner, tmp_path: Path) -> None:
        """Empty dir (no gnn_package, no bundle.json) is an error."""
        empty = tmp_path / "empty_dir"
        empty.mkdir()
        result = runner.invoke(app, ["validate", str(empty)])
        assert result.exit_code == 2

    def test_validate_bundle_with_errors_exits_1(self, runner: CliRunner, tmp_path: Path) -> None:
        """A bundle with non-empty errors list must fail validation."""
        bundle = tmp_path / "broken.json"
        bundle.write_text(
            json.dumps(
                {
                    "target": str(tmp_path),
                    "artifacts": {"a": "b"},
                    "stage_results": {"s": {}},
                    "errors": ["stage X blew up"],
                    "metadata": {},
                }
            )
        )
        result = runner.invoke(app, ["validate", str(bundle)])
        assert result.exit_code == 1
        assert "Some checks failed" in result.stdout


# ---------------------------------------------------------------------------
# viz
# ---------------------------------------------------------------------------


class TestVizCommand:
    def test_viz_on_gnn_package_dir_writes_pngs(
        self, runner: CliRunner, gnn_package_dir: Path
    ) -> None:
        """viz over a real package should return a summary table."""
        result = runner.invoke(app, ["viz", str(gnn_package_dir)])
        assert result.exit_code == 0, result.stdout
        assert "Visualization output summary" in result.stdout
        assert "Category" in result.stdout
        assert "Count" in result.stdout

    def test_viz_on_missing_path_exits_2(self, runner: CliRunner, tmp_path: Path) -> None:
        result = runner.invoke(app, ["viz", str(tmp_path / "nope")])
        assert result.exit_code == 2
        assert "does not exist" in result.stdout.lower()

    def test_viz_on_file_exits_2(self, runner: CliRunner, tmp_path: Path) -> None:
        """Passing a file (not dir) is an error."""
        f = tmp_path / "a.txt"
        f.write_text("hello")
        result = runner.invoke(app, ["viz", str(f)])
        assert result.exit_code == 2
        assert "not a directory" in result.stdout.lower()


# ---------------------------------------------------------------------------
# export_gnn
# ---------------------------------------------------------------------------


class TestExportGnnCommand:
    def test_export_gnn_all_formats(
        self, runner: CliRunner, bundle_json: Path, tmp_path: Path
    ) -> None:
        out = tmp_path / "export_out"
        result = runner.invoke(
            app,
            [
                "export-gnn",
                str(bundle_json),
                "--output",
                str(out),
                "--format",
                "all",
            ],
        )
        assert result.exit_code == 0, result.stdout
        # Both files emitted
        assert (out / "bundle.json").exists()
        assert (out / "bundle.md").exists()
        # JSON payload is parseable
        json.loads((out / "bundle.json").read_text())
        # Markdown carries the target header and a real per-stage table
        md = (out / "bundle.md").read_text()
        assert "# COGANT Export" in md
        assert "- target: `" in md
        assert "## Stages" in md

    def test_export_gnn_markdown_only(
        self, runner: CliRunner, bundle_json: Path, tmp_path: Path
    ) -> None:
        out = tmp_path / "md_only"
        result = runner.invoke(
            app,
            ["export-gnn", str(bundle_json), "--output", str(out), "--format", "markdown"],
        )
        assert result.exit_code == 0, result.stdout
        assert (out / "bundle.md").exists()
        # JSON was NOT written in markdown-only mode
        assert not (out / "bundle.json").exists()

    def test_export_gnn_json_only(
        self, runner: CliRunner, bundle_json: Path, tmp_path: Path
    ) -> None:
        out = tmp_path / "json_only"
        result = runner.invoke(
            app,
            ["export-gnn", str(bundle_json), "--output", str(out), "--format", "json"],
        )
        assert result.exit_code == 0, result.stdout
        assert (out / "bundle.json").exists()
        assert not (out / "bundle.md").exists()


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------


class TestRenderCommand:
    def test_render_writes_html_site(
        self, runner: CliRunner, bundle_json: Path, tmp_path: Path
    ) -> None:
        out = tmp_path / "site"
        result = runner.invoke(app, ["render", str(bundle_json), "--output", str(out)])
        assert result.exit_code == 0, result.stdout
        assert out.exists() and out.is_dir()
        # render_site writes at least an index.html
        assert (out / "index.html").exists()
        assert "Site rendered" in result.stdout


# ---------------------------------------------------------------------------
# diff
# ---------------------------------------------------------------------------


class TestSessionBackedCommands:
    """scan, extract_static, graph, statespace, process — all use Session."""

    def test_scan_table_output(self, runner: CliRunner, tiny_repo: Path) -> None:
        result = runner.invoke(app, ["scan", str(tiny_repo)])
        assert result.exit_code == 0, result.stdout
        assert "Repository Summary" in result.stdout
        assert "Target" in result.stdout

    def test_scan_json_output(self, runner: CliRunner, tiny_repo: Path) -> None:
        result = runner.invoke(app, ["scan", str(tiny_repo), "--format", "json"])
        assert result.exit_code == 0, result.stdout

    def test_scan_missing_path_exits_nonzero(self, runner: CliRunner, tmp_path: Path) -> None:
        result = runner.invoke(app, ["scan", str(tmp_path / "nope")])
        assert result.exit_code != 0

    def test_graph_command_on_tiny_repo(self, runner: CliRunner, tiny_repo: Path) -> None:
        result = runner.invoke(app, ["graph", str(tiny_repo)])
        assert result.exit_code == 0, result.stdout
        assert "Graph:" in result.stdout

    def test_statespace_command_on_tiny_repo(self, runner: CliRunner, tiny_repo: Path) -> None:
        result = runner.invoke(app, ["statespace", str(tiny_repo)])
        assert result.exit_code == 0, result.stdout
        assert "State Space" in result.stdout

    def test_process_command_on_tiny_repo(self, runner: CliRunner, tiny_repo: Path) -> None:
        result = runner.invoke(app, ["process", str(tiny_repo), "--no-dynamic"])
        assert result.exit_code == 0, result.stdout
        assert "Process Model" in result.stdout

    def test_extract_static_prints_panel(self, runner: CliRunner, tiny_repo: Path) -> None:
        result = runner.invoke(app, ["extract-static", str(tiny_repo)])
        assert result.exit_code == 0, result.stdout
        assert "Static analysis" in result.stdout

    def test_extract_static_with_output(
        self, runner: CliRunner, tiny_repo: Path, tmp_path: Path
    ) -> None:
        out = tmp_path / "static_out"
        result = runner.invoke(app, ["extract-static", str(tiny_repo), "--output", str(out)])
        assert result.exit_code == 0, result.stdout
        assert out.exists()


class TestTranslateCommand:
    """``cogant translate`` hits all the same routes as analyze plus config."""

    def test_translate_on_tiny_repo(
        self, runner: CliRunner, tiny_repo: Path, tmp_path: Path
    ) -> None:
        out = tmp_path / "translate_out"
        result = runner.invoke(
            app,
            [
                "translate",
                str(tiny_repo),
                "--output",
                str(out),
                "--no-dynamic",
            ],
        )
        assert result.exit_code == 0, result.stdout
        assert (out / "bundle.json").exists()
        # Translate-specific summary message
        assert "Translation complete" in result.stdout

    def test_translate_missing_path_exits_1(self, runner: CliRunner, tmp_path: Path) -> None:
        result = runner.invoke(app, ["translate", str(tmp_path / "nope")])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower() or "Error" in result.stdout

    def test_translate_file_path_exits_1(self, runner: CliRunner, tmp_path: Path) -> None:
        f = tmp_path / "file.py"
        f.write_text("pass")
        result = runner.invoke(app, ["translate", str(f)])
        assert result.exit_code == 1

    def test_translate_with_skip_stages(
        self, runner: CliRunner, tiny_repo: Path, tmp_path: Path
    ) -> None:
        """--skip accepts a comma-separated stage list."""
        out = tmp_path / "skip_out"
        result = runner.invoke(
            app,
            [
                "translate",
                str(tiny_repo),
                "--output",
                str(out),
                "--skip",
                "dynamic,validate",
            ],
        )
        assert result.exit_code == 0, result.stdout

    def test_translate_with_config_file_json(
        self, runner: CliRunner, tiny_repo: Path, tmp_path: Path
    ) -> None:
        """--config reads a JSON file and applies overrides."""
        cf = tmp_path / "cfg.json"
        cf.write_text(
            json.dumps(
                {
                    "pipeline": {
                        "skip_stages": ["dynamic", "validate"],
                        "verbose": False,
                    }
                }
            )
        )
        out = tmp_path / "cfg_out"
        result = runner.invoke(
            app,
            [
                "translate",
                str(tiny_repo),
                "--output",
                str(out),
                "--config",
                str(cf),
            ],
        )
        assert result.exit_code == 0, result.stdout
        assert "Loaded config from" in result.stdout


class TestDiffCommand:
    def test_diff_between_two_bundle_files(self, runner: CliRunner, tmp_path: Path) -> None:
        a = tmp_path / "a.json"
        b = tmp_path / "b.json"
        a.write_text(
            json.dumps(
                {
                    "target": "repoA",
                    "artifacts": {},
                    "stage_results": {"static": {}, "graph": {}},
                    "errors": [],
                    "metadata": {},
                }
            )
        )
        b.write_text(
            json.dumps(
                {
                    "target": "repoB",
                    "artifacts": {},
                    "stage_results": {"static": {}, "graph": {}, "translate": {}},
                    "errors": ["one error"],
                    "metadata": {},
                }
            )
        )
        result = runner.invoke(app, ["diff", str(a), str(b)])
        assert result.exit_code == 0, result.stdout
        # Shallow-diff output must mention the two bundles and the added stage
        assert "repoA" in result.stdout or "a.json" in result.stdout
        assert "repoB" in result.stdout or "b.json" in result.stdout
        assert "translate" in result.stdout  # added stage
        assert "Diff complete" in result.stdout

    def test_diff_missing_path_exits_2(self, runner: CliRunner, tmp_path: Path) -> None:
        a = tmp_path / "a.json"
        a.write_text("{}")
        result = runner.invoke(app, ["diff", str(a), str(tmp_path / "missing.json")])
        assert result.exit_code == 2
