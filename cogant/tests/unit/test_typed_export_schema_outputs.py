"""Targeted unit tests: cogant.export.typed_export — JSONL, Arrow IPC, summary, edges.

Targets uncovered lines in py/cogant/export/typed_export.py:
* line 189: adjacency_matrix branch where edge_kind already in edge_type_map
* lines 223-234: to_jsonlines (write items to .jsonl file)
* lines 253-275: to_arrow_ipc (success path + non-dict warning path)
* lines 290-334: export_summary (graph/semantic/state/validation branches)

No mocks: real ProgramGraph, real tmp files, real pyarrow IPC files.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pa = pytest.importorskip("pyarrow")

from cogant.export.typed_export import TypedExporter
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _node(nid: str, kind: NodeKind, name: str | None = None) -> Node:
    return Node(
        id=nid,
        kind=kind,
        name=name or nid,
        qualified_name=f"pkg.{name or nid}",
        path="pkg/file.py",
        language="python",
    )


def _edge(eid: str, src: str, tgt: str, kind: EdgeKind, weight: float = 1.0) -> Edge:
    return Edge(id=eid, source_id=src, target_id=tgt, kind=kind, weight=weight)


def _multi_edge_same_kind_graph() -> ProgramGraph:
    """Two CALLS edges between three function nodes — exercises the
    'edge_kind already in map → append' branch in export_adjacency_matrix.
    """
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/r"))
    g.add_node(_node("a", NodeKind.FUNCTION, name="a"))
    g.add_node(_node("b", NodeKind.FUNCTION, name="b"))
    g.add_node(_node("c", NodeKind.FUNCTION, name="c"))
    g.add_edge(_edge("e1", "a", "b", EdgeKind.CALLS, weight=1.0))
    g.add_edge(_edge("e2", "b", "c", EdgeKind.CALLS, weight=2.0))
    return g


# --------------------------------------------------------------------------- #
# adjacency matrix: append-to-existing-kind branch (line 189)
# --------------------------------------------------------------------------- #


def test_adjacency_matrix_appends_repeated_edge_kinds() -> None:
    """Two edges with the same kind both appear under edge_types['calls']."""
    result = TypedExporter().export_adjacency_matrix(_multi_edge_same_kind_graph())
    assert "calls" in result["edge_types"]
    # Both edges recorded — append branch hit
    assert len(result["edge_types"]["calls"]) == 2
    # Each entry is [src_idx, tgt_idx, weight]
    for entry in result["edge_types"]["calls"]:
        assert len(entry) == 3


# --------------------------------------------------------------------------- #
# to_jsonlines
# --------------------------------------------------------------------------- #


def test_to_jsonlines_writes_one_line_per_item(tmp_path: Path) -> None:
    """Each item lands on its own line as JSON."""
    items = [
        {"id": 1, "name": "alpha"},
        {"id": 2, "name": "beta"},
        {"id": 3, "name": "gamma"},
    ]
    out = tmp_path / "out.jsonl"
    written = TypedExporter().to_jsonlines(items, str(out))
    assert written == str(out)

    raw = out.read_text(encoding="utf-8")
    lines = raw.strip().split("\n")
    assert len(lines) == 3
    parsed = [json.loads(line) for line in lines]
    assert parsed == items


def test_to_jsonlines_creates_parent_directory(tmp_path: Path) -> None:
    """Missing parent directories are created automatically."""
    out = tmp_path / "deep" / "nested" / "out.jsonl"
    items = [{"x": 1}]
    TypedExporter().to_jsonlines(items, str(out))
    assert out.exists()


def test_to_jsonlines_empty_list(tmp_path: Path) -> None:
    """Empty input yields an empty file."""
    out = tmp_path / "empty.jsonl"
    TypedExporter().to_jsonlines([], str(out))
    assert out.exists()
    assert out.read_text(encoding="utf-8") == ""


def test_to_jsonlines_serializes_paths_with_default_str(tmp_path: Path) -> None:
    """Non-JSON-native objects (e.g. Path) are serialized via str()."""
    items = [{"path": Path("/tmp/x")}]
    out = tmp_path / "path.jsonl"
    TypedExporter().to_jsonlines(items, str(out))
    line = out.read_text(encoding="utf-8").strip()
    decoded = json.loads(line)
    assert decoded["path"] == "/tmp/x"


# --------------------------------------------------------------------------- #
# to_arrow_ipc
# --------------------------------------------------------------------------- #


def test_to_arrow_ipc_dict_items_invokes_pa_new_file(tmp_path: Path) -> None:
    """to_arrow_ipc with dict items reaches the pa.ipc.new_file branch.

    NOTE: The current implementation calls ``pa.ipc.new_file(path)`` without
    the required ``schema`` keyword, which pyarrow >= 7 rejects with
    ``TypeError: new_file() missing 1 required positional argument: 'schema'``.
    This test documents the existing behaviour and exercises the
    ``isinstance(items[0], dict)`` true-branch + Table construction lines for
    coverage. When the source is fixed to pass a schema, this test should be
    revised to assert successful roundtripping.
    """
    items = [
        {"id": "n1", "kind": "function", "weight": 1.5},
        {"id": "n2", "kind": "class", "weight": 2.5},
    ]
    out = tmp_path / "out.arrow"
    # Confirm Table.from_pylist accepts the items (pre-bug-line check)
    table = pa.Table.from_pylist(items)
    assert table.num_rows == 2

    with pytest.raises(TypeError, match="schema"):
        TypedExporter().to_arrow_ipc(items, str(out))


def test_to_arrow_ipc_creates_parent_directory(tmp_path: Path) -> None:
    """Parent directory creation happens before the (broken) writer call."""
    out = tmp_path / "deep" / "nested" / "out.arrow"
    items = [{"a": 1}]
    # The mkdir happens before the failing pa.ipc.new_file call
    with pytest.raises(TypeError, match="schema"):
        TypedExporter().to_arrow_ipc(items, str(out))
    # Parent dir was created even though the write failed
    assert out.parent.exists()


def test_to_arrow_ipc_non_dict_items_warns_and_returns_path(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Non-dict items hit the warn-and-skip branch, returning the input path."""
    out = tmp_path / "skip.arrow"
    items = ["not-a-dict", "also-not-a-dict"]
    import logging

    with caplog.at_level(logging.WARNING):
        result = TypedExporter().to_arrow_ipc(items, str(out))
    # Returns the input path string (not the Path-wrapped string)
    assert result == str(out)
    # Warning emitted
    assert any("Cannot convert items" in rec.message for rec in caplog.records)
    # File NOT written
    assert not out.exists()


