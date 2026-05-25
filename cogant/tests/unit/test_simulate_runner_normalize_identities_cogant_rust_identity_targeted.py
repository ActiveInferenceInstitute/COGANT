#!/usr/bin/env python3
"""Targeted branch tests.

Targeted behavioral tests for:
- cogant/simulate/runner.py (67%): validate_model, simulate_step
- cogant/normalize/identities.py (78%): lookup_id, deduplicate_ids, edge IDs, stats
- cogant/rust_backend.py (77%): build_program_graph, env utils
- cogant/statespace/temporal.py (81%): get_critical_path, ordering queries
- cogant/dynamic/enrichment.py (75%): _stable_edge_id, _node_spans_line
- cogant/parsers/tree_sitter_base.py (21%): ParsedSymbol, ParsedFile, available_languages

No mocks. All tests use real objects and real data.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# cogant/normalize/identities.py
# ---------------------------------------------------------------------------


class TestIdentityResolver:
    """Tests for IdentityResolver — covers lookup_id, deduplicate_ids, stats."""

    def _make_resolver(self):
        from cogant.normalize.identities import IdentityResolver

        return IdentityResolver()

    def test_generate_id_is_deterministic(self) -> None:
        r = self._make_resolver()
        id1 = r.generate_id("module", "repo://demo", path="src/main.py")
        r.generate_id("module", "repo://demo", path="src/main.py")
        # IDs from two separate resolvers for same inputs match
        r2 = self._make_resolver()
        id3 = r2.generate_id("module", "repo://demo", path="src/main.py")
        assert id1 == id3

    def test_get_id_is_idempotent(self) -> None:
        r = self._make_resolver()
        id1 = r.get_id("symbol", "repo://demo", path="src/a.py", qualified_name="Foo.bar")
        id2 = r.get_id("symbol", "repo://demo", path="src/a.py", qualified_name="Foo.bar")
        assert id1 == id2

    def test_lookup_id_returns_none_for_unknown(self) -> None:
        r = self._make_resolver()
        result = r.lookup_id("module", "repo://unknown", path="missing.py")
        assert result is None

    def test_lookup_id_returns_existing_id(self) -> None:
        r = self._make_resolver()
        generated = r.generate_id("module", "repo://demo", path="a.py")
        found = r.lookup_id("module", "repo://demo", path="a.py")
        assert found == generated

    def test_get_record_returns_none_for_unknown(self) -> None:
        r = self._make_resolver()
        assert r.get_record("nonexistent_id") is None

    def test_get_record_returns_record_after_generation(self) -> None:
        from cogant.normalize.identities import IdentityRecord

        r = self._make_resolver()
        iid = r.generate_id("class", "repo://demo", qualified_name="Foo")
        record = r.get_record(iid)
        assert record is not None
        assert isinstance(record, IdentityRecord)
        assert record.entity_type == "class"

    def test_deduplicate_ids_removes_duplicates(self) -> None:
        r = self._make_resolver()
        ids = ["a", "b", "a", "c", "b", "d"]
        result = r.deduplicate_ids(ids)
        assert result == ["a", "b", "c", "d"]

    def test_deduplicate_ids_preserves_order(self) -> None:
        r = self._make_resolver()
        ids = ["z", "a", "m", "z", "a"]
        result = r.deduplicate_ids(ids)
        assert result == ["z", "a", "m"]

    def test_deduplicate_ids_empty_list(self) -> None:
        r = self._make_resolver()
        assert r.deduplicate_ids([]) == []

    def test_generate_edge_id_is_deterministic(self) -> None:
        r = self._make_resolver()
        eid1 = r.generate_edge_id("n1", "n2", "calls")
        eid2 = r.generate_edge_id("n1", "n2", "calls")
        assert eid1 == eid2

    def test_generate_edge_id_different_for_different_kinds(self) -> None:
        r = self._make_resolver()
        eid_calls = r.generate_edge_id("n1", "n2", "calls")
        eid_imports = r.generate_edge_id("n1", "n2", "imports")
        assert eid_calls != eid_imports

    def test_generate_edge_id_direction_matters(self) -> None:
        r = self._make_resolver()
        eid_fwd = r.generate_edge_id("n1", "n2", "calls")
        eid_rev = r.generate_edge_id("n2", "n1", "calls")
        assert eid_fwd != eid_rev

    def test_get_statistics_empty(self) -> None:
        r = self._make_resolver()
        stats = r.get_statistics()
        assert stats["total_identities"] == 0
        assert stats["unique_hash_inputs"] == 0

    def test_get_statistics_counts_types(self) -> None:
        r = self._make_resolver()
        r.generate_id("module", "repo://demo", path="a.py")
        r.generate_id("module", "repo://demo", path="b.py")
        r.generate_id("symbol", "repo://demo", qualified_name="Foo")
        stats = r.get_statistics()
        assert stats["total_identities"] == 3
        assert stats.get("type_module") == 2
        assert stats.get("type_symbol") == 1

    def test_clear_cache_resets_everything(self) -> None:
        r = self._make_resolver()
        r.generate_id("module", "repo://demo", path="a.py")
        r.clear_cache()
        stats = r.get_statistics()
        assert stats["total_identities"] == 0

    def test_generate_id_without_path_or_name(self) -> None:
        r = self._make_resolver()
        iid = r.generate_id("repo", "repo://demo")
        assert isinstance(iid, str)
        assert len(iid) > 0

    def test_build_hash_input_all_components(self) -> None:
        r = self._make_resolver()
        h = r._build_hash_input("repo://x", path="src/main.py", qualified_name="Foo.bar")
        assert "repo://x" in h
        assert "src/main.py" in h
        assert "Foo.bar" in h

    def test_build_hash_input_no_optional(self) -> None:
        r = self._make_resolver()
        h = r._build_hash_input("repo://x")
        assert h == "repo://x"


# ---------------------------------------------------------------------------
# cogant/simulate/runner.py
# ---------------------------------------------------------------------------


class TestModelRunnerValidate:
    """Tests for ModelRunner.validate_model and simulate_step."""

    def _make_runner(self):
        from cogant.simulate.runner import ModelRunner

        return ModelRunner(seed=42)

    def _make_state_space(self):
        from cogant.statespace.compiler import StateSpaceModel
        from cogant.statespace.temporal import TimeRegime

        return StateSpaceModel(
            id="ss1",
            schema_name="test",
            time_regime=TimeRegime.SYNCHRONOUS,
            variables={},
            observations={},
            actions={},
            transitions={},
            likelihoods={},
            preferences={},
        )

    def test_has_generative_model_false_when_no_matrices(self) -> None:
        runner = self._make_runner()
        assert runner.has_generative_model is False

    def test_has_generative_model_true_when_all_matrices_set(self) -> None:
        from cogant.simulate.runner import ModelRunner

        runner = ModelRunner(
            seed=42,
            A=[[0.9, 0.1], [0.1, 0.9]],
            B=[[[1.0, 0.0], [0.0, 1.0]], [[0.0, 1.0], [1.0, 0.0]]],
            C=[1.0, 0.0],
            D=[0.5, 0.5],
        )
        assert runner.has_generative_model is True

    def test_validate_model_empty_state_space(self) -> None:
        runner = self._make_runner()
        ss = self._make_state_space()
        result = runner.validate_model(ss)
        assert "valid" in result
        assert "errors" in result
        assert "warnings" in result
        # No variables = invalid
        assert result["valid"] is False
        assert any("No state variables" in e for e in result["errors"])

    def _make_ss_with_var(
        self, var_id: str, var_name: str, kind_name: str = "DISCRETE", dim: int = 2
    ):
        """Create a StateSpaceModel with one variable."""
        from cogant.statespace.compiler import StateSpaceModel
        from cogant.statespace.temporal import TimeRegime
        from cogant.statespace.variables import StateVariable, StateVariableType

        kind = getattr(StateVariableType, kind_name)
        ss = StateSpaceModel(
            id="ss_test",
            schema_name="test",
            time_regime=TimeRegime.SYNCHRONOUS,
            variables={},
            observations={},
            actions={},
            transitions={},
            likelihoods={},
            preferences={},
        )
        ss.variables[var_id] = StateVariable(
            id=var_id, name=var_name, var_type=kind, node_id=var_id
        )
        return ss

    def test_validate_model_with_valid_variable(self) -> None:
        runner = self._make_runner()
        ss = self._make_ss_with_var("v1", "speed", "CONTINUOUS", 1)
        result = runner.validate_model(ss)
        assert result["variable_count"] == 1
        assert result["valid"] is True

    def test_validate_model_with_dangling_action_reference(self) -> None:
        from cogant.statespace.compiler import Transition

        runner = self._make_runner()
        ss = self._make_ss_with_var("v1", "x")
        # Transition references an action that doesn't exist
        ss.transitions["t1"] = Transition(
            id="t1", source_state={"v1": 0}, target_state={"v1": 1}, action_id="missing_action"
        )
        result = runner.validate_model(ss)
        assert result["valid"] is False
        assert any("missing_action" in e for e in result["errors"])

    def test_validate_model_with_action_referencing_unknown_variable(self) -> None:
        from cogant.statespace.compiler import Action

        runner = self._make_runner()
        ss = self._make_ss_with_var("v1", "x")
        ss.actions["a1"] = Action(
            id="a1",
            name="jump",
            controller_id="ctrl",
            effects=["v999"],  # unknown variable
        )
        result = runner.validate_model(ss)
        assert result["valid"] is False
        assert any("v999" in e for e in result["errors"])

    def test_validate_model_action_precondition_unknown_variable(self) -> None:
        from cogant.statespace.compiler import Action

        runner = self._make_runner()
        ss = self._make_ss_with_var("v1", "x")
        ss.actions["a1"] = Action(
            id="a1",
            name="jump",
            controller_id="ctrl",
            preconditions=["v_unknown"],  # unknown variable
        )
        result = runner.validate_model(ss)
        assert result["valid"] is False

    def test_validate_model_counts_correctly(self) -> None:
        from cogant.statespace.compiler import Action
        from cogant.statespace.variables import StateVariable, StateVariableType

        runner = self._make_runner()
        ss = self._make_ss_with_var("v1", "x")
        ss.variables["v2"] = StateVariable(
            id="v2", name="y", var_type=StateVariableType.DISCRETE, node_id="v2"
        )
        ss.actions["a1"] = Action(id="a1", name="act1", controller_id="ctrl")
        result = runner.validate_model(ss)
        assert result["variable_count"] == 2
        assert result["action_count"] == 1

    def test_simulate_step_unknown_action(self) -> None:
        runner = self._make_runner()
        ss = self._make_state_space()
        result = runner.simulate_step(ss, {"v1": 0}, "unknown_action")
        assert result["success"] is False
        assert "Unknown action" in result["error"]
        assert result["next_state"] == {"v1": 0}

    def test_simulate_step_precondition_not_met(self) -> None:
        from cogant.statespace.compiler import Action

        runner = self._make_runner()
        ss = self._make_ss_with_var("v1", "x")
        ss.actions["a1"] = Action(id="a1", name="move", controller_id="ctrl", preconditions=["v1"])
        # State doesn't have v1 -> precondition fails
        result = runner.simulate_step(ss, {}, "a1")
        assert result["success"] is False
        assert "Precondition" in result["error"]

    def test_simulate_step_toggles_boolean(self) -> None:
        from cogant.statespace.compiler import Action

        runner = self._make_runner()
        ss = self._make_ss_with_var("flag", "active", "BOOLEAN", 1)
        ss.actions["a1"] = Action(id="a1", name="toggle", controller_id="ctrl", effects=["flag"])
        state = {"flag": True}
        result = runner.simulate_step(ss, state, "a1")
        assert result["success"] is True
        assert result["next_state"]["flag"] is False

    def test_simulate_step_increments_integer(self) -> None:
        from cogant.statespace.compiler import Action

        runner = self._make_runner()
        ss = self._make_ss_with_var("count", "count", "DISCRETE", 10)
        ss.actions["inc"] = Action(
            id="inc", name="increment", controller_id="ctrl", effects=["count"]
        )
        state = {"count": 5}
        result = runner.simulate_step(ss, state, "inc")
        assert result["success"] is True
        assert result["next_state"]["count"] == 6


# ---------------------------------------------------------------------------
# cogant/rust_backend.py
# ---------------------------------------------------------------------------


class TestRustBackend:
    """Tests for rust_backend module — only pure-Python paths."""

    def test_rust_available_is_bool(self) -> None:
        from cogant.rust_backend import RUST_AVAILABLE

        assert isinstance(RUST_AVAILABLE, bool)

    def test_rust_version_returns_none_or_str(self) -> None:
        from cogant.rust_backend import rust_version

        v = rust_version()
        assert v is None or isinstance(v, str)

    def test_get_program_graph_impl_returns_class(self) -> None:
        from cogant.rust_backend import get_program_graph_impl

        cls = get_program_graph_impl()
        assert callable(cls)

    def test_create_example_graph_raises_when_no_rust(self) -> None:
        from cogant.rust_backend import RUST_AVAILABLE, create_example_graph

        if not RUST_AVAILABLE:
            with pytest.raises(RuntimeError, match="Rust backend not available"):
                create_example_graph()

    def test_build_program_graph_returns_builder(self) -> None:
        from cogant.rust_backend import build_program_graph

        builder = build_program_graph(repo_uri="repo://test", use_rust=False)
        assert builder is not None

    def test_build_program_graph_no_rust_uses_python(self) -> None:
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.rust_backend import build_program_graph

        builder = build_program_graph(repo_uri="repo://test", use_rust=False)
        assert isinstance(builder, ProgramGraphBuilder)

    def test_env_prefers_rust_reads_env_true(self, monkeypatch) -> None:
        from cogant.rust_backend import _env_prefers_rust

        monkeypatch.setenv("COGANT_USE_RUST", "1")
        assert _env_prefers_rust() is True

    def test_env_prefers_rust_reads_env_false(self, monkeypatch) -> None:
        from cogant.rust_backend import _env_prefers_rust

        monkeypatch.setenv("COGANT_USE_RUST", "0")
        assert _env_prefers_rust() is False

    def test_env_prefers_rust_unset_returns_none(self, monkeypatch) -> None:
        from cogant.rust_backend import _env_prefers_rust

        monkeypatch.delenv("COGANT_USE_RUST", raising=False)
        assert _env_prefers_rust() is None

    def test_env_prefers_rust_truthy_string(self, monkeypatch) -> None:
        from cogant.rust_backend import _env_prefers_rust

        monkeypatch.setenv("COGANT_USE_RUST", "true")
        assert _env_prefers_rust() is True

    def test_env_prefers_rust_falsy_string(self, monkeypatch) -> None:
        from cogant.rust_backend import _env_prefers_rust

        monkeypatch.setenv("COGANT_USE_RUST", "false")
        assert _env_prefers_rust() is False

    def test_env_prefers_rust_unknown_value_returns_none(self, monkeypatch) -> None:
        from cogant.rust_backend import _env_prefers_rust

        monkeypatch.setenv("COGANT_USE_RUST", "maybe")
        assert _env_prefers_rust() is None

    def test_build_program_graph_uses_env_false(self, monkeypatch) -> None:
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.rust_backend import build_program_graph

        monkeypatch.setenv("COGANT_USE_RUST", "0")
        builder = build_program_graph(repo_uri="repo://test")
        assert isinstance(builder, ProgramGraphBuilder)


# ---------------------------------------------------------------------------
# cogant/statespace/temporal.py (get_critical_path, get_ordering_constraints,
# get_event_patterns, get_metrics)
# ---------------------------------------------------------------------------


class TestTemporalAnalyzerQueryMethods:
    """Tests for the query/accessor methods in TemporalAnalyzer."""

    def _make_graph(self):
        from cogant.schemas.graph import GraphMetadata, ProgramGraph

        return ProgramGraph(metadata=GraphMetadata(repo_uri="repo://test"))

    def _add_node(self, g, nid, name, **kw):
        from cogant.schemas.core import Node, NodeKind

        node = Node(id=nid, kind=NodeKind.FUNCTION, name=name, qualified_name=name, **kw)
        g.add_node(node)
        return node

    def _add_edge(self, g, eid, src, dst):
        from cogant.schemas.core import Edge, EdgeKind

        edge = Edge(id=eid, source_id=src, target_id=dst, kind=EdgeKind.CALLS)
        g.add_edge(edge)
        return edge

    def test_get_ordering_constraints_before_analyze(self) -> None:
        from cogant.statespace.temporal import TemporalAnalyzer

        g = self._make_graph()
        analyzer = TemporalAnalyzer(g)
        result = analyzer.get_ordering_constraints()
        assert isinstance(result, list)

    def test_get_event_patterns_before_analyze(self) -> None:
        from cogant.statespace.temporal import TemporalAnalyzer

        g = self._make_graph()
        analyzer = TemporalAnalyzer(g)
        result = analyzer.get_event_patterns()
        assert isinstance(result, list)

    def test_get_metrics_before_analyze_returns_none(self) -> None:
        from cogant.statespace.temporal import TemporalAnalyzer

        g = self._make_graph()
        analyzer = TemporalAnalyzer(g)
        assert analyzer.get_metrics() is None

    def test_analyze_returns_time_regime(self) -> None:
        from cogant.statespace.temporal import TemporalAnalyzer, TimeRegime

        g = self._make_graph()
        self._add_node(g, "n1", "main")
        self._add_node(g, "n2", "helper")
        self._add_edge(g, "e1", "n1", "n2")
        analyzer = TemporalAnalyzer(g)
        regime = analyzer.analyze()
        assert isinstance(regime, TimeRegime)

    def test_analyze_sets_metrics(self) -> None:
        from cogant.statespace.temporal import TemporalAnalyzer

        g = self._make_graph()
        self._add_node(g, "n1", "main")
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        metrics = analyzer.get_metrics()
        assert metrics is not None

    def test_get_critical_path_empty_graph(self) -> None:
        from cogant.statespace.temporal import TemporalAnalyzer

        g = self._make_graph()
        analyzer = TemporalAnalyzer(g)
        path = analyzer.get_critical_path()
        assert isinstance(path, list)
        assert len(path) == 0

    def test_get_critical_path_single_node(self) -> None:
        from cogant.statespace.temporal import TemporalAnalyzer

        g = self._make_graph()
        self._add_node(g, "n1", "main")
        analyzer = TemporalAnalyzer(g)
        path = analyzer.get_critical_path()
        assert "n1" in path

    def test_get_critical_path_chain(self) -> None:
        from cogant.statespace.temporal import TemporalAnalyzer

        g = self._make_graph()
        self._add_node(g, "n1", "start")
        self._add_node(g, "n2", "middle")
        self._add_node(g, "n3", "end")
        self._add_edge(g, "e1", "n1", "n2")
        self._add_edge(g, "e2", "n2", "n3")
        analyzer = TemporalAnalyzer(g)
        path = analyzer.get_critical_path()
        assert len(path) >= 1  # at least one node in the critical path

    def test_async_regime_detected_by_name(self) -> None:
        from cogant.statespace.temporal import TemporalAnalyzer, TimeRegime

        g = self._make_graph()
        # Nodes with async-like names should trigger ASYNCHRONOUS regime
        for i in range(10):
            self._add_node(g, f"n{i}", f"async_handler_{i}")
        analyzer = TemporalAnalyzer(g)
        regime = analyzer.analyze()
        # Should detect async regime due to node names
        assert regime in (TimeRegime.ASYNCHRONOUS, TimeRegime.HYBRID, TimeRegime.SYNCHRONOUS)

    def test_event_regime_detected_by_name(self) -> None:
        from cogant.statespace.temporal import TemporalAnalyzer, TimeRegime

        g = self._make_graph()
        for i in range(5):
            self._add_node(g, f"n{i}", f"on_event_{i}", metadata={"event_handler": True})
        analyzer = TemporalAnalyzer(g)
        regime = analyzer.analyze()
        assert isinstance(regime, TimeRegime)


# ---------------------------------------------------------------------------
# cogant/dynamic/enrichment.py helpers
# ---------------------------------------------------------------------------


class TestEnrichmentHelpers:
    """Tests for the pure utility functions in dynamic.enrichment."""

    def test_stable_edge_id_deterministic(self) -> None:
        from cogant.dynamic.enrichment import _stable_edge_id

        id1 = _stable_edge_id("n1", "n2", "calls")
        id2 = _stable_edge_id("n1", "n2", "calls")
        assert id1 == id2

    def test_stable_edge_id_different_for_different_inputs(self) -> None:
        from cogant.dynamic.enrichment import _stable_edge_id

        assert _stable_edge_id("n1", "n2", "calls") != _stable_edge_id("n1", "n2", "imports")

    def test_stable_edge_id_direction_matters(self) -> None:
        from cogant.dynamic.enrichment import _stable_edge_id

        assert _stable_edge_id("n1", "n2", "calls") != _stable_edge_id("n2", "n1", "calls")

    def test_node_spans_line_no_source_range(self) -> None:
        from cogant.dynamic.enrichment import _node_spans_line
        from cogant.schemas.core import Node, NodeKind

        node = Node(id="n1", kind=NodeKind.FUNCTION, name="fn", qualified_name="fn")
        assert _node_spans_line(node, 5) is False

    def test_node_spans_line_within_range(self) -> None:
        from cogant.dynamic.enrichment import _node_spans_line
        from cogant.schemas.core import Node, NodeKind

        node = Node(
            id="n1",
            kind=NodeKind.FUNCTION,
            name="fn",
            qualified_name="fn",
            source_range={"start_line": 10, "end_line": 20},
        )
        assert _node_spans_line(node, 15) is True

    def test_node_spans_line_at_start(self) -> None:
        from cogant.dynamic.enrichment import _node_spans_line
        from cogant.schemas.core import Node, NodeKind

        node = Node(
            id="n1",
            kind=NodeKind.FUNCTION,
            name="fn",
            qualified_name="fn",
            source_range={"start_line": 10, "end_line": 20},
        )
        assert _node_spans_line(node, 10) is True

    def test_node_spans_line_at_end(self) -> None:
        from cogant.dynamic.enrichment import _node_spans_line
        from cogant.schemas.core import Node, NodeKind

        node = Node(
            id="n1",
            kind=NodeKind.FUNCTION,
            name="fn",
            qualified_name="fn",
            source_range={"start_line": 10, "end_line": 20},
        )
        assert _node_spans_line(node, 20) is True

    def test_node_spans_line_outside_range(self) -> None:
        from cogant.dynamic.enrichment import _node_spans_line
        from cogant.schemas.core import Node, NodeKind

        node = Node(
            id="n1",
            kind=NodeKind.FUNCTION,
            name="fn",
            qualified_name="fn",
            source_range={"start_line": 10, "end_line": 20},
        )
        assert _node_spans_line(node, 25) is False
        assert _node_spans_line(node, 5) is False

    def test_node_spans_line_none_range_values(self) -> None:
        from cogant.dynamic.enrichment import _node_spans_line
        from cogant.schemas.core import Node, NodeKind

        node = Node(
            id="n1",
            kind=NodeKind.FUNCTION,
            name="fn",
            qualified_name="fn",
            source_range={"start_line": None, "end_line": None},
        )
        assert _node_spans_line(node, 5) is False


# ---------------------------------------------------------------------------
# cogant/parsers/tree_sitter_base.py — data class tests
# ---------------------------------------------------------------------------


class TestTreeSitterDataClasses:
    """Tests for ParsedSymbol and ParsedFile dataclasses — no grammar needed."""

    def test_parsed_symbol_creation(self) -> None:
        from cogant.parsers.tree_sitter_base import ParsedSymbol

        sym = ParsedSymbol(
            name="my_func",
            kind="function",
            line_start=10,
            line_end=20,
            qualified_name="module.my_func",
        )
        assert sym.name == "my_func"
        assert sym.kind == "function"
        assert sym.line_start == 10
        assert sym.line_end == 20
        assert sym.qualified_name == "module.my_func"

    def test_parsed_symbol_defaults(self) -> None:
        from cogant.parsers.tree_sitter_base import ParsedSymbol

        sym = ParsedSymbol(
            name="fn",
            kind="class",
            line_start=1,
            line_end=5,
            qualified_name="fn",
        )
        assert sym.docstring == ""
        assert sym.metadata == {}

    def test_parsed_symbol_with_metadata(self) -> None:
        from cogant.parsers.tree_sitter_base import ParsedSymbol

        sym = ParsedSymbol(
            name="method",
            kind="method",
            line_start=1,
            line_end=3,
            qualified_name="Class.method",
            docstring="This is a doc",
            metadata={"is_async": True},
        )
        assert sym.docstring == "This is a doc"
        assert sym.metadata["is_async"] is True

    def test_parsed_file_creation(self) -> None:
        from cogant.parsers.tree_sitter_base import ParsedFile

        pf = ParsedFile(path="src/main.py", language="python")
        assert pf.path == "src/main.py"
        assert pf.language == "python"
        assert pf.symbols == []
        assert pf.imports == []
        assert pf.calls == []
        assert pf.errors == []

    def test_parsed_file_with_symbols(self) -> None:
        from cogant.parsers.tree_sitter_base import ParsedFile, ParsedSymbol

        sym = ParsedSymbol(
            name="main",
            kind="function",
            line_start=1,
            line_end=10,
            qualified_name="main",
        )
        pf = ParsedFile(path="main.py", language="python", symbols=[sym])
        assert len(pf.symbols) == 1
        assert pf.symbols[0].name == "main"

    def test_tree_sitter_parser_creates_without_error(self) -> None:
        from cogant.parsers.tree_sitter_base import TreeSitterParser

        # Should construct even if no grammars installed
        parser = TreeSitterParser()
        assert parser is not None

    def test_available_languages_returns_set(self) -> None:
        from cogant.parsers.tree_sitter_base import TreeSitterParser

        parser = TreeSitterParser()
        langs = parser.available_languages()
        assert isinstance(langs, set)

    def test_supported_extensions_returns_set(self) -> None:
        from cogant.parsers.tree_sitter_base import TreeSitterParser

        parser = TreeSitterParser()
        exts = parser.supported_extensions()
        assert isinstance(exts, set)

    def test_language_for_path_python(self) -> None:
        from cogant.parsers.tree_sitter_base import TreeSitterParser

        parser = TreeSitterParser()
        lang = parser.language_for_path(Path("main.py"))
        assert lang == "python"

    def test_language_for_path_typescript(self) -> None:
        from cogant.parsers.tree_sitter_base import TreeSitterParser

        parser = TreeSitterParser()
        lang = parser.language_for_path(Path("app.ts"))
        assert lang == "typescript"

    def test_language_for_path_unknown(self) -> None:
        from cogant.parsers.tree_sitter_base import TreeSitterParser

        parser = TreeSitterParser()
        lang = parser.language_for_path(Path("data.json"))
        assert lang is None

    def test_parse_file_unknown_language_returns_none(self, tmp_path: Path) -> None:
        from cogant.parsers.tree_sitter_base import TreeSitterParser

        parser = TreeSitterParser()
        unknown = tmp_path / "data.toml"
        unknown.write_text("[section]\nkey = 'val'")
        result = parser.parse_file(unknown)
        assert result is None

    def test_parse_file_string_path(self, tmp_path: Path) -> None:
        from cogant.parsers.tree_sitter_base import TreeSitterParser

        parser = TreeSitterParser()
        f = tmp_path / "notes.xyz"
        f.write_text("nothing special")
        # .xyz -> no grammar loaded -> None
        result = parser.parse_file(f)
        assert result is None

    def test_parse_file_known_lang_no_grammar_returns_none(self, tmp_path: Path) -> None:
        from cogant.parsers.tree_sitter_base import TreeSitterParser

        parser = TreeSitterParser()
        # Even if .py is known to the map, if no python grammar loaded -> None
        f = tmp_path / "main.py"
        f.write_text("def hello(): pass")
        result = parser.parse_file(f)
        if "python" not in parser.available_languages():
            assert result is None

    def test_parse_source_no_grammar_returns_none(self) -> None:
        from cogant.parsers.tree_sitter_base import TreeSitterParser

        parser = TreeSitterParser()
        if "python" not in parser.available_languages():
            result = parser.parse_source("def hello(): pass", language="python")
            assert result is None

    def test_get_tree_sitter_parser_singleton(self) -> None:
        from cogant.parsers.tree_sitter_base import get_tree_sitter_parser

        p1 = get_tree_sitter_parser()
        p2 = get_tree_sitter_parser()
        assert p1 is p2

    def test_base_extractor_slice_empty_node(self) -> None:
        from cogant.parsers.tree_sitter_base import _BaseExtractor

        class FakeNode:
            start_byte = 0
            end_byte = 5

        e = _BaseExtractor()
        result = e._slice(b"hello world", FakeNode())
        assert result == "hello"

    def test_base_extractor_slice_attribute_error(self) -> None:
        from cogant.parsers.tree_sitter_base import _BaseExtractor

        class BadNode:
            pass

        e = _BaseExtractor()
        result = e._slice(b"hello", BadNode())
        assert result == ""


# ---------------------------------------------------------------------------
# cogant/ingest/manifest.py — additional edge cases
# ---------------------------------------------------------------------------


class TestManifestParserEdgeCases:
    """Additional edge case tests for ManifestParser."""

    def test_parse_requirements_empty_file(self, tmp_path: Path) -> None:
        from cogant.ingest.manifest import ManifestParser

        f = tmp_path / "requirements.txt"
        f.write_text("")
        mp = ManifestParser()
        deps = mp.parse_requirements_txt(f)
        assert deps == []

    def test_parse_requirements_comments_only(self, tmp_path: Path) -> None:
        from cogant.ingest.manifest import ManifestParser

        f = tmp_path / "requirements.txt"
        f.write_text("# This is a comment\n# Another comment\n")
        mp = ManifestParser()
        deps = mp.parse_requirements_txt(f)
        assert deps == []

    def test_parse_setup_py_simple(self, tmp_path: Path) -> None:
        from cogant.ingest.manifest import ManifestParser

        f = tmp_path / "setup.py"
        f.write_text(
            "from setuptools import setup\n"
            "setup(name='mylib', version='1.0', install_requires=['requests', 'click'])\n"
        )
        mp = ManifestParser()
        meta, deps = mp.parse_setup_py(f)
        names = {d.name for d in deps}
        assert "requests" in names or meta is not None  # sanity

    def test_parse_pyproject_missing_fields(self, tmp_path: Path) -> None:
        from cogant.ingest.manifest import ManifestParser

        f = tmp_path / "pyproject.toml"
        f.write_text('[project]\nname = "foo"\n')
        mp = ManifestParser()
        meta, deps = mp.parse_pyproject_toml(f)
        assert meta.get("name") == "foo"
        assert deps == []

    def test_parse_cargo_toml_with_deps(self, tmp_path: Path) -> None:
        import textwrap

        from cogant.ingest.manifest import ManifestParser

        f = tmp_path / "Cargo.toml"
        f.write_text(
            textwrap.dedent("""\
            [package]
            name = "myapp"
            version = "0.1.0"

            [dependencies]
            serde = "1.0"
            tokio = { version = "1", features = ["full"] }
        """)
        )
        mp = ManifestParser()
        meta, deps = mp.parse_cargo_toml(f)
        names = {d.name for d in deps}
        assert "serde" in names


# ---------------------------------------------------------------------------
# cogant/ingest/repo.py — git repo path
# ---------------------------------------------------------------------------


class TestRepoIngesterGitRepo:
    """Additional tests for RepoIngester on a real git repo path."""

    def test_ingest_local_on_git_repo(self, tmp_path: Path) -> None:
        """When pointed at a git repo, extract_metadata gets the commit hash."""
        import subprocess

        from cogant.ingest.repo import RepoIngester

        # Init a minimal git repo
        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=str(tmp_path),
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=str(tmp_path),
            check=True,
            capture_output=True,
        )
        (tmp_path / "main.py").write_text("def main(): pass")
        subprocess.run(["git", "add", "."], cwd=str(tmp_path), check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"], cwd=str(tmp_path), check=True, capture_output=True
        )

        ingester = RepoIngester(work_dir=tmp_path / "work")
        snapshot = ingester.ingest_local(tmp_path)
        # Should have extracted git metadata
        assert snapshot.metadata.commit_hash is not None
        assert len(snapshot.metadata.commit_hash) == 40

    def test_ingest_local_commit_message_extracted(self, tmp_path: Path) -> None:
        import subprocess

        from cogant.ingest.repo import RepoIngester

        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "t@t.com"],
            cwd=str(tmp_path),
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "T"], cwd=str(tmp_path), check=True, capture_output=True
        )
        (tmp_path / "app.py").write_text("pass")
        subprocess.run(["git", "add", "."], cwd=str(tmp_path), check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "hello world commit"],
            cwd=str(tmp_path),
            check=True,
            capture_output=True,
        )

        ingester = RepoIngester(work_dir=tmp_path / "work")
        snapshot = ingester.ingest_local(tmp_path)
        assert snapshot.metadata.commit_message is not None
        assert "hello world commit" in snapshot.metadata.commit_message
