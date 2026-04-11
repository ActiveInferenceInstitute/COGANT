"""Unit tests for :class:`cogant.statespace.compiler.StateSpaceCompiler`.

Builds real :class:`ProgramGraph` instances and genuine
:class:`SemanticMapping` objects, then exercises the full compilation
pipeline (variables + observations + actions + transitions + likelihoods
+ preferences) without any mocks.

The fixtures mirror what the COGANT pipeline produces for two reference
examples:

- ``calculator_graph``  — a small class with hidden counters, an
  observation channel, and action methods plus a test assertion.
- ``event_pipeline_graph`` — an EventBus/handler topology used to
  exercise POLICY/ACTION folding, OBSERVATION mappings, and fan-out.
"""

from __future__ import annotations

import pytest

from cogant.graph.builder import ProgramGraphBuilder
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import (
    MappingKind,
    ProvenanceRecord,
    SemanticMapping,
)
from cogant.statespace.compiler import (
    Action,
    Likelihood,
    ObservationModality,
    Preference,
    StateSpaceCompiler,
    StateSpaceModel,
    Transition,
)
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import (
    ConfidenceLevel,
    StateVariable,
    StateVariableType,
)

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------- fixtures


@pytest.fixture
def calculator_graph() -> tuple[ProgramGraph, dict[str, str]]:
    """Build a small calculator-shaped graph.

    Returns ``(graph, ids)`` where ``ids`` maps symbolic names to the
    builder-generated node ids. This gives tests stable references
    without hard-coding UUIDs.
    """
    builder = ProgramGraphBuilder(repo_uri="test://calculator")

    module = builder.add_node(
        kind=NodeKind.MODULE,
        name="calculator",
        qualified_name="calculator",
        path="calculator.py",
        language="python",
    )
    cls = builder.add_node(
        kind=NodeKind.CLASS,
        name="Calculator",
        qualified_name="calculator.Calculator",
        path="calculator.py",
        language="python",
        metadata={},
    )
    display = builder.add_node(
        kind=NodeKind.VARIABLE,
        name="display",
        qualified_name="calculator.Calculator.display",
        path="calculator.py",
        language="python",
        metadata={"type_hint": "float", "cardinality": 100},
    )
    counter = builder.add_node(
        kind=NodeKind.VARIABLE,
        name="accumulator",
        qualified_name="calculator.Calculator.accumulator",
        path="calculator.py",
        language="python",
        metadata={"type_hint": "int", "cardinality": 10},
    )
    active = builder.add_node(
        kind=NodeKind.VARIABLE,
        name="is_active",
        qualified_name="calculator.Calculator.is_active",
        path="calculator.py",
        language="python",
        metadata={"type_hint": "bool"},
    )

    input_digit = builder.add_node(
        kind=NodeKind.METHOD,
        name="input_digit",
        qualified_name="calculator.Calculator.input_digit",
        path="calculator.py",
        language="python",
        metadata={"parameters": ["self", "digit"]},
    )
    clear = builder.add_node(
        kind=NodeKind.METHOD,
        name="clear",
        qualified_name="calculator.Calculator.clear",
        path="calculator.py",
        language="python",
        metadata={"parameters": ["self"]},
    )
    get_display = builder.add_node(
        kind=NodeKind.METHOD,
        name="get_display",
        qualified_name="calculator.Calculator.get_display",
        path="calculator.py",
        language="python",
        metadata={"type_hint": "float"},
    )
    assertion = builder.add_node(
        kind=NodeKind.ASSERTION,
        name="assert_display_nonneg",
        qualified_name="tests.test_calculator.assert_display_nonneg",
        path="tests/test_calculator.py",
        language="python",
        metadata={"expression": "display >= 0"},
    )

    # Containment + CONTAINS wiring
    builder.add_edge(module.id, cls.id, EdgeKind.CONTAINS)
    for child in (display, counter, active, input_digit, clear, get_display):
        builder.add_edge(cls.id, child.id, EdgeKind.CONTAINS)

    # Action effects: input_digit writes display; clear writes counter
    builder.add_edge(input_digit.id, display.id, EdgeKind.WRITES)
    builder.add_edge(clear.id, counter.id, EdgeKind.WRITES)
    builder.add_edge(clear.id, active.id, EdgeKind.WRITES)

    # Observation reads display
    builder.add_edge(get_display.id, display.id, EdgeKind.READS)

    # Call graph
    builder.add_edge(input_digit.id, get_display.id, EdgeKind.CALLS)

    graph = builder.finalize()
    ids = {
        "module": module.id,
        "class": cls.id,
        "display": display.id,
        "counter": counter.id,
        "active": active.id,
        "input_digit": input_digit.id,
        "clear": clear.id,
        "get_display": get_display.id,
        "assertion": assertion.id,
    }
    return graph, ids


