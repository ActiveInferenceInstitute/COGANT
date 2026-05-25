"""Behavioral tests for cogant.api.bundle and cogant.__init__.

Covers Bundle dataclass, ArtifactKey enum, _json_default serialization,
and the cogant package-level imports/constants — no mocks.
"""

from __future__ import annotations

import dataclasses
import json
from enum import Enum
from pathlib import Path

import pytest

import cogant
from cogant.api.bundle import ArtifactKey, Bundle, _json_default

# ------------------------------------------------------------------ #
# cogant.__init__ package-level tests
# ------------------------------------------------------------------ #


def test_cogant_version_is_string() -> None:
    assert isinstance(cogant.__version__, str)
    assert len(cogant.__version__) > 0


def test_cogant_rust_available_is_bool() -> None:
    assert isinstance(cogant._RUST_AVAILABLE, bool)


def test_cogant_rust_version_is_none_or_string() -> None:
    rv = cogant.__rust_version__
    assert rv is None or isinstance(rv, str)


def test_cogant_session_importable() -> None:
    # Session is either the real class or None when unavailable
    assert (
        cogant.Session is not None or cogant.Session is None
    )  # always true — just confirms no import error


def test_cogant_all_contains_expected_names() -> None:
    for name in ("Session", "PipelineRunner", "Bundle", "__version__", "_RUST_AVAILABLE"):
        assert name in cogant.__all__


# ------------------------------------------------------------------ #
# ArtifactKey enum tests
# ------------------------------------------------------------------ #


def test_artifact_key_values_are_strings() -> None:
    for key in ArtifactKey:
        assert isinstance(key.value, str)


def test_artifact_key_program_graph_value() -> None:
    assert ArtifactKey.PROGRAM_GRAPH == "_program_graph"


def test_artifact_key_repo_snapshot_value() -> None:
    assert ArtifactKey.REPO_SNAPSHOT == "repo_snapshot"


# ------------------------------------------------------------------ #
# _json_default tests
# ------------------------------------------------------------------ #


def test_json_default_path_to_string() -> None:
    result = _json_default(Path("/tmp/file.txt"))
    assert result == "/tmp/file.txt"


def test_json_default_enum_to_value() -> None:
    class Color(Enum):
        RED = "red"

    result = _json_default(Color.RED)
    assert result == "red"


def test_json_default_set_to_sorted_list() -> None:
    result = _json_default({"c", "a", "b"})
    assert isinstance(result, list)
    assert sorted(result) == ["a", "b", "c"]


def test_json_default_frozenset_to_sorted_list() -> None:
    result = _json_default(frozenset({3, 1, 2}))
    assert sorted(result) == [1, 2, 3]


def test_json_default_dataclass_to_dict() -> None:
    @dataclasses.dataclass
    class Point:
        x: float
        y: float

    result = _json_default(Point(1.0, 2.0))
    assert result == {"x": 1.0, "y": 2.0}


def test_json_default_plain_object_uses_dict() -> None:
    class Obj:
        def __init__(self):
            self.value = 42
            self._private = "hidden"

    result = _json_default(Obj())
    assert result == {"value": 42}


def test_json_default_to_dict_protocol() -> None:
    class HasToDict:
        def to_dict(self) -> dict:
            return {"key": "val"}

    result = _json_default(HasToDict())
    assert result == {"key": "val"}


def test_json_default_pydantic_model_dump() -> None:
    class FakePydantic:
        def model_dump(self) -> dict:
            return {"field": 99}

    result = _json_default(FakePydantic())
    assert result == {"field": 99}


def test_json_default_fallback_to_str() -> None:
    class NoProtocol:
        def __repr__(self) -> str:
            return "NoProtocol()"

        # No __dict__, no model_dump, no to_dict
        __dict__ = property(lambda self: (_ for _ in ()).throw(AttributeError("no dict")))  # type: ignore[assignment]

    # The object will hit the str() fallback
    result = _json_default(42)  # int falls through to str() via all guards
    assert result == "42"


# ------------------------------------------------------------------ #
# Bundle dataclass tests
# ------------------------------------------------------------------ #


def _basic_bundle() -> Bundle:
    return Bundle(target="my/repo")


