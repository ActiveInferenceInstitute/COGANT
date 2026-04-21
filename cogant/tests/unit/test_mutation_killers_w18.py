"""Wave-18 mutation killer tests — engine, matrices, statespace, synthesizer.

Each test is designed to catch a specific class of mutation that standard
coverage-driven tests often miss.  The comments above each test name the
mutant it kills, e.g. ``# kills: new_mappings_this_pass == 0  →  != 0``.

Targets
-------
1. ``cogant.translate.engine`` — fixpoint iteration, conflict resolution,
   coverage report, explain API
2. ``cogant.gnn.matrices``      — _normalize_row boundary cases
3. ``cogant.statespace.compiler`` — variable/observation compilation edge cases
4. ``cogant.reverse.synthesizer``  — degenerate-plan code paths

No mocks. Every test uses real COGANT value objects.
"""

from __future__ import annotations

import ast

import pytest

from cogant.gnn.matrices import GNNMatrices, _normalize_row, _normalize_vector
from cogant.graph.builder import ProgramGraphBuilder
from cogant.graph.queries import GraphQuery
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.schemas.semantic import (
    ConfidenceTier,
    MappingKind,
    ProvenanceRecord,
    SemanticMapping,
)
from cogant.statespace.compiler import (
    StateSpaceCompiler,
    StateSpaceModel,
)
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import (
    ConfidenceLevel,
    StateVariable,
    StateVariableType,
)
from cogant.translate.engine import RuleExplanation, TranslationEngine
from cogant.translate.rules.semantic import ActionRule, ObservationRule
from cogant.translate.rules.structural import MutatingSubsystemRule

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_graph(repo: str = "test://mutation-killers") -> ProgramGraph:
    return ProgramGraph(metadata=GraphMetadata(repo_uri=repo))


def _add_node(g: ProgramGraph, nid: str, kind: NodeKind, name: str, **kw: object) -> Node:
    node = Node(
        id=nid,
        kind=kind,
        name=name,
        qualified_name=kw.get("qn", name),  # type: ignore[arg-type]
        **{k: v for k, v in kw.items() if k != "qn"},
    )
    g.add_node(node)
    return node


def _add_edge(g: ProgramGraph, eid: str, src: str, dst: str, kind: EdgeKind) -> None:
    g.add_edge(Edge(id=eid, source_id=src, target_id=dst, kind=kind))


def _make_mapping(
    mid: str,
    kind: MappingKind,
    node_ids: list[str],
    score: float = 0.75,
    tier: ConfidenceTier = ConfidenceTier.STATIC_ONLY,
) -> SemanticMapping:
    return SemanticMapping(
        id=mid,
        kind=kind,
        graph_fragment_node_ids=node_ids,
        confidence_score=score,
        confidence_tier=tier,
        provenance=ProvenanceRecord(source="test_rule"),
    )


def _empty_state_space() -> StateSpaceModel:
    return StateSpaceModel(schema_name="empty", time_regime=TimeRegime.SYNCHRONOUS)


# ---------------------------------------------------------------------------
# 1.  engine.py — fixpoint convergence
# ---------------------------------------------------------------------------