@pytest.fixture
def calculator_mappings(calculator_graph) -> dict[str, SemanticMapping]:
    """Semantic mappings matching :func:`calculator_graph`."""
    _, ids = calculator_graph
    prov = [ProvenanceRecord(source="static_analysis", confidence=0.9)]

    mappings = [
        SemanticMapping(
            id="map:display",
            kind=MappingKind.HIDDEN_STATE,
            graph_fragment_node_ids=[ids["display"]],
            semantic_label="display",
            description="current display value",
            confidence_score=0.9,
            provenance=prov,
        ),
        SemanticMapping(
            id="map:counter",
            kind=MappingKind.HIDDEN_STATE,
            graph_fragment_node_ids=[ids["counter"]],
            semantic_label="accumulator",
            description="integer accumulator",
            confidence_score=0.85,
            provenance=prov,
        ),
        SemanticMapping(
            id="map:active",
            kind=MappingKind.HIDDEN_STATE,
            graph_fragment_node_ids=[ids["active"]],
            semantic_label="is_active",
            description="calculator active flag",
            confidence_score=0.92,
            provenance=prov,
        ),
        SemanticMapping(
            id="map:obs_display",
            kind=MappingKind.OBSERVATION,
            graph_fragment_node_ids=[ids["get_display"]],
            semantic_label="display_obs",
            description="log of display readings",
            confidence_score=0.88,
            provenance=prov,
        ),
        SemanticMapping(
            id="map:act_input",
            kind=MappingKind.ACTION,
            graph_fragment_node_ids=[ids["input_digit"]],
            semantic_label="input_digit",
            description="press a digit button",
            confidence_score=0.82,
            provenance=prov,
        ),
        SemanticMapping(
            id="map:act_clear",
            kind=MappingKind.ACTION,
            graph_fragment_node_ids=[ids["clear"]],
            semantic_label="clear",
            description="clear calculator state",
            confidence_score=0.78,
            provenance=prov,
        ),
        SemanticMapping(
            id="map:pref_display",
            kind=MappingKind.CONSTRAINT,
            graph_fragment_node_ids=[ids["assertion"]],
            semantic_label="display_nonnegative",
            description="display must stay non-negative",
            confidence_score=0.95,
            provenance=prov,
        ),
    ]
    return {m.id: m for m in mappings}


@pytest.fixture
def event_pipeline_graph() -> tuple[ProgramGraph, dict[str, str]]:
    """An event bus with a POLICY (retry handler) and multiple handlers."""
    builder = ProgramGraphBuilder(repo_uri="test://event-pipeline")

    module = builder.add_node(
        kind=NodeKind.MODULE,
        name="pipeline",
        qualified_name="pipeline",
        path="pipeline.py",
        language="python",
    )
    bus = builder.add_node(
        kind=NodeKind.CLASS,
        name="EventBus",
        qualified_name="pipeline.EventBus",
        path="pipeline.py",
        language="python",
    )
    publish = builder.add_node(
        kind=NodeKind.METHOD,
        name="publish",
        qualified_name="pipeline.EventBus.publish",
        path="pipeline.py",
        language="python",
        metadata={"is_async": True, "parameters": ["self", "event"]},
    )
    log_handler = builder.add_node(
        kind=NodeKind.METHOD,
        name="handle_log",
        qualified_name="pipeline.LoggingEventHandler.handle_log",
        path="pipeline.py",
        language="python",
        metadata={"type_hint": "str"},
    )
    retry_handler = builder.add_node(
        kind=NodeKind.METHOD,
        name="retry_handler",
        qualified_name="pipeline.RetryableEventHandler.retry_handler",
        path="pipeline.py",
        language="python",
        metadata={"has_retry": True, "max_retries": 5, "backoff_strategy": "linear"},
    )
    event_state = builder.add_node(
        kind=NodeKind.VARIABLE,
        name="event_count",
        qualified_name="pipeline.EventBus.event_count",
        path="pipeline.py",
        language="python",
        metadata={"type_hint": "int", "cardinality": 4},
    )

    builder.add_edge(module.id, bus.id, EdgeKind.CONTAINS)
    builder.add_edge(bus.id, publish.id, EdgeKind.CONTAINS)
    builder.add_edge(bus.id, event_state.id, EdgeKind.CONTAINS)
    builder.add_edge(publish.id, event_state.id, EdgeKind.WRITES)
    builder.add_edge(publish.id, log_handler.id, EdgeKind.TRIGGERS)
    builder.add_edge(publish.id, retry_handler.id, EdgeKind.TRIGGERS)

    graph = builder.finalize()
    ids = {
        "module": module.id,
        "bus": bus.id,
        "publish": publish.id,
        "log_handler": log_handler.id,
        "retry_handler": retry_handler.id,
        "event_state": event_state.id,
    }
    return graph, ids


