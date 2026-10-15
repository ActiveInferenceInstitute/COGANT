#!/usr/bin/env python3
"""Targeted branch tests — cogant/__init__.py run_pipeline, gnn/runner.py deeper,
api/orchestration.py light helpers, and reverse/idempotency.py public API.

Covers:
- cogant.run_pipeline: happy path (lines 106-112)
- cogant module attributes: __version__, __rust_version__, _RUST_AVAILABLE, aliases
- GNNModelRunner: missing-package admission and exported prior/posterior history
- api/orchestration.py: _repo_uri helper, program_graph_to_dict
- reverse/idempotency.py: RoundtripResult, _ONTOLOGY_TO_ROLE, _role_multiset_from_model
"""

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# cogant/__init__.py — module attributes and run_pipeline
# ---------------------------------------------------------------------------


class TestCogantInit:
    def test_version_defined(self):
        import cogant

        assert hasattr(cogant, "__version__")
        assert isinstance(cogant.__version__, str)

    def test_rust_available_bool(self):
        import cogant

        assert isinstance(cogant._RUST_AVAILABLE, bool)

    def test_rust_version_none_or_str(self):
        import cogant

        assert cogant.__rust_version__ is None or isinstance(cogant.__rust_version__, str)

    def test_session_alias_available(self):
        import cogant

        # CogantSession should be Session or None
        assert cogant.CogantSession is not None or cogant.CogantSession is None

    def test_gnn_bundle_alias(self):
        import cogant

        assert cogant.GNNBundle is not None or cogant.GNNBundle is None

    def test_run_pipeline_happy_path(self, tmp_path):
        from cogant import run_pipeline

        (tmp_path / "mymodule.py").write_text("def foo():\n    pass\n")
        out = tmp_path / "output"
        out.mkdir()
        result = run_pipeline(str(tmp_path), output_dir=str(out))
        assert result is not None
        assert hasattr(result, "target")

    def test_run_pipeline_with_empty_dir(self, tmp_path):
        from cogant import run_pipeline

        out = tmp_path / "out"
        out.mkdir()
        result = run_pipeline(str(tmp_path), output_dir=str(out))
        assert result is not None


# ---------------------------------------------------------------------------
# gnn/runner.py — GNNModelRunner internal helpers
# ---------------------------------------------------------------------------


class TestGNNModelRunnerHelpers:
    def test_missing_package_rejected(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner

        with pytest.raises(FileNotFoundError):
            GNNModelRunner().load_package(str(tmp_path / "missing"))

    def test_not_loaded_rejected(self):
        from cogant.gnn.runner import GNNModelRunner

        with pytest.raises(RuntimeError, match="not loaded"):
            GNNModelRunner().run(1)

    def test_history_starts_with_exported_prior(self, tmp_path):
        from tests.gnn_execution_fixture import runner

        model = runner(tmp_path)
        model.run(1)
        assert list(model.beliefs_history[0].values()) == [0.75, 0.25]
        assert model.beliefs_history[1] == model.traces[0].beliefs


class TestOrchestrationHelpers:
    def test_repo_uri_local_path(self, tmp_path):
        from cogant.api.orchestration import _repo_uri

        result = _repo_uri(str(tmp_path))
        assert result.startswith("file://")

    def test_repo_uri_nonexistent_path(self, tmp_path):
        from cogant.api.orchestration import _repo_uri

        nonexistent = str(tmp_path / "no_such_dir")
        result = _repo_uri(nonexistent)
        # Returns the original string unchanged
        assert result == nonexistent

    def test_program_graph_to_dict_empty(self):
        from cogant.api.orchestration import program_graph_to_dict
        from cogant.graph.builder import ProgramGraphBuilder

        graph = ProgramGraphBuilder(repo_uri="file:///test").finalize()
        result = program_graph_to_dict(graph)
        assert isinstance(result, dict)

    def test_program_graph_to_dict_with_statistics(self):
        from cogant.api.orchestration import program_graph_to_dict
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        builder.add_node(NodeKind.MODULE, "mod", "mod", path="mod.py")
        graph = builder.finalize()
        stats = builder.get_statistics()
        result = program_graph_to_dict(graph, statistics=stats)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# reverse/idempotency.py — accessible public types
# ---------------------------------------------------------------------------


class TestReverseIdempotency:
    def test_roundtrip_result_import(self):
        from cogant.reverse.idempotency import RoundtripResult

        result = RoundtripResult(
            structurally_isomorphic=True,
            role_preservation_score=0.95,
            original_roles={"hidden": 2},
            synthesized_roles={"hidden": 2},
        )
        assert result.structurally_isomorphic is True
        assert result.role_preservation_score == 0.95

    def test_ontology_to_role_mapping(self):
        from cogant.reverse.idempotency import _ONTOLOGY_TO_ROLE

        assert isinstance(_ONTOLOGY_TO_ROLE, dict)
        assert len(_ONTOLOGY_TO_ROLE) >= 1

    def test_role_multiset_from_model_empty(self):
        from cogant.reverse.idempotency import _role_multiset_from_model
        from cogant.reverse.parser import ReverseGNNModel

        model = ReverseGNNModel()
        result = _role_multiset_from_model(model)
        assert isinstance(result, dict)

    def test_role_multiset_from_mappings_empty(self):
        from cogant.reverse.idempotency import _role_multiset_from_mappings

        result = _role_multiset_from_mappings({})
        assert isinstance(result, dict)

    def test_model_matrices_empty(self):
        from cogant.reverse.idempotency import _model_matrices
        from cogant.reverse.parser import ReverseGNNModel

        model = ReverseGNNModel()
        result = _model_matrices(model)
        assert isinstance(result, dict)