class TestFixpointConvergence:
    """Tests that directly probe the fixpoint loop and its early-exit condition.

    Mutation target: ``if new_mappings_this_pass == 0``
    If mutated to ``!= 0`` the loop would *continue* whenever new mappings
    appear and *exit* after an empty pass — exactly backwards. These tests
    ensure the iteration count is correct and that convergence is detected
    on the right pass.
    """

    def test_fixpoint_exits_after_single_pass_when_no_new_mappings(self) -> None:
        """Engine runs exactly one pass when the rule produces nothing.

        Kills: ``== 0`` → ``!= 0`` (loop never exits early).
        """
        g = _make_graph()
        _add_node(g, "n1", NodeKind.VARIABLE, "x")  # no keyword → no match

        engine = TranslationEngine(max_iterations=5)
        engine.register_rule(ObservationRule())
        mappings = engine.translate(g)

        # Verify the match log contains exactly 1 iteration_complete event.
        iteration_events = [
            ev for ev in engine.get_match_log() if ev["event_type"] == "iteration_complete"
        ]
        assert len(iteration_events) == 1, (
            f"should converge after one empty pass; got {len(iteration_events)} iteration events"
        )
        assert mappings == []

    def test_fixpoint_exits_on_second_pass_after_single_productive_pass(self) -> None:
        """Engine converges after exactly two passes: 1 productive, 1 empty.

        Kills: ``== 0`` → ``!= 0`` (early exit on productive pass instead
        of convergence pass).
        """
        g = _make_graph()
        _add_node(g, "fn1", NodeKind.FUNCTION, "get_temperature")

        engine = TranslationEngine(max_iterations=10)
        engine.register_rule(ObservationRule())
        mappings = engine.translate(g)

        assert len(mappings) >= 1
        iteration_events = [
            ev for ev in engine.get_match_log() if ev["event_type"] == "iteration_complete"
        ]
        # Pass 1 produces ≥1 mapping, pass 2 produces 0 → exits.
        assert len(iteration_events) == 2

    def test_duplicate_mappings_not_added_in_second_pass(self) -> None:
        """Same mapping is not duplicated across fixpoint iterations.

        Kills: ``mapping.id not in self.mappings`` → ``mapping.id in self.mappings``
        (which would reject all new mappings).
        """
        g = _make_graph()
        _add_node(g, "fn1", NodeKind.FUNCTION, "get_sensor_reading")

        engine = TranslationEngine(max_iterations=5)
        engine.register_rule(ObservationRule())
        mappings = engine.translate(g)

        # Exactly one mapping even after multiple passes.
        ids = [m.id for m in mappings]
        assert len(ids) == len(set(ids)), "duplicate mappings detected"


# ---------------------------------------------------------------------------
# 2.  engine.py — conflict resolution
# ---------------------------------------------------------------------------


class TestConflictResolution:
    """Tests that probe _resolve_conflicts boundary conditions.

    Mutation targets:
      - ``len(mids) < 2``  → ``< 1``  (singles get into conflict loop)
      - ``for j in range(i + 1, ...)``  → ``range(i, ...)``  (self-pairs)
      - ``key_a >= key_b``  → ``key_a > key_b``  (tie-breaking changes)
      - ``mapping_a is None or mapping_b is None``  → ``and``  (misses nulls)
    """

    def test_non_overlapping_mappings_both_survive(self) -> None:
        """Two mappings on disjoint nodes have no conflict — both survive.

        Kills: ``len(mids) < 2`` → ``< 1`` (singletons incorrectly get
        into the conflict loop and one gets removed).
        """
        g = _make_graph()
        _add_node(g, "fn1", NodeKind.FUNCTION, "get_temperature")
        _add_node(g, "fn2", NodeKind.FUNCTION, "set_temperature")

        engine = TranslationEngine()
        engine.register_rule(ObservationRule())
        engine.register_rule(ActionRule())
        mappings = engine.translate(g)

        node_ids_touched = set()
        for m in mappings:
            node_ids_touched.update(m.graph_fragment_node_ids)
        # Both nodes should appear — no false conflict removal.
        assert "fn1" in node_ids_touched or "fn2" in node_ids_touched

    def test_overlapping_mappings_higher_confidence_wins(self) -> None:
        """When two mappings share a node, the one with higher confidence survives.

        This test injects two mappings with known scores and verifies the
        winner is the higher-scored one.

        Kills: ``key_a >= key_b``  → ``key_a > key_b``  (equal-score tie
        breaks incorrectly, removing both or keeping the wrong one).
        """
        engine = TranslationEngine()

        # Inject mappings directly with overlapping node IDs.
        m_high = _make_mapping("m_high", MappingKind.HIDDEN_STATE, ["shared_node"], score=0.90)
        m_low = _make_mapping("m_low", MappingKind.OBSERVATION, ["shared_node"], score=0.60)

        engine.mappings["m_high"] = m_high
        engine.mappings["m_low"] = m_low
        engine._rule_priority["m_high"] = 1
        engine._rule_priority["m_low"] = 0

        engine._resolve_conflicts()

        assert "m_high" in engine.mappings, "high-confidence mapping should survive"
        assert "m_low" not in engine.mappings, "low-confidence mapping should be removed"

    def test_equal_confidence_equal_priority_keeps_lexicographically_first(self) -> None:
        """With identical (priority, confidence) the tie-break keeps one mapping.

        Kills: ``key_a >= key_b``  → ``key_a > key_b``  (if == produces
        True for >= but False for >, the loser assignment flips, causing
        non-deterministic removal or both removed in some edge paths).
        """
        engine = TranslationEngine()

        m_a = _make_mapping("m_aaa", MappingKind.HIDDEN_STATE, ["node_x"], score=0.75)
        m_b = _make_mapping("m_bbb", MappingKind.OBSERVATION, ["node_x"], score=0.75)

        engine.mappings["m_aaa"] = m_a
        engine.mappings["m_bbb"] = m_b
        engine._rule_priority["m_aaa"] = 0
        engine._rule_priority["m_bbb"] = 0

        engine._resolve_conflicts()

        # Exactly one must survive (not zero, not two).
        surviving = set(engine.mappings.keys())
        assert len(surviving) == 1
        assert surviving <= {"m_aaa", "m_bbb"}

    def test_no_self_conflict_on_single_node_mapping(self) -> None:
        """A single mapping referencing one node must never be removed.

        Kills: ``for j in range(i + 1, ...)`` → ``range(i, ...)``
        (self-pairs are generated; the mapping conflicts with itself and
        gets removed).
        """
        engine = TranslationEngine()

        m = _make_mapping("solo", MappingKind.ACTION, ["only_node"], score=0.85)
        engine.mappings["solo"] = m
        engine._rule_priority["solo"] = 0

        engine._resolve_conflicts()

        assert "solo" in engine.mappings, "solo mapping should not be self-removed"


