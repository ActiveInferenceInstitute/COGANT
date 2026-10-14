"""Drift analysis must read the state space stored in ``model.gnn.json``.

``model.gnn.json`` (and therefore ``cogant diff`` on two
``gnn_package/`` directories) stores the state space as ``variables`` /
``observations`` / ``actions`` dicts keyed by id. DriftAnalyzer only
understood the pydantic-schema shape (``states`` lists keyed by
``var_id`` / ``modality_id`` / ``action_id``): iterating the dicts
yielded string keys and ``compute_state_space_drift`` raised
``AttributeError``, while the churn score never saw any state variable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cogant.api.bundle import Bundle
from cogant.api.orchestration import (
    run_export,
    run_graph,
    run_ingest,
    run_process,
    run_statespace,
    run_static,
    run_translate,
)
from cogant.cli.diff import diff_command, load_bundle
from cogant.scoring.drift import DriftAnalyzer

pytestmark = pytest.mark.unit

_COUNTER = (
    "class Counter:\n    def __init__(self):\n        self.count = 0\n\n"
    "    def get_count(self):\n        return self.count\n\n"
    "    def increment(self):\n        self.count += 1\n"
)


def _export_package(repo: Path, out: Path) -> Path:
    """Run the pipeline on ``repo`` and return the written ``gnn_package`` dir."""
    bundle = Bundle(target=str(repo))
    run_ingest(str(repo), bundle)
    run_static(bundle)
    run_graph(bundle, str(repo))
    run_translate(bundle)
    run_statespace(bundle, str(repo))
    run_process(bundle, str(repo))
    run_export(bundle, str(out), render_visualizations=False)
    return out / "gnn_package"


@pytest.fixture
def two_packages_of_same_source(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "m.py").write_text(_COUNTER, encoding="utf-8")
    return _export_package(repo, tmp_path / "out_a"), _export_package(repo, tmp_path / "out_b")


def test_state_space_drift_reads_dict_shaped_gnn_state_space(
    two_packages_of_same_source: tuple[Path, Path],
) -> None:
    package_a, package_b = two_packages_of_same_source
    bundle_a = load_bundle(package_a)
    assert isinstance(bundle_a["state_space"]["observations"], dict)
    assert bundle_a["state_space"]["observations"]

    analyzer = DriftAnalyzer(bundle_a, load_bundle(package_b))
    ss_drift = analyzer.compute_state_space_drift()

    assert all(count == 0 for count in ss_drift.values())


def test_semantic_churn_counts_gnn_state_variables() -> None:
    baseline = {"state_space": {"variables": {"v1": {"id": "v1"}}}}
    current = {"state_space": {"variables": {"v1": {"id": "v1"}, "v2": {"id": "v2"}}}}

    analyzer = DriftAnalyzer(baseline, current)

    assert analyzer.compute_state_space_drift()["state_vars_added"] == 1
    assert analyzer.compute_semantic_churn_score() > 0.0


def test_diff_command_compares_two_gnn_package_directories(
    two_packages_of_same_source: tuple[Path, Path],
) -> None:
    package_a, package_b = two_packages_of_same_source

    report = diff_command(str(package_a), str(package_b))

    assert "## State Space Changes" in report
    assert "**Overall Drift Score**: 0.0%" in report