@pytest.fixture
def event_pipeline_mappings(event_pipeline_graph) -> dict[str, SemanticMapping]:
    """Mappings that exercise POLICY folding into actions and OBSERVATION likelihoods."""
    _, ids = event_pipeline_graph
    prov = [ProvenanceRecord(source="static_analysis", confidence=0.85)]

    mappings = [
        SemanticMapping(
            id="evt:hidden_count",
            kind=MappingKind.HIDDEN_STATE,
            graph_fragment_node_ids=[ids["event_state"]],
            semantic_label="event_count",
            description="integer count",
            confidence_score=0.9,
            provenance=prov,
        ),
        SemanticMapping(
            id="evt:act_publish",
            kind=MappingKind.ACTION,
            graph_fragment_node_ids=[ids["publish"]],
            semantic_label="publish",
            description="publish an event",
            confidence_score=0.9,
            provenance=prov,
        ),
        SemanticMapping(
            id="evt:policy_retry",
            kind=MappingKind.POLICY,
            graph_fragment_node_ids=[ids["retry_handler"]],
            semantic_label="retry_policy",
            description="retry-on-failure policy",
            confidence_score=0.8,
            provenance=prov,
        ),
        SemanticMapping(
            id="evt:obs_log",
            kind=MappingKind.OBSERVATION,
            graph_fragment_node_ids=[ids["log_handler"]],
            semantic_label="log_channel",
            description="log stream of events",
            confidence_score=0.85,
            provenance=prov,
        ),
    ]
    return {m.id: m for m in mappings}


# ------------------------------------------------------------- basic contract


class TestCompilerBasics:
    """Sanity tests around constructor and empty-mapping compilation."""

    def test_constructor_stores_graph_and_schema(self, calculator_graph) -> None:
        graph, _ = calculator_graph
        compiler = StateSpaceCompiler(graph, schema_name="calc")
        assert compiler.graph is graph
        assert compiler.schema_name == "calc"

    def test_compile_with_empty_mappings(self, calculator_graph) -> None:
        graph, _ = calculator_graph
        compiler = StateSpaceCompiler(graph, schema_name="empty")
        model = compiler.compile({})
        assert isinstance(model, StateSpaceModel)
        assert model.schema_name == "empty"
        assert model.variables == {}
        assert model.observations == {}
        assert model.actions == {}
        assert model.transitions == {}
        assert model.likelihoods == {}
        assert model.preferences == {}
        assert isinstance(model.time_regime, TimeRegime)
        assert model.metadata["variable_count"] == 0


# ---------------------------------------------------- calculator compilation


