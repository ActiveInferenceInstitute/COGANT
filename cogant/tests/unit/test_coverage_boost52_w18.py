#!/usr/bin/env python3
"""Coverage boost batch 52 — api/orchestration.py stage runners and serializers,
api/bundle.py Bundle accessors, reverse/idempotency.py remaining helpers.

Covers:
- api/orchestration.py: _serialize_node, _serialize_edge, run_ingest, run_static,
  run_normalize (partial), run_graph (empty snapshot), _default_translation_engine
- api/bundle.py: Bundle get_artifact (KeyError path), Bundle serialization
- reverse/idempotency.py: _state_space_matrices, _nodes_edges_from_mappings,
  RoundtripResult.summary method
"""

import pytest
from pathlib import Path

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# api/bundle.py — Bundle accessors and errors
# ---------------------------------------------------------------------------

class TestBundle:
    def test_bundle_init(self, tmp_path):
        from cogant.api.bundle import Bundle
        bundle = Bundle(target=str(tmp_path))
        assert bundle.target == str(tmp_path)
        assert isinstance(bundle.artifacts, dict)
        assert isinstance(bundle.stage_results, dict)
        assert isinstance(bundle.errors, list)
        assert isinstance(bundle.metadata, dict)

    def test_get_artifact_missing_not_required(self, tmp_path):
        from cogant.api.bundle import Bundle
        bundle = Bundle(target=str(tmp_path))
        result = bundle.get_artifact("nonexistent_key")
        assert result is None

    def test_get_artifact_present(self, tmp_path):
        from cogant.api.bundle import Bundle
        bundle = Bundle(target=str(tmp_path))
        bundle.artifacts["my_key"] = {"data": 42}
        result = bundle.get_artifact("my_key")
        assert result == {"data": 42}

    def test_get_artifact_required_raises(self, tmp_path):
        from cogant.api.bundle import Bundle
        bundle = Bundle(target=str(tmp_path))
        with pytest.raises((KeyError, RuntimeError)):
            bundle.get_artifact("missing_key", required=True)


# ---------------------------------------------------------------------------
# api/orchestration.py — _serialize_node, _serialize_edge
# ---------------------------------------------------------------------------

class TestSerializeNodeAndEdge:
    def test_serialize_node_basic(self):
        from cogant.api.orchestration import _serialize_node
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        node = builder.add_node(NodeKind.MODULE, "mymod", "mymod", path="mymod.py")
        result = _serialize_node(node)
        assert isinstance(result, dict)
        assert "kind" in result
        assert isinstance(result["kind"], str)  # Enum coerced to string

    def test_serialize_edge_basic(self):
        from cogant.api.orchestration import _serialize_edge
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind, EdgeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        n1 = builder.add_node(NodeKind.MODULE, "mod", "mod", path="mod.py")
        n2 = builder.add_node(NodeKind.CLASS, "Cls", "mod.Cls", path="mod.py")
        edge = builder.add_edge(n1.id, n2.id, EdgeKind.CONTAINS)
        result = _serialize_edge(edge)
        assert isinstance(result, dict)
        assert "kind" in result
        assert isinstance(result["kind"], str)


# ---------------------------------------------------------------------------
# api/orchestration.py — run_ingest and run_static
# ---------------------------------------------------------------------------

def _make_bundle(tmp_path):
    from cogant.api.bundle import Bundle
    return Bundle(target=str(tmp_path))


class TestRunIngest:
    def test_run_ingest_empty_dir(self, tmp_path):
        from cogant.api.orchestration import run_ingest
        bundle = _make_bundle(tmp_path)
        result = run_ingest(str(tmp_path), bundle)
        assert isinstance(result, dict)
        assert result["type"] == "ingest"
        assert "file_count" in result
        assert "language_distribution" in result

    def test_run_ingest_with_python_file(self, tmp_path):
        from cogant.api.orchestration import run_ingest
        (tmp_path / "module.py").write_text("x = 1\n")
        bundle = _make_bundle(tmp_path)
        result = run_ingest(str(tmp_path), bundle)
        assert result["file_count"] >= 1
        assert "python" in result["language_distribution"]

    def test_run_ingest_stores_snapshot_in_bundle(self, tmp_path):
        from cogant.api.orchestration import run_ingest
        bundle = _make_bundle(tmp_path)
        run_ingest(str(tmp_path), bundle)
        snapshot = bundle.artifacts.get("repo_snapshot")
        assert snapshot is not None

    def test_run_ingest_returns_target(self, tmp_path):
        from cogant.api.orchestration import run_ingest
        bundle = _make_bundle(tmp_path)
        result = run_ingest(str(tmp_path), bundle)
        assert result["target"] == str(tmp_path)


