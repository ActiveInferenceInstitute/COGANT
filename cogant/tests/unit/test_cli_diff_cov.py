"""Behavioral tests for cogant.cli.diff.

Exercises load_bundle and diff_command helpers using real temporary files.
No mocks — all I/O uses tmp_path with real JSON content.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cogant.cli.diff import load_bundle


# ------------------------------------------------------------------ #
# load_bundle tests
# ------------------------------------------------------------------ #


def test_load_bundle_empty_dir(tmp_path: Path) -> None:
    """load_bundle returns empty dict when directory has no known files."""
    result = load_bundle(tmp_path)
    assert isinstance(result, dict)
    assert result == {}


def test_load_bundle_reads_program_graph(tmp_path: Path) -> None:
    """load_bundle reads program_graph.json into bundle['graph']."""
    graph_data = {"nodes": {"n1": {"id": "n1", "kind": "function"}}, "edges": {}}
    (tmp_path / "program_graph.json").write_text(json.dumps(graph_data))

    result = load_bundle(tmp_path)
    assert "graph" in result
    assert result["graph"]["nodes"]["n1"]["kind"] == "function"


def test_load_bundle_reads_semantic_mappings_dict(tmp_path: Path) -> None:
    """load_bundle reads semantic_mappings.json when it is a dict."""
    mappings_data = {"m1": {"id": "m1", "concept": "state"}}
    (tmp_path / "semantic_mappings.json").write_text(json.dumps(mappings_data))

    result = load_bundle(tmp_path)
    assert "mappings" in result
    assert "m1" in result["mappings"]


def test_load_bundle_reads_semantic_mappings_list(tmp_path: Path) -> None:
    """load_bundle converts list-format semantic_mappings into a dict keyed by id."""
    mappings_data = [{"id": "m1", "concept": "state"}, {"id": "m2", "concept": "obs"}]
    (tmp_path / "semantic_mappings.json").write_text(json.dumps(mappings_data))

    result = load_bundle(tmp_path)
    assert "mappings" in result
    assert "m1" in result["mappings"]
    assert "m2" in result["mappings"]


def test_load_bundle_reads_gnn_state_space(tmp_path: Path) -> None:
    """load_bundle extracts state_space from model.gnn.json when present."""
    gnn_data = {
        "state_space": {"hidden_states": ["s0", "s1"]},
        "other_key": "ignored",
    }
    (tmp_path / "model.gnn.json").write_text(json.dumps(gnn_data))

    result = load_bundle(tmp_path)
    assert "state_space" in result
    assert result["state_space"]["hidden_states"] == ["s0", "s1"]


def test_load_bundle_gnn_without_state_space(tmp_path: Path) -> None:
    """load_bundle handles model.gnn.json that has no 'state_space' key."""
    gnn_data = {"process_model": {"stages": []}}
    (tmp_path / "model.gnn.json").write_text(json.dumps(gnn_data))

    result = load_bundle(tmp_path)
    # state_space key must not appear when the JSON doesn't have it
    assert "state_space" not in result


def test_load_bundle_all_files(tmp_path: Path) -> None:
    """load_bundle populates graph, mappings, and state_space from all files."""
    (tmp_path / "program_graph.json").write_text(json.dumps({"nodes": {}, "edges": {}}))
    (tmp_path / "semantic_mappings.json").write_text(json.dumps({"k": {"id": "k"}}))
    (tmp_path / "model.gnn.json").write_text(
        json.dumps({"state_space": {"hidden_states": []}})
    )

    result = load_bundle(tmp_path)
    assert "graph" in result
    assert "mappings" in result
    assert "state_space" in result


def test_load_bundle_list_mappings_with_no_id(tmp_path: Path) -> None:
    """load_bundle handles list entries that have no 'id' field (key becomes None)."""
    mappings_data = [{"concept": "obs"}]  # no 'id' key
    (tmp_path / "semantic_mappings.json").write_text(json.dumps(mappings_data))

    result = load_bundle(tmp_path)
    assert "mappings" in result
    # None key allowed — dict must have exactly one entry
    assert len(result["mappings"]) == 1


# ------------------------------------------------------------------ #
# diff_command tests (covers lines 63-115)
# ------------------------------------------------------------------ #


def test_diff_command_empty_dirs_returns_string(tmp_path: Path) -> None:
    """diff_command runs end-to-end on two empty output dirs."""
    from cogant.cli.diff import diff_command

    dir_a = tmp_path / "baseline"
    dir_b = tmp_path / "current"
    dir_a.mkdir()
    dir_b.mkdir()

    result = diff_command(str(dir_a), str(dir_b))
    assert isinstance(result, str)
    assert "Codebase Diff Report" in result


def test_diff_command_includes_dir_names(tmp_path: Path) -> None:
    """diff_command report includes names of both directories."""
    from cogant.cli.diff import diff_command

    dir_a = tmp_path / "v1_baseline"
    dir_b = tmp_path / "v2_current"
    dir_a.mkdir()
    dir_b.mkdir()

    result = diff_command(str(dir_a), str(dir_b))
    assert "v1_baseline" in result
    assert "v2_current" in result


def test_diff_command_with_graph_data(tmp_path: Path) -> None:
    """diff_command handles directories that contain program_graph.json files."""
    from cogant.cli.diff import diff_command

    dir_a = tmp_path / "old"
    dir_b = tmp_path / "new"
    dir_a.mkdir()
    dir_b.mkdir()

    # DriftAnalyzer expects graph["nodes"] to be a list (or iterable of node objects)
    graph_a = {"nodes": [{"id": "n1"}], "edges": []}
    graph_b = {"nodes": [{"id": "n1"}, {"id": "n2"}], "edges": []}
    (dir_a / "program_graph.json").write_text(json.dumps(graph_a))
    (dir_b / "program_graph.json").write_text(json.dumps(graph_b))

    result = diff_command(str(dir_a), str(dir_b))
    assert isinstance(result, str)
    assert "Metrics Comparison" in result


def test_diff_command_metrics_sections_present(tmp_path: Path) -> None:
    """diff_command includes both Baseline and Current metrics sections."""
    from cogant.cli.diff import diff_command

    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()

    result = diff_command(str(dir_a), str(dir_b))
    assert "Baseline Metrics" in result
    assert "Current Metrics" in result