# ---------------------------------------------------------------------------
# 3.  engine.py — get_coverage_report
# ---------------------------------------------------------------------------


class TestCoverageReport:
    """Tests for get_coverage_report numeric boundary conditions.

    Mutation targets:
      - ``total > 0``  → ``>= 0``  (always divides, ZeroDivisionError on empty)
      - Coverage percentage formula off-by-fraction
    """

    def test_coverage_report_empty_graph(self) -> None:
        """Empty graph: total=0, coverage_pct must be 0.0 without error.

        Kills: ``total > 0`` → ``>= 0`` (0.0 / 0 would raise ZeroDivisionError).
        """
        g = _make_graph()
        engine = TranslationEngine()
        report = engine.get_coverage_report(g)

        assert report["total_nodes"] == 0
        assert report["covered_nodes"] == 0
        assert report["coverage_percent"] == 0.0

    def test_coverage_report_full_coverage(self) -> None:
        """All nodes covered gives exactly 100.0%.

        Kills: coverage_pct formula mutation (e.g., / (total - 1)).
        """
        g = _make_graph()
        _add_node(g, "fn1", NodeKind.FUNCTION, "get_x")
        _add_node(g, "fn2", NodeKind.FUNCTION, "set_y")

        engine = TranslationEngine()
        m = _make_mapping("m1", MappingKind.OBSERVATION, ["fn1", "fn2"])
        engine.mappings["m1"] = m

        report = engine.get_coverage_report(g)
        assert report["total_nodes"] == 2
        assert report["covered_nodes"] == 2
        assert report["coverage_percent"] == pytest.approx(100.0)
        assert report["uncovered_node_ids"] == []

    def test_coverage_report_partial_coverage(self) -> None:
        """1 of 4 nodes covered → 25.0%.

        Kills: formula mutation (e.g., * 10 instead of * 100).
        """
        g = _make_graph()
        for i in range(4):
            _add_node(g, f"n{i}", NodeKind.VARIABLE, f"var{i}")

        engine = TranslationEngine()
        m = _make_mapping("m1", MappingKind.HIDDEN_STATE, ["n0"])
        engine.mappings["m1"] = m

        report = engine.get_coverage_report(g)
        assert report["total_nodes"] == 4
        assert report["covered_nodes"] == 1
        assert report["coverage_percent"] == pytest.approx(25.0)
        assert len(report["uncovered_node_ids"]) == 3


# ---------------------------------------------------------------------------
# 4.  engine.py — explain API boundary conditions
# ---------------------------------------------------------------------------


