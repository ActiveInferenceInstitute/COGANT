"""Regression test for compute_structural_drift crash on run-dir code path.

Run directories persist program graphs in the dict-shape emitted by
``cogant.api.orchestration._dump_program_graph``:

    "nodes": {node_id: {...}, ...}
    "edges": {edge_id: {...}, ...}

When ``cogant diff`` loads such a bundle via
``cogant.cli.diff.load_bundle`` and hands it to
``DriftAnalyzer.compute_structural_drift``, the comprehension
``{n.get("id"): n for n in graph.get("nodes", [])}`` iterates the dict
which yields the string keys (node ids). Calling ``.get("id")`` on a
string raised ``AttributeError`` and crashed the drift pipeline.

These tests reproduce that real-world scenario: build a bundle whose
``graph`` key has the orchestration dict-shape (no lists, no mocks),
write it to ``tmp_path`` as ``program_graph.json``, load it through the
public CLI helper, and run the real ``DriftAnalyzer`` against it.
"""

from __future__ import annotations

import json
from pathlib import Path

from cogant.cli.diff import load_bundle
from cogant.scoring.drift import DriftAnalyzer


def _dict_shape_graph() -> dict[str, object]:
    """Return a program graph in the run-dir dict shape."""
    return {
        "type": "program_graph",
        "metadata": {"repo_uri": "test", "languages": ["python"], "version": "1"},
        "nodes": {
            "fn.alpha": {"id": "fn.alpha", "kind": "function", "attributes": {}},
            "fn.beta": {"id": "fn.beta", "kind": "function", "attributes": {}},
            "fn.gamma": {"id": "fn.gamma", "kind": "function", "attributes": {}},
        },
        "edges": {
            "e1": {"source": "fn.alpha", "target": "fn.beta", "kind": "CALLS"},
            "e2": {"source": "fn.beta", "target": "fn.gamma", "kind": "CALLS"},
        },
        "statistics": {},
    }


def _dict_shape_graph_modified() -> dict[str, object]:
    """Same shape, with one node removed and one added — yields real drift."""
    return {
        "type": "program_graph",
        "metadata": {"repo_uri": "test", "languages": ["python"], "version": "1"},
        "nodes": {
            "fn.alpha": {"id": "fn.alpha", "kind": "function", "attributes": {}},
            "fn.beta": {"id": "fn.beta", "kind": "function", "attributes": {}},
            "fn.delta": {"id": "fn.delta", "kind": "function", "attributes": {}},
        },
        "edges": {
            "e1": {"source": "fn.alpha", "target": "fn.beta", "kind": "CALLS"},
            "e3": {"source": "fn.beta", "target": "fn.delta", "kind": "CALLS"},
        },
        "statistics": {},
    }


def test_compute_structural_drift_handles_dict_shaped_nodes_and_edges(
    tmp_path: Path,
) -> None:
    """Dict-shaped graphs from run dirs must not crash drift analysis.

    Writes two real ``program_graph.json`` files in the orchestration
    dict shape, loads them through the real CLI helper, constructs a
    real ``DriftAnalyzer``, and invokes ``compute_structural_drift``.
    Pre-fix this raised ``AttributeError: 'str' object has no
    attribute 'get'``.
    """
    run_a = tmp_path / "run_a"
    run_b = tmp_path / "run_b"
    run_a.mkdir()
    run_b.mkdir()

    (run_a / "program_graph.json").write_text(json.dumps(_dict_shape_graph()))
    (run_b / "program_graph.json").write_text(json.dumps(_dict_shape_graph_modified()))

    bundle_a = load_bundle(run_a)
    bundle_b = load_bundle(run_b)

    analyzer = DriftAnalyzer(bundle_a, bundle_b)

    # Must not raise.
    result = analyzer.compute_structural_drift()

    # Real behavioral assertions on the diff content.
    # fn.gamma was removed, fn.delta was added, fn.alpha/fn.beta unchanged.
    assert set(result["nodes_added"]) == {"fn.delta"}
    assert set(result["nodes_removed"]) == {"fn.gamma"}
    assert result["nodes_added_count"] == 1
    assert result["nodes_removed_count"] == 1
    assert result["nodes_changed_count"] == 0

    # Edge e2 (beta→gamma) removed, e3 (beta→delta) added; e1 unchanged.
    assert result["edges_added_count"] == 1
    assert result["edges_removed_count"] == 1


def test_compute_drift_score_end_to_end_on_run_dir_bundles(
    tmp_path: Path,
) -> None:
    """Full drift pipeline must succeed for dict-shaped run-dir bundles.

    Covers the public ``analyze`` entry point, which exercises
    structural, semantic, and state-space drift together. This is the
    exact path ``cogant diff`` uses in production.
    """
    run_a = tmp_path / "run_a"
    run_b = tmp_path / "run_b"
    run_a.mkdir()
    run_b.mkdir()

    (run_a / "program_graph.json").write_text(json.dumps(_dict_shape_graph()))
    (run_b / "program_graph.json").write_text(json.dumps(_dict_shape_graph_modified()))

    bundle_a = load_bundle(run_a)
    bundle_b = load_bundle(run_b)

    analyzer = DriftAnalyzer({}, {})
    score = analyzer.analyze(bundle_a, bundle_b)

    # Structural drift shows the add/remove we seeded. This is the
    # load-bearing diff signal — the coarse ``architectural_score``
    # is count-based and intentionally insensitive to identity swaps
    # at equal cardinality.
    struct = score.details["structural_drift"]
    assert struct["nodes_added_count"] == 1
    assert struct["nodes_removed_count"] == 1
    assert set(struct["nodes_added"]) == {"fn.delta"}
    assert set(struct["nodes_removed"]) == {"fn.gamma"}
    assert struct["edges_added_count"] == 1
    assert struct["edges_removed_count"] == 1

    # Overall score is bounded.
    assert 0.0 <= score.total_score <= 1.0
