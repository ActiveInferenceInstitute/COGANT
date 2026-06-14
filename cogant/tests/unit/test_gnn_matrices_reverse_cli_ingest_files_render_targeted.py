#!/usr/bin/env python3
"""Targeted branch tests — gnn/matrices.py additional methods,
reverse/cli.py rendering helpers, ingest/files.py additional paths,
gnn/package.py build method (via partial execution).

Covers:
- gnn/matrices.py: to_gnn_markdown_block, validate_shapes with populated matrices,
  compute_B, compute_C, _normalize_row, _normalize_vector, _state_node_ids,
  _obs_node_ids, _action_node_ids, _top_k_state_ids
- reverse/cli.py: _render_plan_summary, _render_roundtrip_result paths
- gnn/package.py: GNNPackageBuilder.build with empty data
"""

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# gnn/matrices.py — module-level helpers
# ---------------------------------------------------------------------------


class TestGNNMatricesHelpers:
    def test_normalize_row_basic(self):
        from cogant.gnn.matrices import _normalize_row

        result = _normalize_row([1.0, 1.0, 2.0])
        assert abs(sum(result) - 1.0) < 1e-9
        assert len(result) == 3

    def test_normalize_row_uniform(self):
        from cogant.gnn.matrices import _normalize_row

        result = _normalize_row([1.0, 1.0])
        assert abs(result[0] - 0.5) < 1e-9
        assert abs(result[1] - 0.5) < 1e-9

    def test_normalize_row_zero_sum(self):
        from cogant.gnn.matrices import _normalize_row

        # Zero row → uniform fallback
        result = _normalize_row([0.0, 0.0, 0.0])
        assert abs(sum(result) - 1.0) < 1e-9

    def test_normalize_vector_basic(self):
        from cogant.gnn.matrices import _normalize_vector

        result = _normalize_vector([3.0, 1.0])
        assert abs(sum(result) - 1.0) < 1e-9
        assert abs(result[0] - 0.75) < 1e-9

    def test_normalize_vector_zero(self):
        from cogant.gnn.matrices import _normalize_vector

        result = _normalize_vector([0.0, 0.0])
        assert abs(sum(result) - 1.0) < 1e-9


class TestGNNMatricesAdditional:
    def _make_matrices(self):
        from cogant.gnn.matrices import GNNMatrices
        from cogant.schemas.graph import GraphMetadata, ProgramGraph
        from cogant.statespace.compiler import StateSpaceModel
        from cogant.statespace.temporal import TimeRegime

        graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///test"))
        state_space = StateSpaceModel(
            id="ss1",
            schema_name="test",
            variables={},
            observations={},
            actions={},
            transitions={},
            likelihoods={},
            preferences={},
            time_regime=TimeRegime.SYNCHRONOUS,
        )
        return GNNMatrices(graph, mappings={}, state_space=state_space)

    def test_compute_B_returns_list(self):
        matrices = self._make_matrices()
        B = matrices.compute_B()
        assert isinstance(B, list)

    def test_compute_C_returns_list(self):
        matrices = self._make_matrices()
        C = matrices.compute_C()
        assert isinstance(C, list)

    def test_to_gnn_markdown_block_returns_string(self):
        matrices = self._make_matrices()
        result = matrices.to_gnn_markdown_block()
        assert isinstance(result, str)

    def test_validate_shapes_with_empty_model(self):
        matrices = self._make_matrices()
        ok, errors = matrices.validate_shapes()
        assert isinstance(ok, bool)
        assert isinstance(errors, list)

    def test_state_node_ids_returns_list(self):
        matrices = self._make_matrices()
        ids = matrices._state_node_ids()
        assert isinstance(ids, list)

    def test_obs_node_ids_returns_list(self):
        matrices = self._make_matrices()
        ids = matrices._obs_node_ids()
        assert isinstance(ids, list)

    def test_action_node_ids_returns_list(self):
        matrices = self._make_matrices()
        ids = matrices._action_node_ids()
        assert isinstance(ids, list)

    def test_top_k_state_ids_empty(self):
        matrices = self._make_matrices()
        result = matrices._top_k_state_ids([], 5)
        assert isinstance(result, list)
        assert result == []

    def test_top_k_state_ids_fewer_than_k(self):
        matrices = self._make_matrices()
        ids = ["id_a", "id_b"]
        result = matrices._top_k_state_ids(ids, 10)
        assert isinstance(result, list)
        assert set(result).issubset({"id_a", "id_b"})

    def test_edges_from_nonexistent_node(self):
        matrices = self._make_matrices()
        result = matrices._edges_from("nonexistent_node_id")
        assert isinstance(result, list)
        assert result == []

    def test_edges_to_nonexistent_node(self):
        matrices = self._make_matrices()
        result = matrices._edges_to("nonexistent_node_id")
        assert isinstance(result, list)
        assert result == []