class TestCompileCalculator:
    """Full-pipeline compile on the calculator fixture."""

    def test_variables_extracted(self, calculator_graph, calculator_mappings) -> None:
        graph, ids = calculator_graph
        compiler = StateSpaceCompiler(graph, schema_name="calc")
        model = compiler.compile(calculator_mappings)

        assert len(model.variables) == 3
        display_var = model.variables[f"var_{ids['display']}"]
        assert isinstance(display_var, StateVariable)
        assert display_var.var_type is StateVariableType.CONTINUOUS
        assert display_var.is_discrete is False

        counter_var = model.variables[f"var_{ids['counter']}"]
        assert counter_var.var_type is StateVariableType.DISCRETE
        assert counter_var.cardinality == 10

        flag_var = model.variables[f"var_{ids['active']}"]
        assert flag_var.var_type is StateVariableType.BOOLEAN
        assert flag_var.domain == [False, True]

    def test_observation_extracted(self, calculator_graph, calculator_mappings) -> None:
        graph, ids = calculator_graph
        compiler = StateSpaceCompiler(graph, schema_name="calc")
        model = compiler.compile(calculator_mappings)

        obs_id = f"obs_{ids['get_display']}"
        assert obs_id in model.observations
        obs = model.observations[obs_id]
        assert isinstance(obs, ObservationModality)
        assert obs.name == "display_obs"
        # description contains "log" so modality type should be log
        assert obs.modality_type == "log"
        assert obs.source_node_id == ids["get_display"]

    def test_actions_from_action_mappings(
        self, calculator_graph, calculator_mappings
    ) -> None:
        graph, ids = calculator_graph
        compiler = StateSpaceCompiler(graph, schema_name="calc")
        model = compiler.compile(calculator_mappings)

        assert f"act_{ids['input_digit']}" in model.actions
        assert f"act_{ids['clear']}" in model.actions
        input_action = model.actions[f"act_{ids['input_digit']}"]
        assert isinstance(input_action, Action)
        assert input_action.name == "input_digit"
        assert input_action.controller_id == ids["input_digit"]
        # effects should reference the WRITES target (display)
        assert any("display" in eff or ids["display"] in eff for eff in input_action.effects)
        # parameters are sourced from the function metadata, normalized to a
        # dict that drops the implicit ``self``.
        assert input_action.parameters == {"digit": None}
        # preconditions should note the digit parameter and Calculator instance
        assert any("digit" in p for p in input_action.preconditions)

    def test_transitions_for_each_action(self, calculator_graph, calculator_mappings) -> None:
        graph, ids = calculator_graph
        compiler = StateSpaceCompiler(graph, schema_name="calc")
        model = compiler.compile(calculator_mappings)

        assert len(model.transitions) == len(model.actions)
        for action_id in model.actions:
            trans_id = f"trans_{action_id}"
            assert trans_id in model.transitions
            trans = model.transitions[trans_id]
            assert isinstance(trans, Transition)
            assert trans.action_id == action_id

    def test_transition_source_and_target_states(
        self, calculator_graph, calculator_mappings
    ) -> None:
        graph, ids = calculator_graph
        compiler = StateSpaceCompiler(graph, schema_name="calc")
        model = compiler.compile(calculator_mappings)

        input_trans = model.transitions[f"trans_act_{ids['input_digit']}"]
        display_var_id = f"var_{ids['display']}"
        # input_digit writes display, so target state should be "post"
        assert input_trans.target_state.get(display_var_id) == "post"
        assert input_trans.source_state.get(display_var_id) == "pre"

        clear_trans = model.transitions[f"trans_act_{ids['clear']}"]
        counter_var_id = f"var_{ids['counter']}"
        active_var_id = f"var_{ids['active']}"
        assert clear_trans.target_state.get(counter_var_id) == "post"
        assert clear_trans.target_state.get(active_var_id) == "post"

    def test_likelihoods_per_variable(self, calculator_graph, calculator_mappings) -> None:
        graph, ids = calculator_graph
        compiler = StateSpaceCompiler(graph, schema_name="calc")
        model = compiler.compile(calculator_mappings)

        # One likelihood per hidden-state variable + one per observation
        # mapping node.
        like_display = model.likelihoods[f"like_var_{ids['display']}"]
        assert isinstance(like_display, Likelihood)
        assert like_display.distribution_type == "gaussian"
        assert "mean" in like_display.parameters and "variance" in like_display.parameters

        like_counter = model.likelihoods[f"like_var_{ids['counter']}"]
        assert like_counter.distribution_type == "categorical"

        like_flag = model.likelihoods[f"like_var_{ids['active']}"]
        assert like_flag.distribution_type == "bernoulli"
        assert like_flag.parameters == {"p": 0.5}

        obs_like = model.likelihoods[f"like_obs_{ids['get_display']}"]
        # get_display has type_hint "float" -> gaussian
        assert obs_like.distribution_type == "gaussian"

    def test_preferences_from_constraint(
        self, calculator_graph, calculator_mappings
    ) -> None:
        graph, ids = calculator_graph
        compiler = StateSpaceCompiler(graph, schema_name="calc")
        model = compiler.compile(calculator_mappings)

        assert len(model.preferences) == 1
        pref = next(iter(model.preferences.values()))
        assert isinstance(pref, Preference)
        assert pref.name == "display_nonnegative"
        # Weight comes from confidence 0.95
        assert pref.weight == pytest.approx(0.95)
        # Expression pulled from the assertion's metadata["expression"]
        assert pref.expression == "display >= 0"

    def test_metadata_counts(self, calculator_graph, calculator_mappings) -> None:
        graph, _ = calculator_graph
        compiler = StateSpaceCompiler(graph, schema_name="calc")
        model = compiler.compile(calculator_mappings)
        meta = model.metadata
        assert meta["variable_count"] == len(model.variables)
        assert meta["observation_count"] == len(model.observations)
        assert meta["action_count"] == len(model.actions)
        assert meta["transition_count"] == len(model.transitions)