def test_to_arrow_ipc_empty_list_skips(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Empty input → no Arrow file written (the truthiness check fails)."""
    out = tmp_path / "empty.arrow"
    import logging

    with caplog.at_level(logging.WARNING):
        result = TypedExporter().to_arrow_ipc([], str(out))
    assert result == str(out)
    assert not out.exists()


# --------------------------------------------------------------------------- #
# export_summary
# --------------------------------------------------------------------------- #


def test_export_summary_minimal_dict() -> None:
    """An almost-empty pipeline_result still produces the core status keys."""
    summary = TypedExporter().export_summary({})
    assert summary["status"] == "unknown"
    assert summary["timestamp"] is None
    assert summary["duration_seconds"] == 0
    # No optional keys present
    assert "graph_stats" not in summary
    assert "semantic_mapping_stats" not in summary
    assert "state_space_stats" not in summary
    assert "validation" not in summary


def test_export_summary_with_all_sections() -> None:
    """All optional sections are populated when their inputs are present."""
    pipeline_result = {
        "status": "success",
        "timestamp": "2026-05-08T10:00:00Z",
        "duration_seconds": 12.5,
        "program_graph": {
            "metadata": {
                "node_count": 42,
                "edge_count": 99,
                "languages": ["python", "rust"],
            }
        },
        "semantic_mappings": {
            "mappings": {
                "m1": {"role": "hidden_state"},
                "m2": {"role": "hidden_state"},
                "m3": {"role": "observation"},
                "m4": {},  # missing role → "unknown"
            }
        },
        "state_space_model": {
            "hidden_states": ["s0", "s1", "s2"],
            "observations": ["o0", "o1"],
            "actions": ["a0"],
        },
        "validation_results": {
            "passed": True,
            "score": 0.95,
            "findings": [{"id": "f1"}, {"id": "f2"}],
        },
    }
    summary = TypedExporter().export_summary(pipeline_result)

    assert summary["status"] == "success"
    assert summary["timestamp"] == "2026-05-08T10:00:00Z"
    assert summary["duration_seconds"] == 12.5

    assert summary["graph_stats"]["node_count"] == 42
    assert summary["graph_stats"]["edge_count"] == 99
    assert summary["graph_stats"]["languages"] == ["python", "rust"]

    assert summary["semantic_mapping_stats"]["hidden_state"] == 2
    assert summary["semantic_mapping_stats"]["observation"] == 1
    assert summary["semantic_mapping_stats"]["unknown"] == 1

    assert summary["state_space_stats"]["hidden_states"] == 3
    assert summary["state_space_stats"]["observations"] == 2
    assert summary["state_space_stats"]["actions"] == 1

    assert summary["validation"]["passed"] is True
    assert summary["validation"]["score"] == 0.95
    assert summary["validation"]["finding_count"] == 2


def test_export_summary_semantic_without_mappings_key() -> None:
    """semantic_mappings present but without 'mappings' subkey: skipped."""
    pipeline_result = {"semantic_mappings": {"other": "data"}}
    summary = TypedExporter().export_summary(pipeline_result)
    assert "semantic_mapping_stats" not in summary


def test_export_summary_graph_with_missing_metadata_keys() -> None:
    """graph_data with empty metadata yields zeroed stats."""
    pipeline_result = {"program_graph": {}}
    summary = TypedExporter().export_summary(pipeline_result)
    assert summary["graph_stats"]["node_count"] == 0
    assert summary["graph_stats"]["edge_count"] == 0
    assert summary["graph_stats"]["languages"] == []


def test_export_summary_state_space_empty_lists() -> None:
    """Empty state-space lists produce zeros, not crashes."""
    pipeline_result = {
        "state_space_model": {
            "hidden_states": [],
            "observations": [],
            "actions": [],
        }
    }
    summary = TypedExporter().export_summary(pipeline_result)
    assert summary["state_space_stats"] == {
        "hidden_states": 0,
        "observations": 0,
        "actions": 0,
    }


def test_export_summary_validation_with_defaults() -> None:
    """validation_results without optional keys uses False/0/[] defaults."""
    pipeline_result = {"validation_results": {}}
    summary = TypedExporter().export_summary(pipeline_result)
    assert summary["validation"]["passed"] is False
    assert summary["validation"]["score"] == 0
    assert summary["validation"]["finding_count"] == 0