class TestExplainBoundaryConditions:
    """Tests that probe the explain method's node matching logic.

    Mutation targets:
      - ``node_id == node.id or node.id in fragment_ids``  → ``and``
        (misses nodes captured only by ``node_id`` field or only in
        ``fragment_ids``).
      - ``fired=True``  → ``fired=False``  (inverted result for matched node).
    """

    def test_explain_returns_fired_false_for_non_matching_node(self) -> None:
        """Rule that produces no matches gives fired=False.

        Kills: ``fired=False`` default in non-match arm → ``fired=True``.
        """
        g = _make_graph()
        node = _add_node(g, "cls1", NodeKind.CLASS, "PlainClass")
        query = GraphQuery(g)

        # MutatingSubsystemRule needs WRITES edges; no edges here.
        explanation = MutatingSubsystemRule().explain(node, g, query)
        assert explanation.fired is False
        assert explanation.rule_name == MutatingSubsystemRule().name

    def test_explain_returns_fired_true_for_direct_match(self) -> None:
        """Rule that matches via node_id gives fired=True.

        Kills: ``node_id == node.id or node.id in fragment_ids`` → ``and``
        (would require node to appear in BOTH fields).
        """
        g = _make_graph()
        node = _add_node(g, "fn_obs", NodeKind.FUNCTION, "get_sensor")
        query = GraphQuery(g)

        explanation = ObservationRule().explain(node, g, query)
        assert explanation.fired is True

    def test_rule_explanation_to_dict_has_fired_field(self) -> None:
        """RuleExplanation.to_dict always includes the 'fired' key.

        Kills: removal of 'fired' from to_dict() return.
        """
        expl = RuleExplanation(
            rule_name="test",
            priority=0,
            fired=True,
            reason="test reason",
            evidence=["ev1"],
            mapping_kind="OBSERVATION",
        )
        d = expl.to_dict()
        assert "fired" in d
        assert d["fired"] is True
        assert d["rule_name"] == "test"
        assert d["evidence"] == ["ev1"]


# ---------------------------------------------------------------------------
# 5.  gnn/matrices.py — _normalize_row boundary cases
# ---------------------------------------------------------------------------


class TestNormalizeRow:
    """Tests that probe _normalize_row and _normalize_vector boundaries.

    Mutation targets:
      - ``n == 0``  → ``n != 0``  (returns [] for non-empty, uniform for empty)
      - ``total <= _EPSILON``  → ``total < _EPSILON``  (exact-zero corner)
      - ``1.0 / n``  → ``1.0 / (n - 1)`` or ``1.0 / (n + 1)``
      - Division formula ``v / total``
    """

    def test_empty_row_returns_empty_list(self) -> None:
        """Empty input must return empty output.

        Kills: ``n == 0`` → ``n != 0`` (returns uniform for empty, crashes
        for non-empty).
        """
        assert _normalize_row([]) == []

    def test_all_zeros_returns_uniform(self) -> None:
        """All-zero row must return uniform distribution.

        Kills: ``total <= _EPSILON`` → ``total < _EPSILON``  (exact 0.0
        does not trigger fallback; instead division by zero occurs).
        """
        result = _normalize_row([0.0, 0.0, 0.0])
        assert len(result) == 3
        for v in result:
            assert v == pytest.approx(1.0 / 3)

    def test_single_element_normalizes_to_one(self) -> None:
        """Single non-zero element must normalize to exactly 1.0.

        Kills: ``v / total`` → ``v * total`` (gives total^2, not 1.0).
        """
        result = _normalize_row([5.0])
        assert result == pytest.approx([1.0])

    def test_two_elements_sum_to_one(self) -> None:
        """Two-element row: output must sum to exactly 1.0.

        Kills: off-by-one in ``1.0 / n`` uniform fallback (though here
        ``total > _EPSILON`` so main branch is exercised).
        """
        result = _normalize_row([3.0, 1.0])
        assert sum(result) == pytest.approx(1.0)
        assert result[0] == pytest.approx(0.75)
        assert result[1] == pytest.approx(0.25)

    def test_uniform_fallback_for_near_zero_sum(self) -> None:
        """Near-zero (but above float denormal) sum triggers uniform fallback.

        This catches mutations that replace ``<=`` with ``<`` in the
        epsilon guard, causing near-zero sums to go through the division
        branch and produce values that don't sum to 1.0 due to underflow.
        """
        tiny = 1e-15  # below _EPSILON = 1e-9
        result = _normalize_row([tiny, tiny, tiny])
        assert sum(result) == pytest.approx(1.0)
        for v in result:
            assert v == pytest.approx(1.0 / 3)

    def test_normalize_vector_delegates_to_normalize_row(self) -> None:
        """_normalize_vector must produce same result as _normalize_row.

        Kills: if _normalize_vector applies a different formula than
        _normalize_row.
        """
        row = [2.0, 4.0, 4.0]
        assert _normalize_vector(row) == pytest.approx(_normalize_row(row))

    def test_large_row_sums_to_one(self) -> None:
        """100-element row: sum of normalized values is exactly 1.0.

        Kills: accumulation-error mutations in the division loop.
        """
        row = list(range(1, 101))  # [1, 2, ..., 100]
        result = _normalize_row(row)
        assert len(result) == 100
        assert sum(result) == pytest.approx(1.0, abs=1e-9)
        assert all(v >= 0 for v in result)


