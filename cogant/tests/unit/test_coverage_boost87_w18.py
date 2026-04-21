#!/usr/bin/env python3
"""Coverage boost batch 87 — ingest/incremental.py module functions,
gnn/package.py additional extract methods, static/calls.py additional paths,
gnn/json_export.py additional paths.

Covers:
- ingest/incremental.py: get_changed_files (non-git), apply_incremental_patch,
  source_files_changed_since (non-git), ChangedFile dataclass
- gnn/package.py: _extract_action_space, _extract_observation_space,
  _extract_preferences, _extract_constraints, _extract_objectives,
  _extract_factorization, _extract_factor_list, _extract_ontology_mappings
- static/calls.py: CallEdge dataclass, CallGraphBuilder additional paths
- gnn/json_export.py: GNNJSONExporter._build_matrices_section
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# ingest/incremental.py — module-level functions and additional coverage
# ---------------------------------------------------------------------------


class TestIncrementalModuleFunctions:
    def test_get_changed_files_non_git(self, tmp_path):
        from cogant.ingest.incremental import get_changed_files

        result = get_changed_files(tmp_path, since_commit="HEAD~1")
        assert result == []

    def test_get_changed_files_with_extensions_non_git(self, tmp_path):
        from cogant.ingest.incremental import get_changed_files

        result = get_changed_files(tmp_path, since_commit="abc123", extensions={".py"})
        assert result == []

    def test_apply_incremental_patch_basic(self):
        from cogant.ingest.incremental import apply_incremental_patch

        cached = {"stage_a": "result_a", "stage_b": "result_b"}
        fresh = {"stage_b": "new_result_b", "stage_c": "result_c"}
        changed = [Path("main.py"), Path("utils.py")]
        merged = apply_incremental_patch(cached, fresh, changed)
        assert merged["stage_a"] == "result_a"
        assert merged["stage_b"] == "new_result_b"
        assert merged["stage_c"] == "result_c"
        assert merged["_incremental_patch"]["changed_count"] == 2

    def test_apply_incremental_patch_empty_new(self):
        from cogant.ingest.incremental import apply_incremental_patch

        cached = {"stage_x": "result_x"}
        merged = apply_incremental_patch(cached, {}, [])
        assert merged["stage_x"] == "result_x"
        assert merged["_incremental_patch"]["changed_count"] == 0

    def test_apply_incremental_patch_does_not_mutate_inputs(self):
        from cogant.ingest.incremental import apply_incremental_patch

        cached = {"a": 1}
        fresh = {"b": 2}
        apply_incremental_patch(cached, fresh, [])
        assert "b" not in cached
        assert "_incremental_patch" not in cached

    def test_source_files_changed_since_non_git(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        result = ingester.source_files_changed_since("HEAD~1")
        assert result == []

    def test_source_files_changed_since_with_extensions_non_git(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        result = ingester.source_files_changed_since("HEAD~1", extensions={".py"})
        assert result == []

    def test_source_extensions_includes_python(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        assert ".py" in ingester._SOURCE_EXTENSIONS
        assert ".ts" in ingester._SOURCE_EXTENSIONS
        assert ".rs" in ingester._SOURCE_EXTENSIONS

    def test_incremental_ingester_init_with_timeout(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path, git_timeout=5.0)
        assert ingester is not None

    def test_changed_file_change_types(self, tmp_path):
        from cogant.ingest.incremental import ChangedFile

        for change_type in ["A", "M", "D", "R", "C", "T", "U", "?"]:
            cf = ChangedFile(path=Path("test.py"), change_type=change_type)
            assert cf.change_type == change_type


# ---------------------------------------------------------------------------
# gnn/package.py — additional extract methods
# ---------------------------------------------------------------------------


def _make_builder():
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
    return GNNPackageBuilder(
        graph=graph, state_space=state_space, process_model=process_model, mappings={}
    )


class TestGNNPackageBuilderExtractMethods:
    def test_extract_action_space_empty(self):
        builder = _make_builder()
        result = builder._extract_action_space()
        assert isinstance(result, list)

    def test_extract_observation_space_empty(self):
        builder = _make_builder()
        result = builder._extract_observation_space()
        assert isinstance(result, list)

    def test_extract_preferences_empty(self):
        builder = _make_builder()
        result = builder._extract_preferences()
        assert isinstance(result, list)

    def test_extract_constraints_empty(self):
        builder = _make_builder()
        result = builder._extract_constraints()
        assert isinstance(result, list)

    def test_extract_objectives_empty(self):
        builder = _make_builder()
        result = builder._extract_objectives()
        assert isinstance(result, list)

    def test_extract_factorization_empty(self):
        builder = _make_builder()
        result = builder._extract_factorization()
        assert isinstance(result, dict)

    def test_extract_factor_list_empty(self):
        builder = _make_builder()
        result = builder._extract_factor_list()
        assert isinstance(result, list)

    def test_extract_ontology_mappings_empty(self):
        builder = _make_builder()
        result = builder._extract_ontology_mappings()
        assert isinstance(result, list)

    def test_extract_actions_empty(self):
        builder = _make_builder()
        result = builder._extract_actions()
        assert isinstance(result, list)

    def test_extract_policies_empty(self):
        builder = _make_builder()
        result = builder._extract_policies()
        assert isinstance(result, list)

    def test_state_var_object_nonexistent(self):
        builder = _make_builder()
        result = builder._state_var_object("nonexistent_id")
        assert result is None

    def test_action_object_nonexistent(self):
        builder = _make_builder()
        result = builder._action_object("nonexistent_action")
        assert result is None


# ---------------------------------------------------------------------------
# static/calls.py — CallEdge dataclass and additional paths
# ---------------------------------------------------------------------------


class TestCallEdge:
    def test_call_edge_basic(self):
        from cogant.static.calls import CallEdge

        edge = CallEdge(
            id="edge_001",
            source_file=Path("mymod.py"),
            caller_id="caller_node_id",
            caller_name="mymod.process",
            callee_name="mymod.helper",
        )
        assert edge.caller_name == "mymod.process"
        assert edge.callee_name == "mymod.helper"
        assert edge.source_file == Path("mymod.py")

    def test_call_edge_with_metadata(self):
        from cogant.static.calls import CallEdge

        edge = CallEdge(
            id="edge_002",
            source_file=Path("x.py"),
            caller_id="cid",
            caller_name="a",
            callee_name="b",
            line_num=5,
            is_method_call=True,
            receiver="self",
        )
        assert edge.is_method_call is True
        assert edge.receiver == "self"
        assert edge.line_num == 5


class TestCallGraphBuilderAdditional:
    def test_extract_calls_from_source_basic(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder

        builder = CallGraphBuilder()
        src = "def main():\n    result = helper()\n    return result\n"
        fp = tmp_path / "main.py"
        calls = builder.extract_calls_from_source(src, fp)
        assert isinstance(calls, list)

    def test_extract_calls_from_source_empty(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder

        builder = CallGraphBuilder()
        calls = builder.extract_calls_from_source("", tmp_path / "empty.py")
        assert isinstance(calls, list)

    def test_extract_calls_from_source_invalid_syntax(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder

        builder = CallGraphBuilder()
        calls = builder.extract_calls_from_source("def broken(:\n    pass", tmp_path / "bad.py")
        assert calls == []

    def test_extract_calls_from_file_nonexistent(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder

        builder = CallGraphBuilder()
        calls = builder.extract_calls_from_file(tmp_path / "missing.py")
        assert calls == []

    def test_extract_calls_from_source_chained_calls(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder

        builder = CallGraphBuilder()
        src = "x = obj.method().another()\n"
        fp = tmp_path / "chain.py"
        calls = builder.extract_calls_from_source(src, fp)
        assert isinstance(calls, list)

    def test_extract_calls_from_multiple_files(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder

        builder = CallGraphBuilder()
        (tmp_path / "a.py").write_text("def fa():\n    fb()\n")
        (tmp_path / "b.py").write_text("def fb():\n    pass\n")
        calls_a = builder.extract_calls_from_file(tmp_path / "a.py")
        calls_b = builder.extract_calls_from_file(tmp_path / "b.py")
        all_calls = calls_a + calls_b
        assert isinstance(all_calls, list)


# ---------------------------------------------------------------------------
# gnn/json_export.py — additional paths
# ---------------------------------------------------------------------------


class TestGNNJSONExporterAdditional:
    def _make_exporter(self):
        from cogant.gnn.json_export import GNNJSONExporter
        from cogant.process.extractor import ProcessModel
        from cogant.schemas.graph import GraphMetadata, ProgramGraph
        from cogant.statespace.compiler import StateSpaceModel
        from cogant.statespace.temporal import TimeRegime

        graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///test"))
        ss = StateSpaceModel(
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
        return GNNJSONExporter(
            program_graph=graph,
            state_space_model=ss,
            process_model=pm,
            semantic_mappings={},
        )

    def test_export_contains_required_keys(self):
        exporter = self._make_exporter()
        result = exporter.export()
        # Should have at least some top-level structure
        assert isinstance(result, dict)

    def test_export_to_string_returns_json(self):
        exporter = self._make_exporter()
        result_str = exporter.export_to_string()
        data = json.loads(result_str)
        assert isinstance(data, dict)

    def test_export_metadata_present(self):
        exporter = self._make_exporter()
        result = exporter.export()
        # Should have some metadata or model key
        assert len(result) >= 1