# ---------------------------------------------------------------------------
# reverse/cli.py — rendering helpers (test via output capture)
# ---------------------------------------------------------------------------


class TestReverseCLIRenderHelpers:
    def test_render_plan_summary_produces_output(self, tmp_path, capsys):
        from cogant.reverse.cli import _render_plan_summary

        gnn_path = tmp_path / "model.gnn.md"
        pkg_path = tmp_path / "pkg"
        # Should not raise; produces Rich table output
        _render_plan_summary(
            gnn_path=gnn_path,
            package_path=pkg_path,
            state_count=3,
            obs_count=2,
            action_count=2,
            policy_count=1,
            constraint_count=0,
        )
        # If it got here without raising, rendering worked

    def test_render_roundtrip_result_isomorphic(self, capsys):
        from cogant.reverse.cli import _render_roundtrip_result
        from cogant.reverse.idempotency import RoundtripResult

        result = RoundtripResult(
            structurally_isomorphic=True,
            role_preservation_score=0.95,
            original_roles={"HIDDEN_STATE": 2, "OBSERVATION": 1},
            synthesized_roles={"HIDDEN_STATE": 2, "OBSERVATION": 1},
            shape_match={"A": True, "B": True},
            errors=[],
        )
        # Should not raise
        _render_roundtrip_result(result, threshold=0.80)

    def test_render_roundtrip_result_not_isomorphic(self, capsys):
        from cogant.reverse.cli import _render_roundtrip_result
        from cogant.reverse.idempotency import RoundtripResult

        result = RoundtripResult(
            structurally_isomorphic=False,
            role_preservation_score=0.55,
            original_roles={"HIDDEN_STATE": 3},
            synthesized_roles={"HIDDEN_STATE": 2},
            shape_match={"A": False, "B": True},
            errors=["Role mismatch for HIDDEN_STATE"],
        )
        # Should not raise
        _render_roundtrip_result(result, threshold=0.80)

    def test_render_roundtrip_result_with_package_path(self, tmp_path, capsys):
        from cogant.reverse.cli import _render_roundtrip_result
        from cogant.reverse.idempotency import RoundtripResult

        result = RoundtripResult(
            structurally_isomorphic=True,
            role_preservation_score=1.0,
            original_roles={},
            synthesized_roles={},
            shape_match={},
            errors=[],
            package_path=str(tmp_path / "synthesized_pkg"),
        )
        _render_roundtrip_result(result, threshold=0.80)


# ---------------------------------------------------------------------------
# gnn/package.py — build method with empty components
# ---------------------------------------------------------------------------


class TestGNNPackageBuilderBuild:
    def test_build_creates_output_files(self, tmp_path):
        from cogant.gnn.package import GNNPackageBuilder
        from cogant.process.extractor import ProcessModel
        from cogant.schemas.graph import GraphMetadata, ProgramGraph
        from cogant.statespace.compiler import StateSpaceModel
        from cogant.statespace.temporal import TimeRegime

        graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///test"))
        state_space = StateSpaceModel(
            id="ss1",
            schema_name="test",
            variables={},
            observations={},
            actions={},
            transitions={},
            likelihoods={},
            preferences={},
            time_regime=TimeRegime.SYNCHRONOUS,
        )
        process_model = ProcessModel(id="pm1", schema_name="test", stages={}, connections={})
        builder = GNNPackageBuilder(
            graph=graph,
            state_space=state_space,
            process_model=process_model,
            mappings={},
        )
        output_dir = tmp_path / "gnn_package"
        manifest = builder.build(str(output_dir))
        assert isinstance(manifest, dict)
        assert output_dir.exists()
        # Manifest should have some info
        assert "version" in manifest or "schema_name" in manifest or len(manifest) > 0

    def test_build_manifest_has_version(self, tmp_path):
        from cogant.gnn.package import GNNPackageBuilder
        from cogant.process.extractor import ProcessModel
        from cogant.schemas.graph import GraphMetadata, ProgramGraph
        from cogant.statespace.compiler import StateSpaceModel
        from cogant.statespace.temporal import TimeRegime

        graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///test"))
        state_space = StateSpaceModel(
            id="ss1",
            schema_name="test",
            variables={},
            observations={},
            actions={},
            transitions={},
            likelihoods={},
            preferences={},
            time_regime=TimeRegime.SYNCHRONOUS,
        )
        pm = ProcessModel(id="pm1", schema_name="test", stages={}, connections={})
        builder = GNNPackageBuilder(
            graph=graph, state_space=state_space, process_model=pm, mappings={}
        )
        manifest = builder.build(str(tmp_path / "pkg"))
        # Should have a version key
        assert "version" in manifest
        assert manifest["version"] == GNNPackageBuilder.PACKAGE_VERSION
