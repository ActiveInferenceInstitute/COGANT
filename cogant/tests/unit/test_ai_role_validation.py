"""Tests validating Active Inference role assignment quality.

These are qualitative validation tests - they verify that the translation
engine assigns sensible semantic roles to known code patterns, and that
end-to-end runs over the control-positive fixtures produce Markov-blanket
partitions with all four Active Inference roles represented.

Each test deliberately targets a small, hand-built program graph so that
the assertion reflects the rule under study (ObservationRule, ActionRule,
etc.) rather than the behaviour of the full rule stack.
"""

from __future__ import annotations

import logging
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure the cogant package and examples directory are importable
_REPO_ROOT = Path(__file__).parent.parent.parent  # tests/unit -> tests -> cogant/
_PY = _REPO_ROOT / "py"
_EX = _REPO_ROOT / "examples"
for _p in (_PY, _EX):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from cogant.graph.builder import ProgramGraphBuilder
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.semantic import MappingKind
from cogant.translate.engine import TranslationEngine
from cogant.translate.rules.resilience import RetryPatternRule
from cogant.translate.rules.semantic import (
    ActionRule,
    ObservationRule,
    PolicyRule,
    PreferenceRule,
)
from cogant.translate.rules.structural import (
    MutatingSubsystemRule,
    ReadOnlyInputRule,
)

# ---------------------------------------------------------------------------
# Micro-fixture helpers
# ---------------------------------------------------------------------------


def _fresh_builder(uri: str = "test://ai-role-validation") -> ProgramGraphBuilder:
    return ProgramGraphBuilder(repo_uri=uri)


def _apply_rule(graph, rule) -> dict:
    """Run a single rule against ``graph`` and return ``{node_id: kind}``."""
    engine = TranslationEngine()
    engine.register_rule(rule)
    mappings = engine.translate(graph)
    return {
        mapping.graph_fragment_node_ids[0]: mapping.kind
        for mapping in mappings
        if mapping.graph_fragment_node_ids
    }


# ---------------------------------------------------------------------------
# ObservationRule: pure getters -> OBSERVATION
# ---------------------------------------------------------------------------


def test_pure_getter_maps_to_observation() -> None:
    """A function named ``get_*`` that only reads should become an OBSERVATION."""
    builder = _fresh_builder()
    fn = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="get_display",
        qualified_name="calc.get_display",
        path="calc.py",
        language="Python",
    )
    state = builder.add_node(
        kind=NodeKind.VARIABLE,
        name="display",
        qualified_name="calc.display",
        path="calc.py",
        language="Python",
    )
    builder.add_edge(fn.id, state.id, EdgeKind.READS)

    kinds = _apply_rule(builder.graph, ObservationRule())
    assert fn.id in kinds, "getter function must receive a mapping"
    assert kinds[fn.id] == MappingKind.OBSERVATION


def test_read_only_function_without_keyword_still_observation() -> None:
    """A read-only function should become OBSERVATION even without a keyword."""
    builder = _fresh_builder()
    fn = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="peek_internal",  # no "get/read/..." keyword
        qualified_name="mod.peek_internal",
        path="mod.py",
        language="Python",
    )
    var = builder.add_node(
        kind=NodeKind.VARIABLE,
        name="counter",
        qualified_name="mod.counter",
        path="mod.py",
        language="Python",
    )
    builder.add_edge(fn.id, var.id, EdgeKind.READS)

    kinds = _apply_rule(builder.graph, ObservationRule())
    assert kinds.get(fn.id) == MappingKind.OBSERVATION


# ---------------------------------------------------------------------------
# ActionRule: mutating methods with action keywords -> ACTION
# ---------------------------------------------------------------------------


def test_mutating_setter_maps_to_action() -> None:
    """A ``set_*`` method with a WRITES edge should become an ACTION."""
    builder = _fresh_builder()
    fn = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="set_value",
        qualified_name="mod.set_value",
        path="mod.py",
        language="Python",
    )
    var = builder.add_node(
        kind=NodeKind.VARIABLE,
        name="state",
        qualified_name="mod.state",
        path="mod.py",
        language="Python",
    )
    builder.add_edge(fn.id, var.id, EdgeKind.WRITES)

    kinds = _apply_rule(builder.graph, ActionRule())
    assert fn.id in kinds
    assert kinds[fn.id] == MappingKind.ACTION


def test_process_method_maps_to_action() -> None:
    """A method named ``process_*`` should also become an ACTION."""
    builder = _fresh_builder()
    m = builder.add_node(
        kind=NodeKind.METHOD,
        name="process_request",
        qualified_name="app.App.process_request",
        path="app.py",
        language="Python",
    )
    # Even without WRITES, keyword match is sufficient for ActionRule
    kinds = _apply_rule(builder.graph, ActionRule())
    assert kinds.get(m.id) == MappingKind.ACTION