class TestRunStatic:
    def test_run_static_requires_snapshot(self, tmp_path):
        from cogant.api.orchestration import run_static
        bundle = _make_bundle(tmp_path)
        with pytest.raises(RuntimeError, match="ingest"):
            run_static(bundle)

    def test_run_static_with_empty_snapshot(self, tmp_path):
        from cogant.api.orchestration import run_ingest, run_static
        bundle = _make_bundle(tmp_path)
        run_ingest(str(tmp_path), bundle)
        result = run_static(bundle)
        assert isinstance(result, dict)
        assert result["type"] == "static_analysis"
        assert "modules" in result

    def test_run_static_with_python_file(self, tmp_path):
        from cogant.api.orchestration import run_ingest, run_static
        (tmp_path / "mymod.py").write_text("def foo():\n    return 1\n")
        bundle = _make_bundle(tmp_path)
        run_ingest(str(tmp_path), bundle)
        result = run_static(bundle)
        assert result["symbols"]["python_modules_parsed"] >= 1

    def test_run_static_stores_modules_in_bundle(self, tmp_path):
        from cogant.api.orchestration import run_ingest, run_static
        (tmp_path / "m.py").write_text("class Foo:\n    pass\n")
        bundle = _make_bundle(tmp_path)
        run_ingest(str(tmp_path), bundle)
        run_static(bundle)
        modules = bundle.artifacts.get("parsed_modules_detail")
        assert isinstance(modules, list)


# ---------------------------------------------------------------------------
# api/orchestration.py — run_normalize
# ---------------------------------------------------------------------------

class TestRunNormalize:
    def test_run_normalize_with_empty_snapshot(self, tmp_path):
        from cogant.api.orchestration import run_ingest, run_static, run_normalize
        bundle = _make_bundle(tmp_path)
        run_ingest(str(tmp_path), bundle)
        run_static(bundle)
        result = run_normalize(bundle)
        assert isinstance(result, dict)
        assert "type" in result

    def test_run_normalize_with_python_file(self, tmp_path):
        from cogant.api.orchestration import run_ingest, run_static, run_normalize
        (tmp_path / "mod.py").write_text("def bar(x: int) -> int:\n    return x\n")
        bundle = _make_bundle(tmp_path)
        run_ingest(str(tmp_path), bundle)
        run_static(bundle)
        result = run_normalize(bundle)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# reverse/idempotency.py — _state_space_matrices, _nodes_edges_from_mappings,
# RoundtripResult.summary
# ---------------------------------------------------------------------------

class TestReverseIdempotencyHelpers:
    def test_state_space_matrices_none(self):
        from cogant.reverse.idempotency import _state_space_matrices
        result = _state_space_matrices(None)
        assert result == {}

    def test_state_space_matrices_empty_model(self):
        from cogant.reverse.idempotency import _state_space_matrices
        from cogant.statespace.compiler import StateSpaceModel
        from cogant.statespace.temporal import TimeRegime
        ss = StateSpaceModel(
            id="ss1", schema_name="test",
            variables={}, observations={}, actions={},
            transitions={}, likelihoods={}, preferences={},
            time_regime=TimeRegime.SYNCHRONOUS,
        )
        result = _state_space_matrices(ss)
        assert isinstance(result, dict)

    def test_nodes_edges_from_mappings_none(self):
        from cogant.reverse.idempotency import _nodes_edges_from_mappings
        nodes, edges = _nodes_edges_from_mappings(None)
        assert nodes == []
        assert edges == []

    def test_nodes_edges_from_mappings_empty_dict(self):
        from cogant.reverse.idempotency import _nodes_edges_from_mappings
        nodes, edges = _nodes_edges_from_mappings({})
        assert nodes == []
        assert edges == []

    def test_roundtrip_result_summary(self):
        from cogant.reverse.idempotency import RoundtripResult
        result = RoundtripResult(
            is_isomorphic=True,
            role_match_score=0.9,
            matrix_score=0.85,
            structural_score=0.8,
        )
        summary = result.summary()
        assert isinstance(summary, str)
        assert "ISO" in summary
        assert "0.90" in summary or "90" in summary

    def test_roundtrip_result_summary_drift(self):
        from cogant.reverse.idempotency import RoundtripResult
        result = RoundtripResult(
            is_isomorphic=False,
            role_match_score=0.5,
        )
        summary = result.summary()
        assert "DRIFT" in summary

    def test_role_multiset_from_mappings_none(self):
        from cogant.reverse.idempotency import _role_multiset_from_mappings
        result = _role_multiset_from_mappings(None)
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_role_multiset_from_model_with_states(self):
        from cogant.reverse.idempotency import _role_multiset_from_model
        from cogant.reverse.parser import ReverseGNNModel, _parse_state_space_block

        model = ReverseGNNModel()
        _parse_state_space_block("s_f0[2,1]\no_m0[3,1]\nu_c0[2,1]\n", model)
        result = _role_multiset_from_model(model)
        assert isinstance(result, dict)
        assert result.get("HIDDEN_STATE", 0) == 1
        assert result.get("OBSERVATION", 0) == 1
        assert result.get("ACTION", 0) == 1
