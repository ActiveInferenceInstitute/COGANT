"""Targeted unit tests for: exercise cogant.reverse.cli commands end-to-end.

Uses typer.testing.CliRunner to drive reverse_command and roundtrip_command
with a real GNN markdown file produced by GNNMarkdownFormatter. Both the
Rich-table and --json output paths are tested, plus the error branches.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from cogant.gnn.formatter import GNNMarkdownFormatter
from cogant.process.extractor import ProcessModel
from cogant.reverse.cli import reverse_command, roundtrip_command
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.statespace.compiler import StateSpaceModel
from cogant.statespace.temporal import TimeRegime


@pytest.fixture()
def gnn_markdown(tmp_path: Path) -> Path:
    """Produce a valid (if empty) GNN markdown file on disk."""
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
    pm = ProcessModel(id="m", schema_name="v0.1.0", stages={}, connections={})
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="test", languages={"python"}))
    formatter = GNNMarkdownFormatter(g, ss, pm, {})
    gnn_path = tmp_path / "model.gnn.md"
    gnn_path.write_text(formatter.format())
    return gnn_path


@pytest.fixture()
def typer_app() -> typer.Typer:
    app = typer.Typer()
    app.command("reverse")(reverse_command)
    app.command("roundtrip")(roundtrip_command)
    return app


class TestReverseCommand:
    """Drive cogant.reverse.cli.reverse_command via CliRunner."""

    def test_reverse_command_rich_output(
        self, gnn_markdown: Path, tmp_path: Path, typer_app: typer.Typer
    ) -> None:
        runner = CliRunner()
        out_dir = tmp_path / "out"
        result = runner.invoke(
            typer_app,
            ["reverse", str(gnn_markdown), "--output", str(out_dir)],
        )
        assert result.exit_code == 0, result.stdout
        # The Rich table header shows up in the captured stdout
        assert "Reverse synthesis summary" in result.stdout
        assert "Source GNN" in result.stdout
        assert "Output package" in result.stdout
        # The package directory must actually exist on disk
        assert out_dir.exists()

    def test_reverse_command_json_output(
        self, gnn_markdown: Path, tmp_path: Path, typer_app: typer.Typer
    ) -> None:
        runner = CliRunner()
        out_dir = tmp_path / "out"
        result = runner.invoke(
            typer_app,
            ["reverse", str(gnn_markdown), "--output", str(out_dir), "--json"],
        )
        assert result.exit_code == 0, result.stdout
        # The JSON payload must be parseable and contain the keys we emit.
        # Rich may colourize, so locate the first '{' and the last '}'.
        start = result.stdout.find("{")
        end = result.stdout.rfind("}")
        assert start >= 0 and end > start
        payload = json.loads(result.stdout[start : end + 1])
        assert payload["source_gnn"] == str(gnn_markdown)
        assert "package_path" in payload
        assert "package_name" in payload
        assert "hidden_states" in payload
        assert "observations" in payload
        assert "actions" in payload
        assert "policies" in payload
        assert "constraints" in payload
        assert "has_A_matrix" in payload
        assert "has_B_tensor" in payload
        assert "has_C_vector" in payload
        assert "has_D_vector" in payload

    def test_reverse_command_missing_file_exits_nonzero(
        self, tmp_path: Path, typer_app: typer.Typer
    ) -> None:
        """Typer's ``exists=True`` argument validation rejects a missing file."""
        runner = CliRunner()
        result = runner.invoke(
            typer_app,
            ["reverse", str(tmp_path / "nonexistent.gnn.md")],
        )
        # Typer argument validation yields exit code 2
        assert result.exit_code != 0


class TestRoundtripCommand:
    """Drive cogant.reverse.cli.roundtrip_command via CliRunner."""

    def test_roundtrip_file_mode_rich_output(
        self, gnn_markdown: Path, tmp_path: Path, typer_app: typer.Typer
    ) -> None:
        runner = CliRunner()
        result = runner.invoke(
            typer_app,
            ["roundtrip", str(gnn_markdown), "--threshold", "0", "--keep-tmp"],
        )
        assert result.exit_code == 0, result.stdout
        assert "Round-trip verification" in result.stdout
        # Empty-GNN round-trip still reports an explicit status tier.
        assert "PRESERVED" in result.stdout or "DRIFT" in result.stdout

    def test_roundtrip_file_mode_json_output(
        self, gnn_markdown: Path, tmp_path: Path, typer_app: typer.Typer
    ) -> None:
        runner = CliRunner()
        result = runner.invoke(
            typer_app,
            ["roundtrip", str(gnn_markdown), "--json", "--threshold", "0", "--keep-tmp"],
        )
        assert result.exit_code == 0, result.stdout
        start = result.stdout.find("{")
        end = result.stdout.rfind("}")
        assert start >= 0 and end > start
        payload = json.loads(result.stdout[start : end + 1])
        assert "roundtrip_status" in payload
        assert "role_preservation_score" in payload
        assert "structurally_isomorphic" in payload
        assert "original_roles" in payload
        assert "synthesized_roles" in payload
        assert "matrix_score" in payload
        assert "structural_score" in payload
        assert "role_confusion" in payload
        assert "graph_edit_distance" in payload
        assert payload["generated_code"]["status"] == "not_requested"
        assert "shape_match" in payload
        assert "threshold" in payload

    def test_roundtrip_custom_threshold(
        self, gnn_markdown: Path, tmp_path: Path, typer_app: typer.Typer
    ) -> None:
        runner = CliRunner()
        result = runner.invoke(
            typer_app,
            ["roundtrip", str(gnn_markdown), "--json", "--threshold", "0.95"],
        )
        assert result.exit_code == 1
        start = result.stdout.find("{")
        end = result.stdout.rfind("}")
        payload = json.loads(result.stdout[start : end + 1])
        assert payload["threshold"] == 0.95

    def test_roundtrip_with_output_dir(
        self, gnn_markdown: Path, tmp_path: Path, typer_app: typer.Typer
    ) -> None:
        runner = CliRunner()
        out_dir = tmp_path / "roundtrip_out"
        result = runner.invoke(
            typer_app,
            [
                "roundtrip",
                str(gnn_markdown),
                "--output",
                str(out_dir),
                "--threshold",
                "0",
                "--keep-tmp",
            ],
        )
        assert result.exit_code == 0
        metrics = out_dir / "metrics.json"
        assert metrics.is_file()
        payload = json.loads(metrics.read_text(encoding="utf-8"))
        assert payload["schema_version"] == "2.0"
        assert payload["role_preservation_score"] == 0.0
        assert "matrix_score" in payload
        assert payload["generated_code"]["compile_status"] == "passed"
        assert payload["generated_code"]["status"] == "passed"
        assert payload["generated_code"]["test_status"] == "passed"
        assert "role_confusion" in payload