# ---------------------------------------------------------------------------
# PolicyRule: handler/controller classes -> POLICY
# ---------------------------------------------------------------------------


def test_handler_class_maps_to_policy() -> None:
    """A class whose name contains ``handler`` should become POLICY."""
    builder = _fresh_builder()
    cls = builder.add_node(
        kind=NodeKind.CLASS,
        name="EventHandler",
        qualified_name="pipeline.EventHandler",
        path="pipeline.py",
        language="Python",
    )
    kinds = _apply_rule(builder.graph, PolicyRule())
    assert kinds.get(cls.id) == MappingKind.POLICY


# ---------------------------------------------------------------------------
# ReadOnlyInputRule: modules with only READS -> OBSERVATION
# ---------------------------------------------------------------------------


def test_readonly_module_maps_to_observation() -> None:
    """A module whose only outbound edges are READS should become OBSERVATION."""
    builder = _fresh_builder()
    module = builder.add_node(
        kind=NodeKind.MODULE,
        name="sensors",
        qualified_name="sensors",
        path="sensors.py",
        language="Python",
    )
    var = builder.add_node(
        kind=NodeKind.VARIABLE,
        name="temp",
        qualified_name="sensors.temp",
        path="sensors.py",
        language="Python",
    )
    builder.add_edge(module.id, var.id, EdgeKind.READS)

    kinds = _apply_rule(builder.graph, ReadOnlyInputRule())
    assert module.id in kinds
    assert kinds[module.id] == MappingKind.OBSERVATION


# ---------------------------------------------------------------------------
# MutatingSubsystemRule: classes touched by WRITES -> HIDDEN_STATE
# ---------------------------------------------------------------------------


def test_mutating_class_maps_to_hidden_state() -> None:
    """A class with a WRITES edge should become HIDDEN_STATE."""
    builder = _fresh_builder()
    cls = builder.add_node(
        kind=NodeKind.CLASS,
        name="Calculator",
        qualified_name="calc.Calculator",
        path="calc.py",
        language="Python",
    )
    method = builder.add_node(
        kind=NodeKind.METHOD,
        name="clear",
        qualified_name="calc.Calculator.clear",
        path="calc.py",
        language="Python",
    )
    builder.add_edge(method.id, cls.id, EdgeKind.WRITES)

    kinds = _apply_rule(builder.graph, MutatingSubsystemRule())
    assert cls.id in kinds
    assert kinds[cls.id] == MappingKind.HIDDEN_STATE


# ---------------------------------------------------------------------------
# RetryPatternRule: retry/backoff/circuit/timeout keywords -> POLICY
# ---------------------------------------------------------------------------


def test_retry_function_maps_to_policy() -> None:
    """A function whose name includes ``retry`` should become POLICY."""
    builder = _fresh_builder()
    fn = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="retry_fetch",
        qualified_name="net.retry_fetch",
        path="net.py",
        language="Python",
        metadata={"keywords": ["retry", "backoff"]},
    )
    kinds = _apply_rule(builder.graph, RetryPatternRule())
    assert kinds.get(fn.id) == MappingKind.POLICY


# ---------------------------------------------------------------------------
# PreferenceRule: assertions / validators -> CONSTRAINT
# ---------------------------------------------------------------------------


def test_assertion_function_maps_to_constraint() -> None:
    """An ``assert_*`` method should become a CONSTRAINT/preference."""
    builder = _fresh_builder()
    fn = builder.add_node(
        kind=NodeKind.METHOD,
        name="assert_display",
        qualified_name="calc.Calculator.assert_display",
        path="calc.py",
        language="Python",
    )
    kinds = _apply_rule(builder.graph, PreferenceRule())
    assert kinds.get(fn.id) == MappingKind.CONSTRAINT


# ---------------------------------------------------------------------------
# End-to-end: calculator fixture produces expected role distributions
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def calculator_pipeline():
    """Run the real orchestrator pipeline against the calculator fixture.

    Returns a tuple ``(graph, semantic_mappings_dict, markov_blanket)``.
    Module-scoped so we pay the ingest/parse cost once.
    """
    logging.disable(logging.CRITICAL)
    from orchestrate_roundtrip import RoundtripOrchestrator  # type: ignore

    from cogant.markov.extractor import MarkovBlanketExtractor

    repo = _EX / "control_positive" / "calculator"
    with tempfile.TemporaryDirectory() as d:
        orch = RoundtripOrchestrator(repo, Path(d))
        snapshot = orch._ingest_repo()
        parsed = orch._parse_files(snapshot)
        symtabs = orch._extract_symbols(parsed)
        imports = orch._analyze_imports(snapshot)
        calls = orch._build_call_graph(snapshot)
        graph = orch._build_program_graph(snapshot, parsed, symtabs, imports, calls)
        mappings = orch._apply_translation_rules(graph)
        blanket = MarkovBlanketExtractor(graph).extract(strategy="auto")
    return graph, mappings, blanket


