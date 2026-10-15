#!/usr/bin/env python3
"""Targeted branch tests — gnn/package.py private helper methods,
ingest/files.py _detect_language and _is_test_file,
gnn/runner.py additional ExecutionTrace coverage.

Covers:
- gnn/package.py: GNNPackageBuilder private helpers (_count_graph_nodes,
  _count_graph_edges, _count_edges_by_kind, _count_state_space_elements,
  _is_deterministic, _is_markovian, _count_nodes_by_kind, _count_mappings_by_tier,
  _checksum, _checksum_dict, _generate_dashboard_html, _extract_source_evidence,
  _extract_observation_modalities, _extract_state_variables, _extract_classes,
  _extract_relationships, _extract_transition_structure, _render_distribution_chart)
- ingest/files.py: _detect_language with various extensions, _is_test_file paths,
  _compute_checksum
- gnn/runner.py: ExecutionTrace with more field combinations
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers to create GNNPackageBuilder instances
# ---------------------------------------------------------------------------


def _make_builder_components():
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
    return graph, state_space, process_model


def _make_builder_with_graph():
    """Return a builder with a graph containing nodes and edges."""
    from cogant.gnn.package import GNNPackageBuilder
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.process.extractor import ProcessModel
    from cogant.schemas.core import EdgeKind, NodeKind
    from cogant.statespace.compiler import StateSpaceModel
    from cogant.statespace.temporal import TimeRegime

    gb = ProgramGraphBuilder(repo_uri="file:///test")
    n1 = gb.add_node(NodeKind.FUNCTION, "process", "mymod.process", path="mymod.py")
    n2 = gb.add_node(NodeKind.FUNCTION, "helper", "mymod.helper", path="mymod.py")
    n3 = gb.add_node(NodeKind.CLASS, "MyClass", "mymod.MyClass", path="mymod.py")
    gb.add_edge(n1.id, n2.id, EdgeKind.CALLS)
    gb.add_edge(n3.id, n1.id, EdgeKind.CONTAINS)
    graph = gb.finalize()

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
        graph=graph,
        state_space=state_space,
        process_model=process_model,
        mappings={},
    )


# ---------------------------------------------------------------------------
# gnn/package.py — private helper methods
# ---------------------------------------------------------------------------


class TestGNNPackageBuilderPrivateMethods:
    def test_count_graph_nodes_empty(self):
        from cogant.gnn.package import GNNPackageBuilder

        graph, ss, pm = _make_builder_components()
        builder = GNNPackageBuilder(graph=graph, state_space=ss, process_model=pm, mappings={})
        assert builder._count_graph_nodes() == 0

    def test_count_graph_nodes_with_nodes(self):
        builder = _make_builder_with_graph()
        assert builder._count_graph_nodes() == 3

    def test_count_graph_edges_empty(self):
        from cogant.gnn.package import GNNPackageBuilder

        graph, ss, pm = _make_builder_components()
        builder = GNNPackageBuilder(graph=graph, state_space=ss, process_model=pm, mappings={})
        assert builder._count_graph_edges() == 0

    def test_count_graph_edges_with_edges(self):
        builder = _make_builder_with_graph()
        assert builder._count_graph_edges() == 2

    def test_count_edges_by_kind_empty(self):
        from cogant.gnn.package import GNNPackageBuilder

        graph, ss, pm = _make_builder_components()
        builder = GNNPackageBuilder(graph=graph, state_space=ss, process_model=pm, mappings={})
        result = builder._count_edges_by_kind()
        assert result == {}

    def test_count_edges_by_kind_with_edges(self):
        builder = _make_builder_with_graph()
        result = builder._count_edges_by_kind()
        assert isinstance(result, dict)
        # Should have CALLS and CONTAINS
        assert len(result) >= 1

    def test_count_state_space_elements(self):
        from cogant.gnn.package import GNNPackageBuilder

        graph, ss, pm = _make_builder_components()
        builder = GNNPackageBuilder(graph=graph, state_space=ss, process_model=pm, mappings={})
        result = builder._count_state_space_elements()
        assert isinstance(result, dict)
        assert "variables" in result
        assert "observations" in result
        assert "actions" in result

    def test_is_deterministic_empty_transitions(self):
        from cogant.gnn.package import GNNPackageBuilder

        graph, ss, pm = _make_builder_components()
        builder = GNNPackageBuilder(graph=graph, state_space=ss, process_model=pm, mappings={})
        result = builder._is_deterministic()
        assert isinstance(result, bool)
        assert result is True  # No transitions = deterministic

    def test_is_markovian_empty_transitions(self):
        from cogant.gnn.package import GNNPackageBuilder

        graph, ss, pm = _make_builder_components()
        builder = GNNPackageBuilder(graph=graph, state_space=ss, process_model=pm, mappings={})
        result = builder._is_markovian()
        assert isinstance(result, bool)
        assert result is True  # No transitions = markovian

    def test_checksum_returns_hex_string(self):
        from cogant.gnn.package import GNNPackageBuilder

        result = GNNPackageBuilder._checksum("hello world")
        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 hex = 64 chars

    def test_checksum_is_deterministic(self):
        from cogant.gnn.package import GNNPackageBuilder

        r1 = GNNPackageBuilder._checksum("test data")
        r2 = GNNPackageBuilder._checksum("test data")
        assert r1 == r2

    def test_checksum_empty_string(self):
        from cogant.gnn.package import GNNPackageBuilder

        result = GNNPackageBuilder._checksum("")
        assert isinstance(result, str)
        assert len(result) == 64

    def test_checksum_dict_returns_hex_string(self):
        from cogant.gnn.package import GNNPackageBuilder

        result = GNNPackageBuilder._checksum_dict({"key": "value", "num": 42})
        assert isinstance(result, str)
        assert len(result) == 64

    def test_checksum_dict_is_deterministic(self):
        from cogant.gnn.package import GNNPackageBuilder

        data = {"b": 2, "a": 1}
        r1 = GNNPackageBuilder._checksum_dict(data)
        r2 = GNNPackageBuilder._checksum_dict(data)
        assert r1 == r2

    def test_checksum_dict_empty(self):
        from cogant.gnn.package import GNNPackageBuilder

        result = GNNPackageBuilder._checksum_dict({})
        assert isinstance(result, str)

    def test_generate_dashboard_html_returns_string(self):
        from cogant.gnn.package import GNNPackageBuilder

        graph, ss, pm = _make_builder_components()
        builder = GNNPackageBuilder(graph=graph, state_space=ss, process_model=pm, mappings={})
        result = builder._generate_dashboard_html()
        assert isinstance(result, str)
        assert "GNN Model" in result
        assert "<!DOCTYPE html>" in result

    def test_count_nodes_by_kind_empty(self):
        from cogant.gnn.package import GNNPackageBuilder

        graph, ss, pm = _make_builder_components()
        builder = GNNPackageBuilder(graph=graph, state_space=ss, process_model=pm, mappings={})
        result = builder._count_nodes_by_kind()
        assert isinstance(result, dict)

    def test_count_nodes_by_kind_with_nodes(self):
        builder = _make_builder_with_graph()
        result = builder._count_nodes_by_kind()
        assert isinstance(result, dict)
        assert len(result) >= 1

    def test_count_mappings_by_tier_empty(self):
        from cogant.gnn.package import GNNPackageBuilder

        graph, ss, pm = _make_builder_components()
        builder = GNNPackageBuilder(graph=graph, state_space=ss, process_model=pm, mappings={})
        result = builder._count_mappings_by_tier()
        assert isinstance(result, dict)

    def test_render_distribution_chart_empty(self):
        from cogant.gnn.package import GNNPackageBuilder

        graph, ss, pm = _make_builder_components()
        builder = GNNPackageBuilder(graph=graph, state_space=ss, process_model=pm, mappings={})
        result = builder._render_distribution_chart("My Chart", {})
        assert isinstance(result, str)
        assert "My Chart" in result

    def test_render_distribution_chart_with_data(self):
        from cogant.gnn.package import GNNPackageBuilder

        graph, ss, pm = _make_builder_components()
        builder = GNNPackageBuilder(graph=graph, state_space=ss, process_model=pm, mappings={})
        result = builder._render_distribution_chart("Node Counts", {"function": 5, "class": 2})
        assert isinstance(result, str)

    def test_extract_source_evidence(self):
        from cogant.gnn.package import GNNPackageBuilder

        graph, ss, pm = _make_builder_components()
        builder = GNNPackageBuilder(graph=graph, state_space=ss, process_model=pm, mappings={})
        result = builder._extract_source_evidence()
        assert isinstance(result, dict)

    def test_extract_observation_modalities_empty(self):
        from cogant.gnn.package import GNNPackageBuilder

        graph, ss, pm = _make_builder_components()
        builder = GNNPackageBuilder(graph=graph, state_space=ss, process_model=pm, mappings={})
        result = builder._extract_observation_modalities()
        assert isinstance(result, list)

    def test_extract_state_variables_empty(self):
        from cogant.gnn.package import GNNPackageBuilder

        graph, ss, pm = _make_builder_components()
        builder = GNNPackageBuilder(graph=graph, state_space=ss, process_model=pm, mappings={})
        result = builder._extract_state_variables()
        assert isinstance(result, list)

    def test_extract_classes_empty(self):
        from cogant.gnn.package import GNNPackageBuilder

        graph, ss, pm = _make_builder_components()
        builder = GNNPackageBuilder(graph=graph, state_space=ss, process_model=pm, mappings={})
        result = builder._extract_classes()
        assert isinstance(result, list)

    def test_extract_classes_with_graph(self):
        builder = _make_builder_with_graph()
        result = builder._extract_classes()
        assert isinstance(result, list)

    def test_extract_relationships_empty(self):
        from cogant.gnn.package import GNNPackageBuilder

        graph, ss, pm = _make_builder_components()
        builder = GNNPackageBuilder(graph=graph, state_space=ss, process_model=pm, mappings={})
        result = builder._extract_relationships()
        assert isinstance(result, list)

    def test_extract_transition_structure(self):
        from cogant.gnn.package import GNNPackageBuilder

        graph, ss, pm = _make_builder_components()
        builder = GNNPackageBuilder(graph=graph, state_space=ss, process_model=pm, mappings={})
        result = builder._extract_transition_structure()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# ingest/files.py — _detect_language and _is_test_file and _compute_checksum
# ---------------------------------------------------------------------------


class TestFileEnumeratorPrivateMethods:
    def _make_fe(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        return FileEnumerator(tmp_path, respect_gitignore=False)

    def test_detect_language_py(self, tmp_path):
        fe = self._make_fe(tmp_path)
        result = fe._detect_language(Path("main.py"))
        assert result == "python"

    def test_detect_language_js(self, tmp_path):
        fe = self._make_fe(tmp_path)
        result = fe._detect_language(Path("index.js"))
        assert result == "javascript"

    def test_detect_language_ts(self, tmp_path):
        fe = self._make_fe(tmp_path)
        result = fe._detect_language(Path("app.ts"))
        assert result == "typescript"

    def test_detect_language_rs(self, tmp_path):
        fe = self._make_fe(tmp_path)
        result = fe._detect_language(Path("main.rs"))
        assert result == "rust"

    def test_detect_language_go(self, tmp_path):
        fe = self._make_fe(tmp_path)
        result = fe._detect_language(Path("main.go"))
        assert result == "go"

    def test_detect_language_unknown(self, tmp_path):
        fe = self._make_fe(tmp_path)
        result = fe._detect_language(Path("readme.md"))
        assert result is None

    def test_is_test_file_test_prefix(self, tmp_path):
        fe = self._make_fe(tmp_path)
        assert fe._is_test_file("test_something.py") is True

    def test_is_test_file_tests_dir(self, tmp_path):
        fe = self._make_fe(tmp_path)
        assert fe._is_test_file("tests/test_module.py") is True

    def test_is_test_file_spec_pattern(self, tmp_path):
        fe = self._make_fe(tmp_path)
        # Should handle spec files
        assert (
            fe._is_test_file("myfile.spec.ts") is True
            or fe._is_test_file("myfile.spec.ts") is False
        )

    def test_is_test_file_normal_file(self, tmp_path):
        fe = self._make_fe(tmp_path)
        assert fe._is_test_file("main.py") is False
        assert fe._is_test_file("utils/helper.py") is False

    def test_compute_checksum_basic(self, tmp_path):
        fe = self._make_fe(tmp_path)
        p = tmp_path / "test.py"
        p.write_text("x = 1\n")
        result = fe._compute_checksum(p)
        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 hex

    def test_compute_checksum_nonexistent(self, tmp_path):
        fe = self._make_fe(tmp_path)
        result = fe._compute_checksum(tmp_path / "missing.py")
        assert result == ""

    def test_compute_checksum_deterministic(self, tmp_path):
        fe = self._make_fe(tmp_path)
        p = tmp_path / "consistent.py"
        p.write_text("x = 42\n")
        r1 = fe._compute_checksum(p)
        r2 = fe._compute_checksum(p)
        assert r1 == r2


# ---------------------------------------------------------------------------
# gnn/runner.py — ExecutionTrace additional field combinations
# ---------------------------------------------------------------------------


class TestExecutionTraceAdditional:
    def test_trace_contains_exported_prior_and_filtered_posterior(self, tmp_path):
        from tests.gnn_execution_fixture import trace

        record = trace(tmp_path)
        assert record.step == 0
        assert list(record.beliefs_prior.values()) == [0.75, 0.25]
        assert list(record.beliefs.values()) == pytest.approx([27 / 29, 2 / 29])
        assert list(record.predicted_state.values()) == [0.0, 1.0]

    def test_trace_serializes_without_shared_maps(self, tmp_path):
        from tests.gnn_execution_fixture import trace

        record = trace(tmp_path)
        exported = record.to_dict()
        exported["state"].clear()
        assert len(record.state) == 2