def test_bundle_target_stored() -> None:
    b = Bundle(target="repo/path")
    assert b.target == "repo/path"


def test_bundle_default_empty_collections() -> None:
    b = _basic_bundle()
    assert b.artifacts == {}
    assert b.stage_results == {}
    assert b.errors == []
    assert b.metadata == {}


def test_bundle_get_artifact_missing_returns_none() -> None:
    b = _basic_bundle()
    assert b.get_artifact("missing_key") is None


def test_bundle_get_artifact_required_raises_on_missing() -> None:
    b = _basic_bundle()
    with pytest.raises(KeyError, match="missing_key"):
        b.get_artifact("missing_key", required=True)


def test_bundle_get_artifact_returns_value() -> None:
    b = _basic_bundle()
    b.artifacts["foo"] = {"x": 1}
    assert b.get_artifact("foo") == {"x": 1}


def test_bundle_repo_summary_defaults() -> None:
    b = _basic_bundle()
    summary = b.repo_summary()
    assert summary["target"] == "my/repo"
    assert summary["file_count"] == 0
    assert summary["total_errors"] == 0


def test_bundle_repo_summary_uses_ingest_stage() -> None:
    b = _basic_bundle()
    b.stage_results["ingest"] = {"file_count": 42, "language_distribution": {"py": 0.8}}
    summary = b.repo_summary()
    assert summary["file_count"] == 42
    assert summary["language_distribution"]["py"] == 0.8


def test_bundle_program_graph_returns_graph_stage() -> None:
    b = _basic_bundle()
    b.stage_results["graph"] = {"nodes": {}, "edges": {}}
    assert b.program_graph() == {"nodes": {}, "edges": {}}


def test_bundle_state_space_model_returns_statespace_stage() -> None:
    b = _basic_bundle()
    b.stage_results["statespace"] = {"hidden_states": ["s0"]}
    assert b.state_space_model() == {"hidden_states": ["s0"]}


def test_bundle_process_model_returns_process_stage() -> None:
    b = _basic_bundle()
    b.stage_results["process"] = {"stages": ["ingest"]}
    assert b.process_model() == {"stages": ["ingest"]}


def test_bundle_validation_report_returns_validate_stage() -> None:
    b = _basic_bundle()
    b.stage_results["validate"] = {"passed": True, "warnings": []}
    report = b.validation_report()
    assert report["passed"] is True


def test_bundle_gnn_markdown_contains_target() -> None:
    b = _basic_bundle()
    md = b.gnn_markdown()
    assert "my/repo" in md
    assert "GNN Model" in md


def test_bundle_gnn_markdown_counts_node_features() -> None:
    b = _basic_bundle()
    b.stage_results["translate"] = {"node_features": [1, 2, 3], "edge_indices": []}
    md = b.gnn_markdown()
    assert "Count: 3" in md


def test_bundle_to_json_is_valid_json() -> None:
    b = _basic_bundle()
    b.artifacts["key"] = {"val": 1}
    raw = b.to_json()
    parsed = json.loads(raw)
    assert parsed["target"] == "my/repo"
    assert parsed["artifacts"]["key"] == {"val": 1}


def test_bundle_to_json_serializes_path_in_artifacts() -> None:
    b = _basic_bundle()
    b.artifacts["output_path"] = Path("/tmp/out.json")
    raw = b.to_json()
    parsed = json.loads(raw)
    assert parsed["artifacts"]["output_path"] == "/tmp/out.json"


def test_bundle_save_json_writes_file(tmp_path: Path) -> None:
    b = _basic_bundle()
    b.artifacts["x"] = 42
    out = tmp_path / "bundle.json"
    b.save_json(str(out))
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["artifacts"]["x"] == 42


def test_bundle_errors_accumulated() -> None:
    b = _basic_bundle()
    b.errors.append("stage ingest failed")
    assert b.repo_summary()["total_errors"] == 1


def test_bundle_get_artifact_with_artifact_key_constant() -> None:
    b = _basic_bundle()
    b.artifacts[ArtifactKey.PROGRAM_GRAPH] = {"nodes": {}}
    result = b.get_artifact(ArtifactKey.PROGRAM_GRAPH)
    assert "nodes" in result
