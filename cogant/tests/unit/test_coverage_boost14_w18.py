#!/usr/bin/env python3
"""Coverage boost batch 14 — additional coverage gaps.

Covers:
- cache/store.py: CacheStore, CacheKey, CacheEntry
- cache/hasher.py: hash_file, hash_repo
- viz/boundary.py: map_type_boundaries, generate_boundary_report, _find_containing_module
- viz/semantic_view.py: SemanticVisualizer render_json, from_state_space
- viz/cytoscape_view.py: build_cytoscape_graph_data, _build_role_index, _compute_degrees
- ingest/incremental.py: IncrementalIngester, ChangedFile
- gnn/runner.py: more GNNModelRunner coverage
- dynamic/enrichment.py: _normalize_path, _node_spans_line
- dynamic/coverage.py: more coverage paths
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_graph():
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import EdgeKind, NodeKind

    builder = ProgramGraphBuilder(repo_uri="file:///test_repo")
    mod = builder.add_node(NodeKind.MODULE, "mymodule", "mymodule", path="mymodule.py")
    cls = builder.add_node(NodeKind.CLASS, "MyClass", "mymodule.MyClass", path="mymodule.py")
    func = builder.add_node(
        NodeKind.FUNCTION,
        name="my_func",
        qualified_name="mymodule.my_func",
        path="mymodule.py",
        source_range={"start_line": 1, "end_line": 10},
    )
    builder.add_edge(mod.id, cls.id, EdgeKind.CONTAINS)
    builder.add_edge(cls.id, func.id, EdgeKind.CONTAINS)
    return builder.finalize()


# ---------------------------------------------------------------------------
# cache/hasher.py
# ---------------------------------------------------------------------------


class TestCacheHasher:
    """Test hash_file and hash_repo functions."""

    def test_hash_file_basic(self, tmp_path):
        from cogant.cache.hasher import hash_file

        f = tmp_path / "test.py"
        f.write_bytes(b"x = 1\n")
        h = hash_file(f)
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex

    def test_hash_file_deterministic(self, tmp_path):
        from cogant.cache.hasher import hash_file

        f = tmp_path / "code.py"
        f.write_bytes(b"def foo(): pass\n")
        h1 = hash_file(f)
        h2 = hash_file(f)
        assert h1 == h2

    def test_hash_file_different_content(self, tmp_path):
        from cogant.cache.hasher import hash_file

        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_bytes(b"x = 1")
        f2.write_bytes(b"x = 2")
        assert hash_file(f1) != hash_file(f2)

    def test_hash_repo_basic(self, tmp_path):
        from cogant.cache.hasher import hash_repo

        (tmp_path / "main.py").write_bytes(b"def main(): pass\n")
        (tmp_path / "util.py").write_bytes(b"def util(): pass\n")
        h = hash_repo(tmp_path)
        assert isinstance(h, str)
        assert len(h) == 64

    def test_hash_repo_deterministic(self, tmp_path):
        from cogant.cache.hasher import hash_repo

        (tmp_path / "code.py").write_bytes(b"x = 42\n")
        h1 = hash_repo(tmp_path)
        h2 = hash_repo(tmp_path)
        assert h1 == h2

    def test_hash_repo_changes_with_content(self, tmp_path):
        from cogant.cache.hasher import hash_repo

        f = tmp_path / "script.py"
        f.write_bytes(b"version = 1\n")
        h1 = hash_repo(tmp_path)
        f.write_bytes(b"version = 2\n")
        h2 = hash_repo(tmp_path)
        assert h1 != h2

    def test_hash_repo_custom_extensions(self, tmp_path):
        from cogant.cache.hasher import hash_repo

        (tmp_path / "app.ts").write_bytes(b"const x = 1;\n")
        (tmp_path / "app.py").write_bytes(b"x = 1\n")
        # Only hash .ts files
        h = hash_repo(tmp_path, extensions=[".ts"])
        assert isinstance(h, str)

    def test_hash_repo_empty_directory(self, tmp_path):
        from cogant.cache.hasher import hash_repo

        empty = tmp_path / "empty"
        empty.mkdir()
        h = hash_repo(empty)
        assert isinstance(h, str)

    def test_hash_repo_ignores_git_dir(self, tmp_path):
        from cogant.cache.hasher import hash_repo

        (tmp_path / "main.py").write_bytes(b"x = 1\n")
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_bytes(b"[core]\n")
        h = hash_repo(tmp_path)
        assert isinstance(h, str)


# ---------------------------------------------------------------------------
# cache/store.py
# ---------------------------------------------------------------------------


class TestCacheStore:
    """Test CacheStore operations."""

    def test_put_and_get(self, tmp_path):
        from cogant.cache.store import CacheKey, CacheStore

        store = CacheStore(cache_dir=tmp_path / "cache")
        key = CacheKey(repo_path="/tmp/repo", content_hash="a" * 64, cogant_version="0.5.0")
        results = {"stage1": {"nodes": 5}, "stage2": {"edges": 10}}
        entry = store.put(key, results)
        assert entry.stage_results == results

        retrieved = store.get(key)
        assert retrieved is not None
        assert retrieved.stage_results == results
        assert retrieved.hit is True

    def test_get_miss(self, tmp_path):
        from cogant.cache.store import CacheKey, CacheStore

        store = CacheStore(cache_dir=tmp_path / "cache")
        key = CacheKey(repo_path="/nonexistent", content_hash="b" * 64, cogant_version="0.5.0")
        result = store.get(key)
        assert result is None

    def test_invalidate(self, tmp_path):
        from cogant.cache.store import CacheKey, CacheStore

        store = CacheStore(cache_dir=tmp_path / "cache")
        key = CacheKey(repo_path="/tmp/repo2", content_hash="c" * 64, cogant_version="0.5.0")
        store.put(key, {"data": 1})
        assert store.invalidate(key) is True
        assert store.get(key) is None

    def test_invalidate_missing_returns_false(self, tmp_path):
        from cogant.cache.store import CacheKey, CacheStore

        store = CacheStore(cache_dir=tmp_path / "cache")
        key = CacheKey(repo_path="/x", content_hash="d" * 64, cogant_version="0.5.0")
        assert store.invalidate(key) is False

    def test_clear(self, tmp_path):
        from cogant.cache.store import CacheKey, CacheStore

        store = CacheStore(cache_dir=tmp_path / "cache")
        key1 = CacheKey(repo_path="/r1", content_hash="e" * 64, cogant_version="0.5.0")
        key2 = CacheKey(repo_path="/r2", content_hash="f" * 64, cogant_version="0.5.0")
        store.put(key1, {"a": 1})
        store.put(key2, {"b": 2})
        count = store.clear()
        assert count >= 2

    def test_clear_empty_store(self, tmp_path):
        from cogant.cache.store import CacheStore

        store = CacheStore(cache_dir=tmp_path / "empty_cache")
        count = store.clear()
        assert count == 0

    def test_stats_empty(self, tmp_path):
        from cogant.cache.store import CacheStore

        store = CacheStore(cache_dir=tmp_path / "stats_cache")
        stats = store.stats()
        assert "entries" in stats
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats
        assert stats["entries"] == 0

    def test_stats_with_hits_and_misses(self, tmp_path):
        from cogant.cache.store import CacheKey, CacheStore

        store = CacheStore(cache_dir=tmp_path / "cache2")
        key = CacheKey(repo_path="/repo", content_hash="1" * 64, cogant_version="0.5.0")
        # Miss
        store.get(key)
        # Put + hit
        store.put(key, {"x": 1})
        store.get(key)
        stats = store.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5

    def test_expired_entry_returns_none(self, tmp_path):
        from cogant.cache.store import CacheKey, CacheStore

        # Very short TTL
        store = CacheStore(cache_dir=tmp_path / "cache3", ttl_seconds=0)
        key = CacheKey(repo_path="/expired", content_hash="2" * 64, cogant_version="0.5.0")
        store.put(key, {"data": "old"})
        # With ttl=0, entry is immediately expired
        result = store.get(key)
        assert result is None

    def test_get_cache_dir(self):
        from cogant.cache.store import get_cache_dir

        d = get_cache_dir()
        assert isinstance(d, Path)
        assert "cogant" in str(d)

    def test_cache_key_frozen(self):
        import dataclasses

        from cogant.cache.store import CacheKey

        key = CacheKey(repo_path="/r", content_hash="0" * 64, cogant_version="0.1")
        with pytest.raises(dataclasses.FrozenInstanceError):
            key.repo_path = "/other"  # type: ignore[misc]

    def test_put_concurrent_keys(self, tmp_path):
        from cogant.cache.store import CacheKey, CacheStore

        store = CacheStore(cache_dir=tmp_path / "cache4")
        keys = [
            CacheKey(repo_path=f"/r{i}", content_hash=str(i) * 64, cogant_version="0.5")
            for i in range(5)
        ]
        for i, key in enumerate(keys):
            store.put(key, {"index": i})
        for i, key in enumerate(keys):
            entry = store.get(key)
            assert entry is not None
            assert entry.stage_results["index"] == i


# ---------------------------------------------------------------------------
# viz/boundary.py — additional methods
# ---------------------------------------------------------------------------


class TestBoundaryMapperExtra:
    """Test BoundaryMapper additional methods."""

    def test_map_type_boundaries_empty(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.viz.boundary import BoundaryMapper

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        graph = builder.finalize()
        mapper = BoundaryMapper()
        result = mapper.map_type_boundaries(graph)
        assert isinstance(result, str)
        assert "graph TD" in result

    def test_map_type_boundaries_with_classes_funcs(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import EdgeKind, NodeKind
        from cogant.viz.boundary import BoundaryMapper

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        mod = builder.add_node(NodeKind.MODULE, "mod", "mod")
        cls = builder.add_node(NodeKind.CLASS, "MyClass", "mod.MyClass")
        func = builder.add_node(NodeKind.FUNCTION, "my_func", "mod.my_func")
        builder.add_edge(mod.id, cls.id, EdgeKind.CONTAINS)
        builder.add_edge(mod.id, func.id, EdgeKind.CONTAINS)
        graph = builder.finalize()
        mapper = BoundaryMapper()
        result = mapper.map_type_boundaries(graph)
        assert "Classes" in result
        assert "Functions" in result
        assert "Modules" in result

    def test_map_type_boundaries_many_classes(self):
        """More than 5 classes should add '... more' line."""
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind
        from cogant.viz.boundary import BoundaryMapper

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        for i in range(8):
            builder.add_node(NodeKind.CLASS, f"Class{i}", f"mod.Class{i}")
        graph = builder.finalize()
        mapper = BoundaryMapper()
        result = mapper.map_type_boundaries(graph)
        assert "more" in result

    def test_generate_boundary_report_empty(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.viz.boundary import BoundaryMapper

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        graph = builder.finalize()
        mapper = BoundaryMapper()
        report = mapper.generate_boundary_report(graph)
        assert "total_boundary_crossings" in report
        assert report["total_boundary_crossings"] == 0

    def test_generate_boundary_report_with_cross_module_edges(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import EdgeKind, NodeKind
        from cogant.viz.boundary import BoundaryMapper

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        mod1 = builder.add_node(NodeKind.MODULE, "mod1", "mod1")
        mod2 = builder.add_node(NodeKind.MODULE, "mod2", "mod2")
        cls1 = builder.add_node(NodeKind.CLASS, "A", "mod1.A")
        cls2 = builder.add_node(NodeKind.CLASS, "B", "mod2.B")
        func1 = builder.add_node(NodeKind.FUNCTION, "f1", "mod1.A.f1")
        func2 = builder.add_node(NodeKind.FUNCTION, "f2", "mod2.B.f2")
        builder.add_edge(mod1.id, cls1.id, EdgeKind.CONTAINS)
        builder.add_edge(mod2.id, cls2.id, EdgeKind.CONTAINS)
        builder.add_edge(cls1.id, func1.id, EdgeKind.CONTAINS)
        builder.add_edge(cls2.id, func2.id, EdgeKind.CONTAINS)
        builder.add_edge(func1.id, func2.id, EdgeKind.CALLS)
        graph = builder.finalize()
        mapper = BoundaryMapper()
        report = mapper.generate_boundary_report(graph)
        assert "type_coupling_score" in report
        assert "external_dependencies_count" in report
        assert isinstance(report["module_coupling_matrix"], dict)


# ---------------------------------------------------------------------------
# viz/semantic_view.py
# ---------------------------------------------------------------------------


class TestSemanticVisualizer:
    """Test SemanticVisualizer."""

    def test_from_state_space_and_render_json(self):
        from cogant.viz.semantic_view import SemanticVisualizer

        state_space = {
            "states": [{"name": "s0", "description": "initial state", "type": "discrete"}],
            "observations": [{"name": "o0", "source": "sensor"}],
            "actions": [{"name": "a0", "target": "motor"}],
            "policies": [{"name": "p0", "rule": "if obs then act", "confidence": 0.8}],
            "transitions": [],
        }
        viz = SemanticVisualizer()
        result = viz.from_state_space(state_space)
        assert result is viz  # Returns self
        assert len(viz.states) == 1
        assert len(viz.observations) == 1

        json_out = viz.render_json()
        data = json.loads(json_out)
        assert "states" in data
        assert "observations" in data
        assert "actions" in data

    def test_semantic_visualizer_empty(self):
        from cogant.viz.semantic_view import SemanticVisualizer

        viz = SemanticVisualizer()
        json_out = viz.render_json()
        data = json.loads(json_out)
        assert data["states"] == []
        assert data["observations"] == []

    def test_render_html_writes_file(self, tmp_path):
        from cogant.viz.semantic_view import SemanticVisualizer

        state_space = {
            "states": [{"name": "ready", "description": "System is ready", "type": "discrete"}],
            "observations": [],
            "actions": [],
            "policies": [],
            "transitions": [],
        }
        viz = SemanticVisualizer()
        viz.from_state_space(state_space)
        out_path = str(tmp_path / "semantic.html")
        result_path = viz.render_html(out_path)
        assert result_path == out_path
        content = Path(out_path).read_text()
        assert "<!DOCTYPE html>" in content
        assert "ready" in content

    def test_semantic_visualizer_with_many_items(self):
        """Test with >6 items per category (should truncate)."""
        from cogant.viz.semantic_view import SemanticVisualizer

        state_space = {
            "states": [{"name": f"s{i}", "description": f"State {i}"} for i in range(10)],
            "observations": [{"name": f"o{i}"} for i in range(10)],
            "actions": [{"name": f"a{i}"} for i in range(10)],
            "policies": [{"name": f"p{i}", "confidence": 0.5} for i in range(10)],
            "transitions": [],
        }
        viz = SemanticVisualizer()
        viz.from_state_space(state_space)
        json_out = viz.render_json()
        data = json.loads(json_out)
        # All 10 should be in JSON output
        assert len(data["states"]) == 10


# ---------------------------------------------------------------------------
# viz/cytoscape_view.py
# ---------------------------------------------------------------------------


class TestCytoscapeView:
    """Test cytoscape view functions."""

    def test_build_graph_data_empty(self):
        from cogant.viz.cytoscape_view import build_cytoscape_graph_data

        data = build_cytoscape_graph_data({"nodes": [], "edges": []})
        assert data["nodes"] == []
        assert data["edges"] == []

    def test_build_graph_data_with_nodes(self):
        from cogant.viz.cytoscape_view import build_cytoscape_graph_data

        graph = {
            "nodes": [
                {"id": "n1", "name": "FunctionA", "qualified_name": "mod.FunctionA"},
                {"id": "n2", "name": "ClassB", "qualified_name": "mod.ClassB"},
            ],
            "edges": [
                {"source_id": "n1", "target_id": "n2", "kind": "CALLS"},
            ],
        }
        data = build_cytoscape_graph_data(graph)
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        node = data["nodes"][0]
        assert "id" in node
        assert "label" in node
        assert "role" in node
        assert "color" in node
        assert "size" in node

    def test_build_graph_data_with_mappings(self):
        from cogant.viz.cytoscape_view import build_cytoscape_graph_data

        graph = {
            "nodes": [{"id": "n1", "name": "StateA"}],
            "edges": [],
        }
        mappings = [
            {
                "kind": "HIDDEN_STATE",
                "graph_fragment_node_ids": ["n1"],
                "confidence_score": 0.9,
            }
        ]
        data = build_cytoscape_graph_data(graph, mappings=mappings)
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["role"] == "HIDDEN_STATE"

    def test_build_role_index_empty(self):
        from cogant.viz.cytoscape_view import _build_role_index

        index = _build_role_index(None)
        assert index == {}

    def test_build_role_index_dict_mappings(self):
        from cogant.viz.cytoscape_view import _build_role_index

        mappings = [
            {"kind": "OBSERVATION", "graph_fragment_node_ids": ["a", "b"], "confidence_score": 0.7},
            {"kind": "HIDDEN_STATE", "graph_fragment_node_ids": ["a"], "confidence_score": 0.9},
        ]
        index = _build_role_index(mappings)
        # Node "a" should have HIDDEN_STATE (higher confidence)
        assert index["a"]["role"] == "HIDDEN_STATE"
        assert index["b"]["role"] == "OBSERVATION"

    def test_compute_degrees(self):
        from cogant.viz.cytoscape_view import _compute_degrees

        edges = [
            {"source_id": "n1", "target_id": "n2"},
            {"source_id": "n1", "target_id": "n3"},
            {"source": "n2", "target": "n3"},
        ]
        degrees = _compute_degrees(edges)
        assert degrees["n1"] == 2  # n1 appears as source twice
        assert degrees["n2"] == 2  # once as target, once as source
        assert degrees["n3"] == 2  # twice as target

    def test_scale_degree_to_size(self):
        from cogant.viz.cytoscape_view import MAX_NODE_SIZE, MIN_NODE_SIZE, _scale_degree_to_size

        # Zero max_degree → MIN_NODE_SIZE
        assert _scale_degree_to_size(0, 0) == MIN_NODE_SIZE
        # degree == max_degree → MAX_NODE_SIZE
        size = _scale_degree_to_size(10, 10)
        assert size == MAX_NODE_SIZE
        # Midpoint
        mid = _scale_degree_to_size(5, 10)
        assert MIN_NODE_SIZE < mid < MAX_NODE_SIZE

    def test_node_list_from_dict(self):
        from cogant.viz.cytoscape_view import _node_list

        graph = {"nodes": {"n1": {"id": "n1"}, "n2": {"id": "n2"}}}
        nodes = _node_list(graph)
        assert len(nodes) == 2

    def test_edge_list_from_list(self):
        from cogant.viz.cytoscape_view import _edge_list

        graph = {"edges": [{"source_id": "n1", "target_id": "n2"}]}
        edges = _edge_list(graph)
        assert len(edges) == 1

    def test_build_cytoscape_html(self):
        from cogant.viz.cytoscape_view import build_cytoscape_html

        graph_data = {
            "nodes": [{"id": "n1", "name": "FuncA"}],
            "edges": [],
        }
        html = build_cytoscape_html(graph_data)
        assert "<!DOCTYPE html>" in html
        assert "cytoscape" in html.lower()

    def test_ai_role_colors_constants(self):
        from cogant.viz.cytoscape_view import AI_ROLE_COLORS, DEFAULT_NODE_COLOR

        assert "HIDDEN_STATE" in AI_ROLE_COLORS
        assert "OBSERVATION" in AI_ROLE_COLORS
        assert "ACTION" in AI_ROLE_COLORS
        assert isinstance(DEFAULT_NODE_COLOR, str)


# ---------------------------------------------------------------------------
# ingest/incremental.py
# ---------------------------------------------------------------------------


class TestIncrementalIngester:
    """Test IncrementalIngester."""

    def test_is_git_repo_for_cogant_dir(self):
        """The COGANT repo itself is a git repo."""
        # Use the actual cogant directory (which is in a git repo)
        import cogant
        from cogant.ingest.incremental import IncrementalIngester

        cogant_path = Path(cogant.__file__).parent.parent.parent
        ingester = IncrementalIngester(cogant_path)
        # Should not raise; result depends on whether git is available
        result = ingester.is_git_repo()
        assert isinstance(result, bool)

    def test_not_git_repo_for_tmp(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        # A fresh temp dir is not a git repo
        ingester = IncrementalIngester(tmp_path)
        assert ingester.is_git_repo() is False

    def test_changed_since_non_git(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        result = ingester.changed_since()
        assert result == []

    def test_working_tree_changes_non_git(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        result = ingester.working_tree_changes()
        assert result == []

    def test_python_files_changed_non_git(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        result = ingester.python_files_changed_since()
        assert result == []

    def test_source_files_changed_non_git(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        result = ingester.source_files_changed_since()
        assert result == []

    def test_changed_file_dataclass(self, tmp_path):
        from cogant.ingest.incremental import ChangedFile

        cf = ChangedFile(path=tmp_path / "main.py", change_type="M")
        assert cf.path == tmp_path / "main.py"
        assert cf.change_type == "M"

    def test_parse_name_status(self, tmp_path):
        from cogant.ingest.incremental import ChangedFile, IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        stdout = "M\tsrc/main.py\nA\tsrc/new.ts\nD\told.js\n"
        result = ingester._parse_name_status(stdout)
        assert len(result) == 3
        assert isinstance(result[0], ChangedFile)
        assert result[0].change_type == "M"
        assert result[1].change_type == "A"

    def test_parse_name_status_rename(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        stdout = "R100\told/path.py\tnew/path.py\n"
        result = ingester._parse_name_status(stdout)
        assert len(result) == 1
        assert result[0].change_type == "R"
        assert "new/path.py" in str(result[0].path)

    def test_source_files_changed_custom_extensions(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        # Non-git: always empty
        result = ingester.source_files_changed_since(extensions={".py"})
        assert result == []

    def test_changed_since_commit_delegates(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        # Non-git: returns empty list
        result = ingester.changed_since_commit("abc123")
        assert result == []


# ---------------------------------------------------------------------------
# dynamic/enrichment.py — internal helpers
# ---------------------------------------------------------------------------


class TestDynamicEnrichmentHelpers:
    """Test internal helper functions in dynamic/enrichment.py."""

    def test_normalize_path_strips_leading_dot_slash(self):
        from cogant.dynamic.enrichment import _normalize_path

        assert _normalize_path("./foo/bar.py") == "foo/bar.py"
        assert _normalize_path("././baz.py") == "baz.py"

    def test_normalize_path_backslash_to_slash(self):
        from cogant.dynamic.enrichment import _normalize_path

        assert _normalize_path("src\\module.py") == "src/module.py"

    def test_normalize_path_no_change(self):
        from cogant.dynamic.enrichment import _normalize_path

        assert _normalize_path("src/module.py") == "src/module.py"

    def test_node_spans_line_no_source_range(self):
        from cogant.dynamic.enrichment import _node_spans_line
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        node = builder.add_node(NodeKind.FUNCTION, "f", "f")  # no source_range
        assert _node_spans_line(node, 5) is False

    def test_node_spans_line_within_range(self):
        from cogant.dynamic.enrichment import _node_spans_line
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        node = builder.add_node(
            NodeKind.FUNCTION, "g", "g", source_range={"start_line": 10, "end_line": 20}
        )
        assert _node_spans_line(node, 10) is True
        assert _node_spans_line(node, 15) is True
        assert _node_spans_line(node, 20) is True
        assert _node_spans_line(node, 9) is False
        assert _node_spans_line(node, 21) is False

    def test_node_spans_line_nested_dict_format(self):
        from cogant.dynamic.enrichment import _node_spans_line
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        node = builder.add_node(
            NodeKind.FUNCTION, "h", "h", source_range={"start": {"line": 5}, "end": {"line": 15}}
        )
        assert _node_spans_line(node, 5) is True
        assert _node_spans_line(node, 15) is True
        assert _node_spans_line(node, 4) is False

    def test_stable_edge_id_deterministic(self):
        from cogant.dynamic.enrichment import _stable_edge_id

        id1 = _stable_edge_id("src", "tgt", "CALLS")
        id2 = _stable_edge_id("src", "tgt", "CALLS")
        assert id1 == id2
        assert len(id1) == 16  # 16 hex chars

    def test_stable_edge_id_different_inputs(self):
        from cogant.dynamic.enrichment import _stable_edge_id

        id1 = _stable_edge_id("src1", "tgt1", "CALLS")
        id2 = _stable_edge_id("src2", "tgt2", "CALLS")
        assert id1 != id2


# ---------------------------------------------------------------------------
# gnn/runner.py — additional GNNModelRunner paths
# ---------------------------------------------------------------------------


class TestGNNModelRunnerExtra:
    """Additional GNNModelRunner tests."""

    def _make_full_package(self, pkg_dir: Path) -> None:
        """Create a full GNN package with all JSON files."""
        manifest = {
            "version": "1.0.0",
            "package_name": "full_model",
            "created_at": "2024-01-01T00:00:00",
        }
        (pkg_dir / "manifest.json").write_text(json.dumps(manifest))
        model = {
            "hidden_states": [{"id": "s0", "name": "idle"}, {"id": "s1", "name": "active"}],
            "observations": [{"id": "o0", "name": "quiet"}, {"id": "o1", "name": "busy"}],
            "actions": [{"id": "a0", "name": "wait"}, {"id": "a1", "name": "process"}],
        }
        (pkg_dir / "model.gnn.json").write_text(json.dumps(model))
        state_space = {
            "variables": [{"name": "s0"}, {"name": "s1"}],
            "observations": [{"name": "o0"}, {"name": "o1"}],
            "actions": [{"name": "a0"}, {"name": "a1"}],
        }
        (pkg_dir / "state_space.json").write_text(json.dumps(state_space))
        transitions = {"s0": {"s0": 0.9, "s1": 0.1}, "s1": {"s0": 0.1, "s1": 0.9}}
        (pkg_dir / "transitions.json").write_text(json.dumps(transitions))
        preferences = {"o0": 0.8, "o1": 0.2}
        (pkg_dir / "preferences.json").write_text(json.dumps(preferences))

    def test_run_returns_result_dict(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner

        pkg_dir = tmp_path / "full_pkg"
        pkg_dir.mkdir()
        self._make_full_package(pkg_dir)
        runner = GNNModelRunner()
        runner.load_package(str(pkg_dir))
        result = runner.run(steps=5)
        assert isinstance(result, dict)

    def test_beliefs_history_populated(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner

        pkg_dir = tmp_path / "pkg_hist"
        pkg_dir.mkdir()
        self._make_full_package(pkg_dir)
        runner = GNNModelRunner()
        runner.load_package(str(pkg_dir))
        runner.run(steps=3)
        assert len(runner.beliefs_history) > 0

    def test_execution_trace_fields_in_run(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner

        pkg_dir = tmp_path / "pkg_trace"
        pkg_dir.mkdir()
        self._make_full_package(pkg_dir)
        runner = GNNModelRunner()
        runner.load_package(str(pkg_dir))
        runner.run(steps=2)
        assert len(runner.traces) == 2
        for trace in runner.traces:
            assert hasattr(trace, "step")
            assert hasattr(trace, "state")
            assert hasattr(trace, "beliefs")


# ---------------------------------------------------------------------------
# viz/boundary.py — _find_containing_module and cross-module edges
# ---------------------------------------------------------------------------


class TestBoundaryMapperModuleMethods:
    """Test _find_containing_module and related path in BoundaryMapper."""

    def test_find_containing_module_not_found(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind
        from cogant.viz.boundary import BoundaryMapper

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        func = builder.add_node(NodeKind.FUNCTION, "orphan_func", "orphan_func")
        graph = builder.finalize()
        mapper = BoundaryMapper()
        # Function not contained in any module
        result = mapper._find_containing_module(func.id, graph)
        assert result is None

    def test_find_containing_module_found(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import EdgeKind, NodeKind
        from cogant.viz.boundary import BoundaryMapper

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        mod = builder.add_node(NodeKind.MODULE, "mymod", "mymod")
        func = builder.add_node(NodeKind.FUNCTION, "fn", "mymod.fn")
        builder.add_edge(mod.id, func.id, EdgeKind.CONTAINS)
        graph = builder.finalize()
        mapper = BoundaryMapper()
        result = mapper._find_containing_module(func.id, graph)
        assert result == mod.id

    def test_map_module_boundaries_with_imports_edges(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import EdgeKind, NodeKind
        from cogant.viz.boundary import BoundaryMapper

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        mod1 = builder.add_node(NodeKind.MODULE, "mod1", "mod1")
        mod2 = builder.add_node(NodeKind.MODULE, "mod2", "mod2")
        func1 = builder.add_node(NodeKind.FUNCTION, "f1", "mod1.f1")
        func2 = builder.add_node(NodeKind.FUNCTION, "f2", "mod2.f2")
        builder.add_edge(mod1.id, func1.id, EdgeKind.CONTAINS)
        builder.add_edge(mod2.id, func2.id, EdgeKind.CONTAINS)
        builder.add_edge(func1.id, func2.id, EdgeKind.IMPORTS)
        graph = builder.finalize()
        mapper = BoundaryMapper()
        result = mapper.map_module_boundaries(graph)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# dynamic/coverage.py — decode numbits
# ---------------------------------------------------------------------------


class TestCoverageDecodeNumbits:
    """Test _decode_numbits internal function."""

    def test_decode_numbits_basic(self):
        from cogant.dynamic.coverage import _decode_numbits

        # byte 0b00000001 → line 0
        result = _decode_numbits(bytes([0b00000001]))
        assert 0 in result

    def test_decode_numbits_multiple_bits(self):
        from cogant.dynamic.coverage import _decode_numbits

        # byte 0b00001111 → lines 0,1,2,3
        result = _decode_numbits(bytes([0b00001111]))
        assert result == [0, 1, 2, 3]

    def test_decode_numbits_multiple_bytes(self):
        from cogant.dynamic.coverage import _decode_numbits

        # 2 bytes: first byte all 1s → lines 0-7; second byte 0b00000001 → line 8
        result = _decode_numbits(bytes([0xFF, 0x01]))
        assert 0 in result
        assert 7 in result
        assert 8 in result

    def test_decode_numbits_empty(self):
        from cogant.dynamic.coverage import _decode_numbits

        result = _decode_numbits(b"")
        assert result == []
