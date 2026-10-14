"""Re-running the pipeline on unchanged source must not report changed items.

Serialized nodes carry ``created_at`` and semantic mappings carry
``created_at`` / ``updated_at`` plus per-provenance ``timestamp``
values, all stamped with the wall clock of the run. DriftAnalyzer used
to compare whole payloads, so two runs over identical code reported
every node and every mapping as "changed".
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

from cogant.api.bundle import Bundle
from cogant.api.orchestration import (
    program_graph_to_dict,
    run_graph,
    run_ingest,
    run_static,
    run_translate,
)
from cogant.scoring.drift import DriftAnalyzer

pytestmark = pytest.mark.unit

_SOURCE = (
    "STATE = {}\n\n\ndef read_state():\n    return STATE\n\n\n"
    "def update_state(x):\n    STATE['x'] = x\n"
)


def _run_bundle(repo: Path) -> dict[str, Any]:
    """Run ingest→translate on ``repo`` and return a JSON round-tripped bundle."""
    bundle = Bundle(target=str(repo))
    run_ingest(str(repo), bundle)
    run_static(bundle)
    run_graph(bundle, str(repo))
    run_translate(bundle)
    payload = {
        "graph": program_graph_to_dict(bundle.artifacts["_program_graph"]),
        "mappings": {k: asdict(v) for k, v in bundle.artifacts["_semantic_mappings"].items()},
    }
    serialized: dict[str, Any] = json.loads(json.dumps(payload, default=str))
    return serialized


@pytest.fixture
def two_runs_of_same_source(tmp_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "m.py").write_text(_SOURCE, encoding="utf-8")
    return _run_bundle(repo), _run_bundle(repo)


def test_identical_source_reports_no_changed_nodes(
    two_runs_of_same_source: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    baseline, current = two_runs_of_same_source
    assert baseline["graph"]["nodes"] != current["graph"]["nodes"]  # timestamps differ

    struct = DriftAnalyzer(baseline, current).compute_structural_drift()

    assert struct["nodes_changed_count"] == 0


def test_identical_source_reports_no_changed_mappings(
    two_runs_of_same_source: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    baseline, current = two_runs_of_same_source
    assert baseline["mappings"]

    sem = DriftAnalyzer(baseline, current).compute_semantic_drift()

    assert (sem["new_count"], sem["lost_count"], sem["changed_count"]) == (0, 0, 0)


def test_node_label_change_is_still_reported() -> None:
    baseline = {"graph": {"nodes": [{"id": "n1", "name": "old", "created_at": "t0"}]}}
    current = {"graph": {"nodes": [{"id": "n1", "name": "new", "created_at": "t1"}]}}

    struct = DriftAnalyzer(baseline, current).compute_structural_drift()

    assert struct["nodes_changed"] == ["n1"]
