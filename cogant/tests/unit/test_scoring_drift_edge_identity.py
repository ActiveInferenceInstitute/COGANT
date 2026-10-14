"""DriftAnalyzer must detect rewired edges in serialized program graphs.

Serialized COGANT edges (``program_graph_to_dict``) name their
endpoints ``source_id`` / ``target_id``. The structural diff used to
key edges on the nonexistent ``source`` / ``target`` fields, so every
edge collapsed to ``"None→None"`` and ``edges_added_count`` /
``edges_removed_count`` stayed 0 however the call graph changed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from cogant.api.bundle import Bundle
from cogant.api.orchestration import (
    program_graph_to_dict,
    run_graph,
    run_ingest,
    run_static,
)
from cogant.scoring.drift import DriftAnalyzer

pytestmark = pytest.mark.unit

_F1_CALLS_F2 = "def f1():\n    return f2()\n\n\ndef f2():\n    return 1\n"
_F2_CALLS_F1 = "def f1():\n    return 1\n\n\ndef f2():\n    return f1()\n"


def _serialized_graph(repo: Path, source: str) -> dict[str, Any]:
    """Write ``source`` as ``repo/m.py`` and return its serialized graph."""
    repo.mkdir(exist_ok=True)
    (repo / "m.py").write_text(source, encoding="utf-8")
    bundle = Bundle(target=str(repo))
    run_ingest(str(repo), bundle)
    run_static(bundle)
    run_graph(bundle, str(repo))
    payload = program_graph_to_dict(bundle.artifacts["_program_graph"])
    serialized: dict[str, Any] = json.loads(json.dumps(payload, default=str))
    return serialized


def test_reversed_call_edge_counts_as_one_added_and_one_removed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    baseline = _serialized_graph(repo, _F1_CALLS_F2)
    current = _serialized_graph(repo, _F2_CALLS_F1)

    struct = DriftAnalyzer({"graph": baseline}, {"graph": current}).compute_structural_drift()

    assert struct["edges_added_count"] == 1
    assert struct["edges_removed_count"] == 1


def test_list_shaped_serialized_edges_are_keyed_by_endpoints(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    baseline = _serialized_graph(repo, _F1_CALLS_F2)
    current = _serialized_graph(repo, _F2_CALLS_F1)

    def as_lists(graph: dict[str, Any]) -> dict[str, Any]:
        return {"nodes": list(graph["nodes"].values()), "edges": list(graph["edges"].values())}

    struct = DriftAnalyzer(
        {"graph": as_lists(baseline)}, {"graph": as_lists(current)}
    ).compute_structural_drift()

    assert (struct["edges_added_count"], struct["edges_removed_count"]) == (1, 1)


def test_edge_kind_change_between_same_endpoints_is_reported() -> None:
    baseline = {"edges": [{"source_id": "a", "target_id": "b", "kind": "calls"}]}
    current = {"edges": [{"source_id": "a", "target_id": "b", "kind": "imports"}]}

    struct = DriftAnalyzer({"graph": baseline}, {"graph": current}).compute_structural_drift()

    assert (struct["edges_added_count"], struct["edges_removed_count"]) == (1, 1)


def test_unchanged_source_reports_no_edge_drift(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    baseline = _serialized_graph(repo, _F1_CALLS_F2)
    current = _serialized_graph(repo, _F1_CALLS_F2)

    struct = DriftAnalyzer({"graph": baseline}, {"graph": current}).compute_structural_drift()

    assert (struct["edges_added_count"], struct["edges_removed_count"]) == (0, 0)