# --------------------------------------------------------- event pipeline


class TestCompileEventPipeline:
    """POLICY and fan-out behaviours on the event bus fixture."""

    def test_policy_mapping_becomes_action(
        self, event_pipeline_graph, event_pipeline_mappings
    ) -> None:
        graph, ids = event_pipeline_graph
        compiler = StateSpaceCompiler(graph, schema_name="events")
        model = compiler.compile(event_pipeline_mappings)

        # Both the ACTION publish and POLICY retry_handler become actions.
        assert f"act_{ids['publish']}" in model.actions
        assert f"act_{ids['retry_handler']}" in model.actions
        assert model.actions[f"act_{ids['retry_handler']}"].name == "retry_policy"

    def test_policy_not_double_counted_as_preference(
        self, event_pipeline_graph, event_pipeline_mappings
    ) -> None:
        graph, _ = event_pipeline_graph
        compiler = StateSpaceCompiler(graph, schema_name="events")
        model = compiler.compile(event_pipeline_mappings)
        # No CONSTRAINT/PREFERENCE mappings in this fixture -> zero preferences.
        assert model.preferences == {}

    def test_observation_mapping_generates_likelihood(
        self, event_pipeline_graph, event_pipeline_mappings
    ) -> None:
        graph, ids = event_pipeline_graph
        compiler = StateSpaceCompiler(graph, schema_name="events")
        model = compiler.compile(event_pipeline_mappings)

        obs_like_id = f"like_obs_{ids['log_handler']}"
        assert obs_like_id in model.likelihoods
        # log_handler has type_hint "str" -> categorical
        assert model.likelihoods[obs_like_id].distribution_type == "categorical"

    def test_hidden_state_variable_flagged_observable(
        self, event_pipeline_graph, event_pipeline_mappings
    ) -> None:
        graph, ids = event_pipeline_graph
        # Add an OBSERVATION mapping pointing at the hidden state node, then
        # recompile and check observable==True.
        event_pipeline_mappings["evt:obs_count"] = SemanticMapping(
            id="evt:obs_count",
            kind=MappingKind.OBSERVATION,
            graph_fragment_node_ids=[ids["event_state"]],
            semantic_label="event_count_obs",
            description="metric stream of counts",
            confidence_score=0.8,
        )
        compiler = StateSpaceCompiler(graph, schema_name="events")
        model = compiler.compile(event_pipeline_mappings)

        var = model.variables[f"var_{ids['event_state']}"]
        assert var.observable is True

    def test_publish_transition_triggered_state(
        self, event_pipeline_graph, event_pipeline_mappings
    ) -> None:
        graph, ids = event_pipeline_graph
        compiler = StateSpaceCompiler(graph, schema_name="events")
        model = compiler.compile(event_pipeline_mappings)

        trans = model.transitions[f"trans_act_{ids['publish']}"]
        event_var_id = f"var_{ids['event_state']}"
        assert trans.target_state.get(event_var_id) == "post"
        # publish has two outgoing TRIGGERS edges; triggered_by should
        # not be None because we populate it from CALLS/TRIGGERS analysis.
        assert trans.triggered_by is not None


# ---------------------------------------------- compiler helper coverage


