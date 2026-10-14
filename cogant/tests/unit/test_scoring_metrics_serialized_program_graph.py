"""CodebaseMetrics must read the program graph COGANT actually writes.

``program_graph.json`` is produced by
:func:`cogant.api.orchestration.program_graph_to_dict`: ``nodes`` and
``edges`` are dicts keyed by id, nodes carry ``path`` (no
``parent_id``), and edges name endpoints ``source_id`` / ``target_id``.
Semantic mappings are keyed by mapping id and reference nodes through
``graph_fragment_node_ids``. Before the fix, iterating the dict-shaped
collections yielded string keys and ``coupling_score`` raised
``AttributeError``, which made ``cogant diff <dirA> <dirB>`` crash on
every real run directory.
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
)
from cogant.cli.diff import diff_command
from cogant.scoring.metrics import CodebaseMetrics

pytestmark = pytest.mark.unit


def _two_module_graph(tmp_path: Path) -> dict[str, Any]:
    """Build and serialize the program graph of a two-file repo.

    ``a.run`` calls ``data.load`` and module ``a`` imports ``data``, so
    the graph holds two CONTAINS edges (intra-module) and an IMPORTS
    plus a CALLS edge (cross-module).
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "data.py").write_text("CACHE = {}\n\n\ndef load():\n    return CACHE\n")
    (repo / "a.py").write_text("from data import load\n\n\ndef run():\n    return load()\n")
    bundle = Bundle(target=str(repo))
    run_ingest(str(repo), bundle)
    run_static(bundle)
    run_graph(bundle, str(repo))
    payload = program_graph_to_dict(bundle.artifacts["_program_graph"])
    serialized: dict[str, Any] = json.loads(json.dumps(payload, default=str))
    return serialized


def _edge_kinds(graph: dict[str, Any]) -> list[str]:
    return sorted(edge["kind"] for edge in graph["edges"].values())


def test_coupling_and_cohesion_split_serialized_edges_by_source_file(tmp_path: Path) -> None:
    graph = _two_module_graph(tmp_path)
    assert _edge_kinds(graph) == ["calls", "contains", "contains", "imports"]

    metrics = CodebaseMetrics(graph, {}, {})

    assert metrics.coupling_score() == pytest.approx(0.5)
    assert metrics.cohesion_score() == pytest.approx(0.5)
    assert metrics.summary().edge_count == 4


def test_semantic_coverage_reads_graph_fragment_node_ids(tmp_path: Path) -> None:
    graph = _two_module_graph(tmp_path)
    run_id = next(n["id"] for n in graph["nodes"].values() if n["qualified_name"] == "a.run")
    mappings = {
        "act_run_mapping": {
            "id": "act_run_mapping",
            "kind": "action",
            "graph_fragment_node_ids": [run_id],
        }
    }

    metrics = CodebaseMetrics(graph, {}, mappings)

    assert metrics.semantic_coverage() == pytest.approx(1 / len(graph["nodes"]))


def test_diff_command_reports_metrics_for_serialized_run_directories(tmp_path: Path) -> None:
    graph = _two_module_graph(tmp_path)
    for name in ("run_a", "run_b"):
        out = tmp_path / name
        out.mkdir()
        (out / "program_graph.json").write_text(json.dumps(graph), encoding="utf-8")

    report = diff_command(str(tmp_path / "run_a"), str(tmp_path / "run_b"))

    assert report.count("- **Coupling Score**: 50.00%") == 2
    assert report.count("- **Cohesion Score**: 50.00%") == 2


def test_list_shaped_graph_with_source_id_edges_matches_dict_shape(tmp_path: Path) -> None:
    graph = _two_module_graph(tmp_path)
    as_lists = {
        "nodes": list(graph["nodes"].values()),
        "edges": list(graph["edges"].values()),
    }

    assert asdict(CodebaseMetrics(as_lists, {}, {}).summary()) == asdict(
        CodebaseMetrics(graph, {}, {}).summary()
    )