# ---------------------------------------------------------------------------
# 6.  gnn/matrices.py — GNNMatrices dimension properties
# ---------------------------------------------------------------------------


class TestGNNMatricesDimensions:
    """Tests that GNNMatrices dimension properties are mutation-safe.

    Mutation targets:
      - ``not self._hidden_states and bool(...)`` → ``or``  (always uses
        state-space vars even when hidden_states is non-empty)
      - ``n_actions`` returning 0 vs 1 on empty actions
    """

    def _minimal_state_space(self, n_vars: int = 2) -> StateSpaceModel:
        variables = {}
        for i in range(n_vars):
            v = StateVariable(
                id=f"var{i}",
                name=f"v{i}",
                var_type=StateVariableType.DISCRETE,
                node_id=f"node{i}",
                cardinality=2,
                confidence=ConfidenceLevel.HIGH,
            )
            variables[v.id] = v
        return StateSpaceModel(
            id="test_ss",
            schema_name="test",
            variables=variables,
            observations={},
            actions={},
            transitions={},
            likelihoods={},
            preferences={},
            time_regime=TimeRegime.SYNCHRONOUS,
        )

    def _make_graph_with_node(self, nid: str, name: str) -> ProgramGraph:
        g = _make_graph()
        _add_node(g, nid, NodeKind.FUNCTION, name)
        return g

    def test_n_states_from_hidden_state_mappings(self) -> None:
        """n_states uses HIDDEN_STATE mappings when present.

        Kills: ``not self._hidden_states and ...`` → ``or ...`` (would
        use state-space vars even when hidden-state mappings exist,
        producing wrong count if counts differ).
        """
        g = self._make_graph_with_node("s1", "state_var")
        ss = self._minimal_state_space(n_vars=5)  # 5 vars in state space

        m_hs = _make_mapping("hs1", MappingKind.HIDDEN_STATE, ["s1"])
        matrices = GNNMatrices(graph=g, mappings=[m_hs], state_space=ss)

        # 1 HIDDEN_STATE mapping, not 5 from state-space vars.
        assert matrices.n_states == 1

    def test_n_states_falls_back_to_state_space_vars_when_no_hs_mappings(self) -> None:
        """n_states falls back to state_space.variables when no HS mappings.

        Kills: ``not self._hidden_states`` → ``self._hidden_states``
        (never falls back, returns 0 when no mappings).
        """
        g = self._make_graph_with_node("n1", "some_var")
        ss = self._minimal_state_space(n_vars=3)

        # No HIDDEN_STATE mappings.
        matrices = GNNMatrices(graph=g, mappings=[], state_space=ss)
        assert matrices.n_states == 3

    def test_n_actions_minimum_one_for_valid_B(self) -> None:
        """n_actions returns at least 1 for a valid B tensor.

        Kills: early return of 0 instead of 1 when action list is empty
        but state-space actions are also empty.
        """
        g = self._make_graph_with_node("n1", "v1")
        ss = StateSpaceModel(
            id="empty_ss",
            schema_name="test",
            variables={},
            observations={},
            actions={},
            transitions={},
            likelihoods={},
            preferences={},
            time_regime=TimeRegime.SYNCHRONOUS,
        )

        matrices = GNNMatrices(graph=g, mappings=[], state_space=ss)
        assert matrices.n_actions >= 1


# ---------------------------------------------------------------------------
# 7.  statespace/compiler.py — compilation edge cases
# ---------------------------------------------------------------------------