class TestCompilerHelpers:
    """Directly exercise smaller helpers so they do not rot over time."""

    def test_infer_modality_type(self, calculator_graph) -> None:
        graph, ids = calculator_graph
        compiler = StateSpaceCompiler(graph, schema_name="calc")
        node = graph.get_node(ids["get_display"])

        log_map = SemanticMapping(
            id="m1",
            kind=MappingKind.OBSERVATION,
            graph_fragment_node_ids=[node.id],
            semantic_label="display_obs",
            description="a log of events",
        )
        assert compiler._infer_modality_type(node, log_map) == "log"

        metric_map = SemanticMapping(
            id="m2",
            kind=MappingKind.OBSERVATION,
            graph_fragment_node_ids=[node.id],
            semantic_label="counter_metric",
            description="a metric feed",
        )
        assert compiler._infer_modality_type(node, metric_map) == "metric"

        event_map = SemanticMapping(
            id="m3",
            kind=MappingKind.OBSERVATION,
            graph_fragment_node_ids=[node.id],
            semantic_label="event_stream",
            description="event-driven",
        )
        assert compiler._infer_modality_type(node, event_map) == "event"

        sensor_map = SemanticMapping(
            id="m4",
            kind=MappingKind.OBSERVATION,
            graph_fragment_node_ids=[node.id],
            semantic_label="temperature_sensor",
            description="sensor reading",
        )
        assert compiler._infer_modality_type(node, sensor_map) == "sensor"

        generic_map = SemanticMapping(
            id="m5",
            kind=MappingKind.OBSERVATION,
            graph_fragment_node_ids=[node.id],
            semantic_label="output",
            description="generic",
        )
        assert compiler._infer_modality_type(node, generic_map) == "generic"

    def test_infer_observation_distribution(self, calculator_graph) -> None:
        graph, _ = calculator_graph
        compiler = StateSpaceCompiler(graph, schema_name="calc")

        class _N:
            def __init__(self, hint):
                self.metadata = {"type_hint": hint}

        assert compiler._infer_observation_distribution(_N("bool")) == "bernoulli"
        assert compiler._infer_observation_distribution(_N("int")) == "categorical"
        assert compiler._infer_observation_distribution(_N("float")) == "gaussian"
        assert compiler._infer_observation_distribution(_N("str")) == "categorical"
        assert compiler._infer_observation_distribution(_N("list[int]")) == "categorical"
        assert compiler._infer_observation_distribution(_N("something")) == "unknown"

    def test_default_distribution_parameters(self, calculator_graph) -> None:
        graph, _ = calculator_graph
        compiler = StateSpaceCompiler(graph, schema_name="calc")

        assert compiler._default_distribution_parameters("bernoulli", None) == {"p": 0.5}
        gauss = compiler._default_distribution_parameters("gaussian", None)
        assert gauss == {"mean": 0.0, "variance": 1.0}
        cat_known = compiler._default_distribution_parameters("categorical", 5)
        assert cat_known == {"alpha": 1.0, "n_classes": 5.0}
        cat_unknown = compiler._default_distribution_parameters("categorical", None)
        assert cat_unknown == {"alpha": 1.0}
        assert compiler._default_distribution_parameters("weird", None) == {}

    def test_map_confidence_tiers(self, calculator_graph) -> None:
        graph, _ = calculator_graph
        compiler = StateSpaceCompiler(graph, schema_name="calc")
        assert compiler._map_confidence(1.0) is ConfidenceLevel.DEFINITE
        assert compiler._map_confidence(0.85) is ConfidenceLevel.HIGH
        assert compiler._map_confidence(0.65) is ConfidenceLevel.MEDIUM
        assert compiler._map_confidence(0.45) is ConfidenceLevel.LOW
        assert compiler._map_confidence(0.1) is ConfidenceLevel.UNCERTAIN

    def test_preference_expression_strategies(self, calculator_graph) -> None:
        graph, ids = calculator_graph
        compiler = StateSpaceCompiler(graph, schema_name="calc")

        # Strategy 1: explicit in mapping metadata
        m1 = SemanticMapping(
            id="p1",
            kind=MappingKind.PREFERENCE,
            graph_fragment_node_ids=[ids["assertion"]],
            semantic_label="pref1",
            description="d1",
            metadata={"expression": "x > 0"},
        )
        assert compiler._extract_preference_expression(m1) == "x > 0"

        # Strategy 2: assertion node metadata
        m2 = SemanticMapping(
            id="p2",
            kind=MappingKind.CONSTRAINT,
            graph_fragment_node_ids=[ids["assertion"]],
            semantic_label="nonneg",
            description="must be non-negative",
        )
        assert compiler._extract_preference_expression(m2) == "display >= 0"

        # Strategy 3: label + description fallback
        m3 = SemanticMapping(
            id="p3",
            kind=MappingKind.PREFERENCE,
            graph_fragment_node_ids=[],
            semantic_label="label",
            description="description",
        )
        assert compiler._extract_preference_expression(m3) == "label: description"

    def test_extract_action_parameters_dict_form(self, calculator_graph) -> None:
        graph, _ = calculator_graph
        compiler = StateSpaceCompiler(graph, schema_name="calc")

        class _N:
            metadata = {"parameters": {"self": None, "x": "int", "y": "float"}}

        result = compiler._extract_action_parameters(_N())
        assert "self" not in result
        assert result["x"] == "int"
        assert result["y"] == "float"

    def test_extract_action_parameters_entry_dict_form(self, calculator_graph) -> None:
        graph, _ = calculator_graph
        compiler = StateSpaceCompiler(graph, schema_name="calc")

        class _N:
            metadata = {
                "parameters": [
                    {"name": "self"},
                    {"name": "count", "type": "int"},
                ]
            }

        result = compiler._extract_action_parameters(_N())
        assert result == {"count": "int"}

    def test_extract_action_parameters_entry_tuple_form(self, calculator_graph) -> None:
        graph, _ = calculator_graph
        compiler = StateSpaceCompiler(graph, schema_name="calc")

        class _N:
            metadata = {"parameters": [("self",), ("name", "str"), ("score", "float")]}

        result = compiler._extract_action_parameters(_N())
        assert result == {"name": "str", "score": "float"}

    def test_extract_action_parameters_none_or_empty(self, calculator_graph) -> None:
        graph, _ = calculator_graph
        compiler = StateSpaceCompiler(graph, schema_name="calc")

        class _N:
            metadata = {}

        assert compiler._extract_action_parameters(_N()) == {}

        class _N2:
            metadata = {"parameters": None}

        assert compiler._extract_action_parameters(_N2()) == {}

        class _N3:
            metadata = {"parameters": 123}  # Unknown shape

        assert compiler._extract_action_parameters(_N3()) == {}

    def test_extract_action_effects_init_method(self, calculator_graph) -> None:
        """An __init__ method's effect should mention the parent class."""
        builder = ProgramGraphBuilder(repo_uri="test://init")
        module = builder.add_node(
            kind=NodeKind.MODULE, name="m", qualified_name="m", path="m.py", language="python",
        )
        cls = builder.add_node(
            kind=NodeKind.CLASS, name="Widget", qualified_name="m.Widget",
            path="m.py", language="python",
        )
        init = builder.add_node(
            kind=NodeKind.METHOD, name="__init__",
            qualified_name="m.Widget.__init__", path="m.py", language="python",
            metadata={"parameters": ["self"]},
        )
        builder.add_edge(module.id, cls.id, EdgeKind.CONTAINS)
        builder.add_edge(cls.id, init.id, EdgeKind.CONTAINS)
        g = builder.finalize()

        compiler = StateSpaceCompiler(g, schema_name="init")
        mapping = SemanticMapping(
            id="m1",
            kind=MappingKind.ACTION,
            graph_fragment_node_ids=[init.id],
            semantic_label="__init__",
        )
        effects = compiler._extract_action_effects(init.id, mapping)
        assert any("Widget" in eff for eff in effects)

    def test_extract_action_effects_calls_fallback(self, calculator_graph) -> None:
        """An action with only CALLS edges and no writes falls back to calls listing."""
        builder = ProgramGraphBuilder(repo_uri="test://calls")
        module = builder.add_node(
            kind=NodeKind.MODULE, name="m", qualified_name="m", path="m.py", language="python",
        )
        caller = builder.add_node(
            kind=NodeKind.FUNCTION, name="orchestrate",
            qualified_name="m.orchestrate", path="m.py", language="python",
        )
        callee = builder.add_node(
            kind=NodeKind.FUNCTION, name="do_work",
            qualified_name="m.do_work", path="m.py", language="python",
        )
        builder.add_edge(module.id, caller.id, EdgeKind.CONTAINS)
        builder.add_edge(module.id, callee.id, EdgeKind.CONTAINS)
        builder.add_edge(caller.id, callee.id, EdgeKind.CALLS)

        g = builder.finalize()
        compiler = StateSpaceCompiler(g, schema_name="calls")
        mapping = SemanticMapping(
            id="m1",
            kind=MappingKind.ACTION,
            graph_fragment_node_ids=[caller.id],
            semantic_label="orchestrate",
        )
        effects = compiler._extract_action_effects(caller.id, mapping)
        assert any("do_work" in eff for eff in effects)

    def test_extract_action_effects_reads_class_fallback(self, calculator_graph) -> None:
        """A method that only READS a class should fall through to the 'manages' strategy."""
        builder = ProgramGraphBuilder(repo_uri="test://reads")
        module = builder.add_node(
            kind=NodeKind.MODULE, name="m", qualified_name="m", path="m.py", language="python",
        )
        cls = builder.add_node(
            kind=NodeKind.CLASS, name="Thing", qualified_name="m.Thing",
            path="m.py", language="python",
        )
        # Use a FUNCTION (not METHOD) so strategy 3 (METHOD parent-class)
        # is not triggered. Leave CALLS and WRITES absent.
        fn = builder.add_node(
            kind=NodeKind.FUNCTION, name="report",
            qualified_name="m.report", path="m.py", language="python",
        )
        builder.add_edge(module.id, cls.id, EdgeKind.CONTAINS)
        builder.add_edge(module.id, fn.id, EdgeKind.CONTAINS)
        builder.add_edge(fn.id, cls.id, EdgeKind.READS)
        g = builder.finalize()

        compiler = StateSpaceCompiler(g, schema_name="reads")
        mapping = SemanticMapping(
            id="m1",
            kind=MappingKind.ACTION,
            graph_fragment_node_ids=[fn.id],
            semantic_label="report",
        )
        effects = compiler._extract_action_effects(fn.id, mapping)
        assert any("manages" in eff for eff in effects)

    def test_extract_action_effects_missing_node_returns_empty(
        self, calculator_graph
    ) -> None:
        graph, _ = calculator_graph
        compiler = StateSpaceCompiler(graph, schema_name="calc")
        mapping = SemanticMapping(
            id="m1",
            kind=MappingKind.ACTION,
            graph_fragment_node_ids=[],
            semantic_label="nothing",
        )
        assert compiler._extract_action_effects("missing-id", mapping) == []

    def test_extract_action_preconditions_explicit_metadata(
        self, calculator_graph
    ) -> None:
        graph, _ = calculator_graph
        compiler = StateSpaceCompiler(graph, schema_name="calc")

        class _N:
            id = "nope"
            metadata = {"preconditions": ["x > 0", "y != None"]}

        # When preconditions are explicit, they are returned as-is.
        result = compiler._extract_action_preconditions(_N())
        assert result == ["x > 0", "y != None"]

    def test_extract_action_preconditions_docstring_hint(self, calculator_graph) -> None:
        graph, ids = calculator_graph
        StateSpaceCompiler(graph, schema_name="calc")

        # Build a node whose metadata contains a 'require' docstring
        builder = ProgramGraphBuilder(repo_uri="test://doc")
        module = builder.add_node(
            kind=NodeKind.MODULE, name="m", qualified_name="m", path="m.py", language="python",
        )
        fn = builder.add_node(
            kind=NodeKind.FUNCTION, name="f",
            qualified_name="m.f", path="m.py", language="python",
            metadata={"docstring": "requires valid x and y"},
        )
        builder.add_edge(module.id, fn.id, EdgeKind.CONTAINS)
        g = builder.finalize()

        compiler2 = StateSpaceCompiler(g, schema_name="doc")
        node = g.get_node(fn.id)
        pre = compiler2._extract_action_preconditions(node)
        assert any("docstring" in p for p in pre)

    def test_preference_scope_follows_reads_writes(
        self, calculator_graph, calculator_mappings
    ) -> None:
        graph, ids = calculator_graph

        # Augment the graph: add a READS edge from the assertion node to
        # display so scope picks it up.
        builder = ProgramGraphBuilder(repo_uri="test://scope")
        module = builder.add_node(
            kind=NodeKind.MODULE,
            name="scope",
            qualified_name="scope",
            path="scope.py",
            language="python",
        )
        assertion = builder.add_node(
            kind=NodeKind.ASSERTION,
            name="a",
            qualified_name="scope.a",
            path="scope.py",
            language="python",
            metadata={"expression": "foo > 0"},
        )
        target = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="foo",
            qualified_name="scope.foo",
            path="scope.py",
            language="python",
            metadata={"type_hint": "int"},
        )
        builder.add_edge(module.id, assertion.id, EdgeKind.CONTAINS)
        builder.add_edge(assertion.id, target.id, EdgeKind.READS)
        sgraph = builder.finalize()

        compiler = StateSpaceCompiler(sgraph, schema_name="scope")
        mapping = SemanticMapping(
            id="p1",
            kind=MappingKind.CONSTRAINT,
            graph_fragment_node_ids=[assertion.id],
            semantic_label="foo_positive",
            description="foo must be positive",
            confidence_score=0.7,
        )
        scope = compiler._extract_preference_scope(mapping)
        assert f"var_{target.id}" in scope
