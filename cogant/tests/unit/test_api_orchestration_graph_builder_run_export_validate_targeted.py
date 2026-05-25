#!/usr/bin/env python3
"""Targeted branch tests — api/orchestration.py run_export, run_validate,
run_dynamic helpers; graph/builder.py ProgramGraphBuilder extended.

Covers:
- run_export: empty bundle (no artifacts), with program graph, with state space model
- run_validate: no graph (synthetic result), with graph (empty)
- run_dynamic: no coverage/trace returns gracefully
- graph/builder.py: ProgramGraphBuilder.get_statistics, finalize, add_node with metadata
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _make_bundle(tmp_path):
    from cogant.api.bundle import Bundle

    return Bundle(target=str(tmp_path))


def _full_pipeline_bundle(tmp_path, python_src=None):
    """Run ingest+graph chain and return bundle."""
    from cogant.api.orchestration import run_graph, run_ingest

    bundle = _make_bundle(tmp_path)
    if python_src:
        (tmp_path / "mod.py").write_text(python_src)
    run_ingest(str(tmp_path), bundle)
    run_graph(bundle, str(tmp_path))
    return bundle


# ---------------------------------------------------------------------------
# api/orchestration.py — run_export
# ---------------------------------------------------------------------------


class TestRunExport:
    def test_run_export_empty_bundle(self, tmp_path):
        from cogant.api.orchestration import run_export

        bundle = _make_bundle(tmp_path)
        out = tmp_path / "output"
        result = run_export(bundle, str(out))
        assert isinstance(result, dict)
        assert result["type"] == "export"
        assert "output_dir" in result
        assert "artifacts" in result

    def test_run_export_creates_output_dir(self, tmp_path):
        from cogant.api.orchestration import run_export

        bundle = _make_bundle(tmp_path)
        out = tmp_path / "new_output"
        assert not out.exists()
        run_export(bundle, str(out))
        assert out.exists()

    def test_run_export_with_program_graph(self, tmp_path):
        from cogant.api.orchestration import run_export

        bundle = _full_pipeline_bundle(tmp_path)
        out = tmp_path / "output"
        result = run_export(bundle, str(out))
        assert isinstance(result, dict)
        # Should have written program_graph.json
        written = result.get("artifacts", [])
        pg_files = [f for f in written if "program_graph" in f]
        assert len(pg_files) >= 1
        assert Path(pg_files[0]).exists()

    def test_run_export_stores_export_paths(self, tmp_path):
        from cogant.api.orchestration import run_export

        bundle = _make_bundle(tmp_path)
        out = tmp_path / "output"
        run_export(bundle, str(out))
        paths = bundle.artifacts.get("export_paths")
        assert isinstance(paths, list)

    def test_run_export_with_state_space(self, tmp_path):
        from cogant.api.orchestration import (
            run_export,
            run_graph,
            run_ingest,
            run_statespace,
            run_translate,
        )

        (tmp_path / "m.py").write_text("class Agent:\n    state: int = 0\n")
        bundle = _make_bundle(tmp_path)
        run_ingest(str(tmp_path), bundle)
        run_graph(bundle, str(tmp_path))
        run_translate(bundle)
        run_statespace(bundle, str(tmp_path))
        out = tmp_path / "output"
        result = run_export(bundle, str(out))
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# api/orchestration.py — run_validate
# ---------------------------------------------------------------------------


class TestRunValidate:
    def test_run_validate_no_graph(self, tmp_path):
        from cogant.api.orchestration import run_validate

        bundle = _make_bundle(tmp_path)
        result = run_validate(bundle)
        assert isinstance(result, dict)
        assert result["type"] == "validation"
        assert result["passed"] is False
        assert "warnings" in result

    def test_run_validate_with_empty_graph(self, tmp_path):
        from cogant.api.orchestration import run_validate

        bundle = _full_pipeline_bundle(tmp_path)
        result = run_validate(bundle)
        assert isinstance(result, dict)
        assert result["type"] == "validation"
        assert "passed" in result
        assert "checks" in result

    def test_run_validate_with_python_module(self, tmp_path):
        from cogant.api.orchestration import run_validate

        bundle = _full_pipeline_bundle(tmp_path, python_src="class Foo:\n    def bar(self): pass\n")
        result = run_validate(bundle)
        assert isinstance(result, dict)
        assert "issues" in result

    def test_run_validate_issues_is_list(self, tmp_path):
        from cogant.api.orchestration import run_validate

        bundle = _full_pipeline_bundle(tmp_path)
        result = run_validate(bundle)
        assert isinstance(result.get("issues", []), list)


# ---------------------------------------------------------------------------
# api/orchestration.py — run_dynamic
# ---------------------------------------------------------------------------


class TestRunDynamic:
    def test_run_dynamic_no_coverage_no_trace(self, tmp_path):
        from cogant.api.orchestration import run_dynamic

        bundle = _full_pipeline_bundle(tmp_path)
        result = run_dynamic(bundle, coverage_path=None, trace_path=None)
        assert isinstance(result, dict)

    def test_run_dynamic_empty_bundle(self, tmp_path):
        from cogant.api.orchestration import run_dynamic

        bundle = _make_bundle(tmp_path)
        result = run_dynamic(bundle)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# graph/builder.py — ProgramGraphBuilder extended
# ---------------------------------------------------------------------------


class TestProgramGraphBuilderExtended:
    def test_get_statistics_empty(self):
        from cogant.graph.builder import ProgramGraphBuilder

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        stats = builder.get_statistics()
        assert isinstance(stats, dict)
        # Stats should have some keys about nodes/edges
        total_nodes = (
            sum(stats.get("nodes_by_kind", {}).values())
            if "nodes_by_kind" in stats
            else stats.get("node_count", 0)
        )
        assert total_nodes == 0

    def test_get_statistics_with_nodes(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import EdgeKind, NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        n1 = builder.add_node(NodeKind.MODULE, "mod", "mod", path="mod.py")
        n2 = builder.add_node(NodeKind.CLASS, "Cls", "mod.Cls", path="mod.py")
        builder.add_edge(n1.id, n2.id, EdgeKind.CONTAINS)
        stats = builder.get_statistics()
        # Stats format: either node_count or nodes_by_kind
        total_nodes = (
            sum(stats.get("nodes_by_kind", {}).values())
            if "nodes_by_kind" in stats
            else stats.get("node_count", 0)
        )
        total_edges = (
            sum(stats.get("edges_by_kind", {}).values())
            if "edges_by_kind" in stats
            else stats.get("edge_count", 0)
        )
        assert total_nodes >= 2
        assert total_edges >= 1

    def test_add_node_with_metadata(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        node = builder.add_node(
            NodeKind.FUNCTION, "myfunc", "mod.myfunc", path="mod.py", language="python"
        )
        assert node is not None
        assert node.name == "myfunc"

    def test_finalize_returns_program_graph(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        builder.add_node(NodeKind.MODULE, "m", "m", path="m.py")
        graph = builder.finalize()
        assert graph is not None
        assert len(graph.nodes) >= 1

    def test_repo_uri_in_metadata(self):
        from cogant.graph.builder import ProgramGraphBuilder

        builder = ProgramGraphBuilder(repo_uri="file:///myrepo")
        graph = builder.finalize()
        assert graph.metadata.repo_uri == "file:///myrepo"
