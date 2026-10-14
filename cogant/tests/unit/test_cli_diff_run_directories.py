"""``cogant diff`` on real translate/analyze run directories.

The run directories are produced by the real pipeline, so the on-disk shapes
(id-keyed graph collections with ``source_id``/``target_id`` edges, the
compiler's id-keyed ``state_space.json``, mappings inside
``gnn_package/model.gnn.json``) are the ones users actually diff.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cogant.api.pipeline import PipelineConfig, PipelineRunner
from cogant.cli.diff import diff_command, load_bundle
from cogant.cli.main import app
from cogant.tools.organize_example_outputs import organize_run_dir

COUNTER_SOURCE = (
    "class Counter:\n"
    "    def __init__(self):\n"
    "        self.n = 0\n"
    "    def inc(self):\n"
    "        self.n += 1\n"
    "    def get(self):\n"
    "        return self.n\n"
)

LEDGER_SOURCE = (
    "class Ledger:\n"
    "    def __init__(self):\n"
    "        self.entries = []\n"
    "    def add(self, value):\n"
    "        self.entries.append(value)\n"
    "    def reset(self):\n"
    "        self.entries = []\n"
    "    def total(self):\n"
    "        return sum(self.entries)\n"
    "    def latest(self):\n"
    "        return self.entries[-1]\n"
)


def _run_dir(tmp_path: Path, name: str, module: str, source: str, *, layout: bool = False) -> Path:
    repo = tmp_path / f"{name}_repo"
    repo.mkdir()
    (repo / f"{module}.py").write_text(source, encoding="utf-8")
    out = tmp_path / name
    config = PipelineConfig(output_dir=str(out), render_visualizations=False, skip_dynamic=True)
    bundle = PipelineRunner().run(str(repo), config)
    assert not bundle.errors, bundle.errors
    if layout:
        organize_run_dir(out, dry_run=False)
    return out


def _metric(report: str, section: str, label: str) -> int:
    body = report.split(f"### {section} Metrics", 1)[1]
    match = re.search(rf"- \*\*{label}\*\*: (\d+)", body)
    assert match, f"{label} missing from {section} metrics"
    return int(match.group(1))


def _drift_count(report: str, heading: str, label: str) -> int:
    body = report.split(f"**{heading}**:", 1)[1]
    match = re.search(rf"- {label}: (\d+)", body)
    assert match, f"{heading}/{label} missing from drift report"
    return int(match.group(1))


@pytest.fixture()
def counter_run(tmp_path: Path) -> Path:
    return _run_dir(tmp_path, "counter_run", "counter", COUNTER_SOURCE)


@pytest.fixture()
def ledger_run(tmp_path: Path) -> Path:
    return _run_dir(tmp_path, "ledger_run", "ledger", LEDGER_SOURCE)


def test_cli_diff_of_two_run_directories_writes_report(
    tmp_path: Path, counter_run: Path, ledger_run: Path
) -> None:
    report_path = tmp_path / "diff.md"
    result = CliRunner().invoke(
        app, ["diff", str(counter_run), str(ledger_run), "-o", str(report_path)]
    )
    assert result.exit_code == 0, result.output
    assert report_path.is_file()
    report = report_path.read_text(encoding="utf-8")

    graph_b = json.loads((ledger_run / "program_graph.json").read_text(encoding="utf-8"))
    assert _metric(report, "Current", "Nodes") == len(graph_b["nodes"]) > 0
    assert _metric(report, "Current", "Edges") == len(graph_b["edges"]) > 1
    # Every edge of the ledger graph is new relative to the counter graph.
    assert _drift_count(report, "Edges", "Added") == len(graph_b["edges"])


def test_diff_loads_state_space_and_mappings_from_run_directory(
    counter_run: Path, ledger_run: Path
) -> None:
    bundle = load_bundle(ledger_run)
    state_space = json.loads((ledger_run / "state_space.json").read_text(encoding="utf-8"))
    gnn_model = json.loads((ledger_run / "gnn_model.json").read_text(encoding="utf-8"))
    assert bundle["state_space"]["variables"].keys() == state_space["variables"].keys()
    assert len(bundle["mappings"]) == gnn_model["mapping_count"] > 0

    report = diff_command(str(counter_run), str(ledger_run))
    assert _metric(report, "Current", "State Variables") == len(state_space["variables"]) > 0
    assert _metric(report, "Current", "Observations") == len(state_space["observations"]) > 0
    assert _metric(report, "Current", "Actions") == len(state_space["actions"]) > 0
    assert _drift_count(report, "Mappings", "New") == gnn_model["mapping_count"]
    assert "Semantic Coverage**: 0.00%" not in report.split("### Current Metrics", 1)[1]


def test_diff_reads_layout_output_run_directories(tmp_path: Path) -> None:
    counter = _run_dir(tmp_path, "counter_layout", "counter", COUNTER_SOURCE, layout=True)
    ledger = _run_dir(tmp_path, "ledger_layout", "ledger", LEDGER_SOURCE, layout=True)
    assert not (ledger / "program_graph.json").exists()

    report = diff_command(str(counter), str(ledger))
    graph_b = json.loads((ledger / "data" / "program_graph.json").read_text(encoding="utf-8"))
    assert _metric(report, "Current", "Nodes") == len(graph_b["nodes"]) > 0
    assert _metric(report, "Current", "State Variables") > 0


def test_diff_of_two_runs_of_same_code_reports_no_changes(tmp_path: Path) -> None:
    first = _run_dir(tmp_path, "first", "counter", COUNTER_SOURCE)
    repo_second = tmp_path / "second_repo"
    # Same module path and content: ids are content-derived, timestamps differ.
    second = tmp_path / "second"
    repo_second.mkdir()
    (repo_second / "counter.py").write_text(COUNTER_SOURCE, encoding="utf-8")
    PipelineRunner().run(
        str(repo_second),
        PipelineConfig(output_dir=str(second), render_visualizations=False, skip_dynamic=True),
    )

    report = diff_command(str(first), str(second))
    assert "**Overall Drift Score**: 0.0%" in report
    assert _drift_count(report, "Nodes", "Changed") == 0
    assert _drift_count(report, "Mappings", "Changed") == 0
    assert _drift_count(report, "State Variables", "Changed") == 0