def test_calculator_produces_multiple_role_kinds(calculator_pipeline) -> None:
    """Calculator fixture must surface multiple AI roles at once."""
    _, mappings, _ = calculator_pipeline
    kinds = {m.kind for m in mappings.values()}
    # At minimum we expect observation + some state/action presence
    assert MappingKind.OBSERVATION in kinds
    # Either class-level HIDDEN_STATE or method-level ACTION must appear
    assert MappingKind.HIDDEN_STATE in kinds or MappingKind.ACTION in kinds


def test_calculator_getters_are_observations(calculator_pipeline) -> None:
    """``get_display`` and ``get_history`` should be OBSERVATION."""
    graph, mappings, _ = calculator_pipeline
    observation_names = {
        graph.get_node(m.graph_fragment_node_ids[0]).name
        for m in mappings.values()
        if m.kind == MappingKind.OBSERVATION and m.graph_fragment_node_ids
    }
    assert "get_display" in observation_names
    assert "get_history" in observation_names


def test_calculator_has_constraint(calculator_pipeline) -> None:
    """``assert_*`` methods in calculator should map to CONSTRAINT."""
    graph, mappings, _ = calculator_pipeline
    constraint_names = {
        graph.get_node(m.graph_fragment_node_ids[0]).name
        for m in mappings.values()
        if m.kind == MappingKind.CONSTRAINT and m.graph_fragment_node_ids
    }
    # At least one of the assertion methods should surface
    assert constraint_names & {"assert_display", "assert_history_length"}


def test_calculator_markov_blanket_partitions_graph(calculator_pipeline) -> None:
    """The Markov blanket must cover every node exactly once."""
    graph, _, blanket = calculator_pipeline
    total = len(graph.nodes)
    assert total > 0
    stats = blanket.stats
    assert stats["total_nodes"] == total
    covered = (
        stats["internal_count"]
        + stats["sensory_count"]
        + stats["active_count"]
        + stats["external_count"]
    )
    assert covered == total, f"blanket must partition all nodes, got {covered}/{total}"
    # Calculator is a small, cohesive class -> most nodes should be internal
    assert stats["internal_count"] >= 1
    # At least one boundary node (the class or its methods) must exist
    assert (stats["sensory_count"] + stats["active_count"]) >= 1


def test_calculator_blanket_roles_are_consistent(calculator_pipeline) -> None:
    """Every node id in the graph must map to exactly one BlanketRole."""
    graph, _, blanket = calculator_pipeline
    role_ids = (
        blanket.internal_ids | blanket.sensory_ids | blanket.active_ids | blanket.external_ids
    )
    assert role_ids == set(graph.nodes.keys())
    # Mutually exclusive
    assert not (blanket.internal_ids & blanket.sensory_ids)
    assert not (blanket.internal_ids & blanket.active_ids)
    assert not (blanket.internal_ids & blanket.external_ids)
    assert not (blanket.sensory_ids & blanket.active_ids)


# ---------------------------------------------------------------------------
# Cross-fixture coverage sanity (event_pipeline / flask_mini)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture_name", ["event_pipeline", "flask_mini"])
def test_other_fixtures_produce_policy_mappings(fixture_name: str) -> None:
    """Handler/middleware-heavy fixtures should surface POLICY mappings."""
    logging.disable(logging.CRITICAL)
    from orchestrate_roundtrip import RoundtripOrchestrator  # type: ignore

    repo = _EX / "control_positive" / fixture_name
    with tempfile.TemporaryDirectory() as d:
        orch = RoundtripOrchestrator(repo, Path(d))
        snapshot = orch._ingest_repo()
        parsed = orch._parse_files(snapshot)
        symtabs = orch._extract_symbols(parsed)
        imports = orch._analyze_imports(snapshot)
        calls = orch._build_call_graph(snapshot)
        graph = orch._build_program_graph(snapshot, parsed, symtabs, imports, calls)
        mappings = orch._apply_translation_rules(graph)

    kinds = {m.kind for m in mappings.values()}
    # These fixtures all contain Handler/Controller/Middleware classes
    assert MappingKind.POLICY in kinds, (
        f"{fixture_name} should surface at least one POLICY mapping; got {kinds}"
    )
    # And they all contain mutating methods, so ACTION should also appear
    assert MappingKind.ACTION in kinds, (
        f"{fixture_name} should surface at least one ACTION mapping; got {kinds}"
    )