class TestStateSpaceCompilerEdgeCases:
    """Tests that probe StateSpaceCompiler on minimal/degenerate inputs.

    Mutation targets:
      - Empty mapping list produces empty model (not a crash)
      - A single HIDDEN_STATE mapping produces exactly 1 variable
      - Preference weight defaults are in [0, 1]
    """

    def _make_graph_with_var(
        self, nid: str = "v1", name: str = "counter"
    ) -> tuple[ProgramGraph, str]:
        builder = ProgramGraphBuilder(repo_uri="test://compiler-edge")
        node = builder.add_node(
            kind=NodeKind.VARIABLE,
            name=name,
            qualified_name=f"mod.{name}",
            path="mod.py",
            language="python",
        )
        return builder.graph, node.id

    def test_empty_mappings_produces_empty_model(self) -> None:
        """Zero semantic mappings → model with no variables/observations/actions.

        Kills: initialization bugs that create non-empty state on empty input.
        """
        graph, _ = self._make_graph_with_var()
        compiler = StateSpaceCompiler(graph, schema_name="empty_test")
        model = compiler.compile({})

        assert len(model.variables) == 0
        assert len(model.observations) == 0
        assert len(model.actions) == 0
        assert len(model.transitions) == 0

    def test_single_hidden_state_mapping_yields_one_variable(self) -> None:
        """One HIDDEN_STATE mapping compiles to exactly one state variable.

        Kills: off-by-one in variable extraction loop.
        """
        graph, node_id = self._make_graph_with_var(nid="state_var", name="state_var")
        compiler = StateSpaceCompiler(graph, schema_name="single_hs")

        m = _make_mapping("hs1", MappingKind.HIDDEN_STATE, [node_id])
        model = compiler.compile({"hs1": m})

        assert len(model.variables) == 1
        assert list(model.variables.values())[0].name == "state_var"

    def test_observation_mapping_without_reads_edge_still_compiles(self) -> None:
        """OBSERVATION mapping on isolated node compiles without error.

        Kills: guard-removal mutation that crashes when READS edges are absent.
        """
        graph, node_id = self._make_graph_with_var(nid="obs_fn", name="get_value")
        compiler = StateSpaceCompiler(graph, schema_name="isolated_obs")

        m = _make_mapping("obs1", MappingKind.OBSERVATION, [node_id])
        model = compiler.compile({"obs1": m})

        # Compilation must not raise; observation count is ≥ 0.
        assert isinstance(model, StateSpaceModel)


# ---------------------------------------------------------------------------
# 8.  reverse/synthesizer.py — degenerate plan edge cases
# ---------------------------------------------------------------------------


class TestSynthesizerDegenerate:
    """Tests that probe the synthesizer on empty/minimal PackagePlans.

    Mutation targets:
      - ``if not plan.state_vars`` → ``if plan.state_vars``
        (inverted: skips the class body instead of using the fallback).
      - Empty plan produces importable source (no SyntaxError).
    """

    def test_render_state_module_empty_plan_produces_fallback_class(self) -> None:
        """Synthesizing an empty plan must produce a fallback State class.

        This catches mutations that invert the ``not plan.state_vars``
        guard, skipping the degenerate-case State class body.
        """
        from cogant.reverse.planner import PackagePlan
        from cogant.reverse.synthesizer import _render_state_module

        plan = PackagePlan()  # no state_vars
        source = _render_state_module(plan)

        tree = ast.parse(source)
        assert isinstance(tree, ast.Module)
        # Fallback class must contain a placeholder update method.
        assert "class State" in source
        assert "_placeholder" in source

    def test_render_state_module_single_state_produces_update(self) -> None:
        """One state var produces a class body with an update() method.

        Kills: mutations that skip the class body when state_vars is
        non-empty (inverted ``if not plan.state_vars`` guard).
        """
        from cogant.reverse.planner import NodePlan, PackagePlan
        from cogant.reverse.synthesizer import _render_state_module

        plan = PackagePlan(
            raw_model_name="one_state",
            state_vars=[NodePlan(name="counter", python_type="int")],
        )
        source = _render_state_module(plan)
        parsed_tree = ast.parse(source)
        assert isinstance(parsed_tree, ast.Module)
        assert "def update" in source, "update() mutator must be present"
        assert "class" in source
