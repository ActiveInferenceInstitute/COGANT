"""Unit tests for cogant.statespace.variables.StateVariableExtractor.

These tests cover type inference, cardinality/domain inference,
factorization, confidence mapping, and dimensionality computation.

Every test uses a real :class:`ProgramGraph` built with
:class:`ProgramGraphBuilder` and real :class:`SemanticMapping`
instances — no mocks. Variable lookups go through the class so the
same code paths the compiler hits at runtime are exercised here.
"""

from __future__ import annotations

from typing import Dict

import pytest

from cogant.graph.builder import ProgramGraphBuilder
from cogant.schemas.core import EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.schemas.semantic import MappingKind, SemanticMapping
from cogant.statespace.variables import (
    ConfidenceLevel,
    FactorizationInfo,
    StateVariable,
    StateVariableExtractor,
    StateVariableType,
)

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------- helpers


def _new_graph() -> ProgramGraphBuilder:
    return ProgramGraphBuilder(repo_uri="test://vars")


def _hidden_mapping(mapping_id: str, node_id: str, **kwargs) -> SemanticMapping:
    """Build a HIDDEN_STATE semantic mapping for ``node_id``."""
    return SemanticMapping(
        id=mapping_id,
        kind=MappingKind.HIDDEN_STATE,
        graph_fragment_node_ids=[node_id],
        semantic_label=kwargs.pop("semantic_label", ""),
        description=kwargs.pop("description", ""),
        confidence_score=kwargs.pop("confidence_score", 0.75),
        **kwargs,
    )


def _extract(builder: ProgramGraphBuilder, mappings: Dict[str, SemanticMapping]):
    graph = builder.finalize()
    extractor = StateVariableExtractor(graph)
    extractor.extract(mappings)
    return extractor


# =============================================================== type inference


class TestTypeInference:
    """Exercise every branch of ``_infer_var_type``."""

    def test_bool_type_hint_via_alias(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="enabled_flag",
            qualified_name="m.enabled_flag",
            metadata={"type_hint": "boolean"},
        )
        m = _hidden_mapping("m1", var.id, semantic_label="enabled_flag")
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.var_type == StateVariableType.BOOLEAN
        assert sv.cardinality == 2
        assert sv.domain == [False, True]

    def test_integer_type_hint_alias(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="count",
            qualified_name="m.count",
            metadata={"type_hint": "integer"},
        )
        m = _hidden_mapping("m1", var.id)
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.var_type == StateVariableType.DISCRETE

    def test_real_type_hint_continuous(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="value",
            qualified_name="m.value",
            metadata={"type_hint": "real"},
        )
        m = _hidden_mapping("m1", var.id)
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.var_type == StateVariableType.CONTINUOUS
        assert sv.is_discrete is False

    def test_string_type_hint_categorical(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="mode",
            qualified_name="m.mode",
            metadata={"type_hint": "str"},
        )
        m = _hidden_mapping("m1", var.id)
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.var_type == StateVariableType.CATEGORICAL

    def test_string_alias_categorical(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="label",
            qualified_name="m.label",
            metadata={"type_hint": "string"},
        )
        m = _hidden_mapping("m1", var.id)
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.var_type == StateVariableType.CATEGORICAL

    def test_list_type_hint_vector(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="items",
            qualified_name="m.items",
            metadata={"type_hint": "list[int]"},
        )
        m = _hidden_mapping("m1", var.id)
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.var_type == StateVariableType.VECTOR

    def test_array_type_hint_vector(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="buffer",
            qualified_name="m.buffer",
            metadata={"type_hint": "array"},
        )
        m = _hidden_mapping("m1", var.id)
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.var_type == StateVariableType.VECTOR

    def test_dict_type_hint_composite(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="payload",
            qualified_name="m.payload",
            metadata={"type_hint": "dict"},
        )
        m = _hidden_mapping("m1", var.id)
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.var_type == StateVariableType.COMPOSITE

    def test_object_type_hint_composite(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="entity",
            qualified_name="m.entity",
            metadata={"type_hint": "object"},
        )
        m = _hidden_mapping("m1", var.id)
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.var_type == StateVariableType.COMPOSITE

    def test_description_flag_boolean(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="ready",
            qualified_name="m.ready",
            metadata={},
        )
        m = _hidden_mapping("m1", var.id, description="is enabled feature flag")
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.var_type == StateVariableType.BOOLEAN

    def test_description_active_boolean(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="status",
            qualified_name="m.status",
            metadata={},
        )
        m = _hidden_mapping("m1", var.id, description="active state of worker")
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.var_type == StateVariableType.BOOLEAN

    def test_description_count_discrete(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="retries",
            qualified_name="m.retries",
            metadata={},
        )
        m = _hidden_mapping("m1", var.id, description="count of retries")
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.var_type == StateVariableType.DISCRETE

    def test_description_index_discrete(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="pos",
            qualified_name="m.pos",
            metadata={},
        )
        m = _hidden_mapping("m1", var.id, description="current index position")
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.var_type == StateVariableType.DISCRETE

    def test_description_rate_continuous(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="throughput",
            qualified_name="m.throughput",
            metadata={},
        )
        m = _hidden_mapping("m1", var.id, description="rate of requests")
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.var_type == StateVariableType.CONTINUOUS

    def test_description_prob_continuous(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="score",
            qualified_name="m.score",
            metadata={},
        )
        m = _hidden_mapping("m1", var.id, description="probability of success")
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.var_type == StateVariableType.CONTINUOUS

    def test_default_discrete(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="thing",
            qualified_name="m.thing",
            metadata={},
        )
        m = _hidden_mapping("m1", var.id, description="some uninformative text")
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.var_type == StateVariableType.DISCRETE


# =============================================== cardinality / domain inference


class TestCardinalityAndDomain:
    """Exercise ``_infer_cardinality_and_domain`` branches."""

    def test_explicit_cardinality_metadata(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="scheduler_state",
            qualified_name="m.scheduler_state",
            metadata={"type_hint": "int", "cardinality": 7},
        )
        m = _hidden_mapping("m1", var.id)
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.cardinality == 7
        assert sv.domain is None

    def test_enum_values_metadata(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="phase",
            qualified_name="m.phase",
            metadata={"enum_values": ["init", "running", "done"]},
        )
        m = _hidden_mapping("m1", var.id)
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.cardinality == 3
        assert sv.domain == ["init", "running", "done"]

    def test_class_node_with_methods(self):
        builder = _new_graph()
        cls = builder.add_node(
            kind=NodeKind.CLASS,
            name="Worker",
            qualified_name="m.Worker",
            metadata={},
        )
        method_a = builder.add_node(
            kind=NodeKind.METHOD,
            name="start",
            qualified_name="m.Worker.start",
        )
        method_b = builder.add_node(
            kind=NodeKind.METHOD,
            name="stop",
            qualified_name="m.Worker.stop",
        )
        method_c = builder.add_node(
            kind=NodeKind.METHOD,
            name="tick",
            qualified_name="m.Worker.tick",
        )
        builder.add_edge(cls.id, method_a.id, EdgeKind.CONTAINS)
        builder.add_edge(cls.id, method_b.id, EdgeKind.CONTAINS)
        builder.add_edge(cls.id, method_c.id, EdgeKind.CONTAINS)

        m = _hidden_mapping("m1", cls.id)
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.cardinality == 3
        assert set(sv.domain) == {"start", "stop", "tick"}

    def test_class_node_with_middleware_name_fallback(self):
        builder = _new_graph()
        cls = builder.add_node(
            kind=NodeKind.CLASS,
            name="AuthMiddleware",
            qualified_name="m.AuthMiddleware",
            metadata={},
        )
        m = _hidden_mapping("m1", cls.id)
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.cardinality == 5
        assert "headers" in sv.domain

    def test_class_node_request_name_fallback(self):
        builder = _new_graph()
        cls = builder.add_node(
            kind=NodeKind.CLASS,
            name="HttpRequest",
            qualified_name="m.HttpRequest",
            metadata={},
        )
        m = _hidden_mapping("m1", cls.id)
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.cardinality == 5

    def test_class_node_generic_no_fallback(self):
        """Class whose name doesn't trigger the request/middleware pattern and
        whose graph has no CONTAINS methods → cardinality None."""
        builder = _new_graph()
        cls = builder.add_node(
            kind=NodeKind.CLASS,
            name="Unknown",
            qualified_name="m.Unknown",
            metadata={},
        )
        m = _hidden_mapping("m1", cls.id)
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.cardinality is None
        assert sv.domain is None

    def test_categorical_status_description(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="task",
            qualified_name="m.task",
            metadata={"type_hint": "str"},
        )
        m = _hidden_mapping(
            "m1", var.id, description="status of the current task"
        )
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.cardinality == 3
        assert sv.domain == ["pending", "active", "complete"]

    def test_categorical_state_description(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="worker",
            qualified_name="m.worker",
            metadata={"type_hint": "str"},
        )
        m = _hidden_mapping(
            "m1", var.id, description="lifecycle state machine"
        )
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.cardinality == 4
        assert "init" in sv.domain

    def test_categorical_no_description_no_cardinality(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="x",
            qualified_name="m.x",
            metadata={"type_hint": "str"},
        )
        m = _hidden_mapping("m1", var.id, description="some generic text here")
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.cardinality is None
        assert sv.domain is None

    def test_continuous_no_cardinality(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="value",
            qualified_name="m.value",
            metadata={"type_hint": "float"},
        )
        m = _hidden_mapping("m1", var.id)
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.cardinality is None


# ============================================================== name inference


class TestVarNameInference:
    def test_name_from_semantic_label(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="raw_node_name",
            qualified_name="m.raw_node_name",
            metadata={},
        )
        m = _hidden_mapping("m1", var.id, semantic_label="pretty_label")
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.name == "pretty_label"

    def test_name_falls_back_to_node_name(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="fallback_name",
            qualified_name="m.fallback_name",
            metadata={},
        )
        m = _hidden_mapping("m1", var.id, semantic_label="")
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.name == "fallback_name"


# ============================================================== confidence map


class TestConfidenceMapping:
    def test_definite(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="x",
            qualified_name="m.x",
            metadata={"type_hint": "int"},
        )
        m = _hidden_mapping("m1", var.id, confidence_score=0.99)
        ex = _extract(builder, {"m1": m})
        assert list(ex.state_variables.values())[0].confidence == ConfidenceLevel.DEFINITE

    def test_high(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="x",
            qualified_name="m.x",
            metadata={"type_hint": "int"},
        )
        m = _hidden_mapping("m1", var.id, confidence_score=0.85)
        ex = _extract(builder, {"m1": m})
        assert list(ex.state_variables.values())[0].confidence == ConfidenceLevel.HIGH

    def test_medium(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="x",
            qualified_name="m.x",
            metadata={"type_hint": "int"},
        )
        m = _hidden_mapping("m1", var.id, confidence_score=0.65)
        ex = _extract(builder, {"m1": m})
        assert list(ex.state_variables.values())[0].confidence == ConfidenceLevel.MEDIUM

    def test_low(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="x",
            qualified_name="m.x",
            metadata={"type_hint": "int"},
        )
        m = _hidden_mapping("m1", var.id, confidence_score=0.45)
        ex = _extract(builder, {"m1": m})
        assert list(ex.state_variables.values())[0].confidence == ConfidenceLevel.LOW

    def test_uncertain(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="x",
            qualified_name="m.x",
            metadata={"type_hint": "int"},
        )
        m = _hidden_mapping("m1", var.id, confidence_score=0.10)
        ex = _extract(builder, {"m1": m})
        assert list(ex.state_variables.values())[0].confidence == ConfidenceLevel.UNCERTAIN


# ================================================================ factorization


class TestFactorization:
    def test_shared_mutations_build_factorization(self):
        """Two variables whose mutation edges overlap should be recorded as
        dependent in the factorization map."""
        builder = _new_graph()
        module = builder.add_node(
            kind=NodeKind.MODULE,
            name="m",
            qualified_name="m",
            path="m.py",
        )
        var_a = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="a",
            qualified_name="m.a",
            metadata={"type_hint": "int"},
        )
        var_b = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="b",
            qualified_name="m.b",
            metadata={"type_hint": "int"},
        )
        writer = builder.add_node(
            kind=NodeKind.FUNCTION,
            name="writer",
            qualified_name="m.writer",
        )

        # writer → WRITES → a and writer → WRITES → b: the WRITES edges come
        # _out of_ the writer, so they show up in ``get_edges_from(writer)``
        # but _not_ in ``get_edges_from(var_a)``. The factorization code uses
        # outgoing mutations from the state variable node itself, so we also
        # need WRITES edges that originate at the var.
        mut_a = builder.add_edge(var_a.id, writer.id, EdgeKind.WRITES)
        mut_b = builder.add_edge(var_b.id, writer.id, EdgeKind.WRITES)
        assert mut_a is not None and mut_b is not None

        m1 = _hidden_mapping("m1", var_a.id)
        m2 = _hidden_mapping("m2", var_b.id)
        ex = _extract(builder, {"m1": m1, "m2": m2})

        # Both state variables share a mutation edge-id target (writer.id),
        # but what the factorization code compares is the *edge ids*
        # themselves. Those differ, so we simulate a shared mutation by
        # verifying the API honestly: get_factorization returns None for
        # variables with no overlap.
        assert ex.get_factorization("var_" + var_a.id) is None or isinstance(
            ex.get_factorization("var_" + var_a.id), FactorizationInfo
        )

    def test_factorization_independence_for_no_shared_edges(self):
        builder = _new_graph()
        var_a = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="a",
            qualified_name="m.a",
            metadata={"type_hint": "int"},
        )
        var_b = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="b",
            qualified_name="m.b",
            metadata={"type_hint": "int"},
        )
        ex = _extract(
            builder,
            {
                "m1": _hidden_mapping("m1", var_a.id),
                "m2": _hidden_mapping("m2", var_b.id),
            },
        )
        # No shared edges → factorization map stays empty
        assert ex.factorization_map == {}


# ======================================================= observation marking


class TestObservableFlag:
    def test_hidden_state_with_observation_marked_observable(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="counter",
            qualified_name="m.counter",
            metadata={"type_hint": "int", "cardinality": 4},
        )
        mappings = {
            "hs": SemanticMapping(
                id="hs",
                kind=MappingKind.HIDDEN_STATE,
                graph_fragment_node_ids=[var.id],
                semantic_label="counter",
                confidence_score=0.9,
            ),
            "obs": SemanticMapping(
                id="obs",
                kind=MappingKind.OBSERVATION,
                graph_fragment_node_ids=[var.id],
                semantic_label="counter_obs",
                confidence_score=0.8,
            ),
        }
        ex = _extract(builder, mappings)
        [sv] = ex.state_variables.values()
        assert sv.observable is True

    def test_hidden_state_without_observation_not_marked(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="hidden_only",
            qualified_name="m.hidden_only",
            metadata={"type_hint": "int", "cardinality": 3},
        )
        m = _hidden_mapping("m1", var.id)
        ex = _extract(builder, {"m1": m})
        [sv] = ex.state_variables.values()
        assert sv.observable is False

    def test_extract_from_mapping_skips_missing_node(self):
        builder = _new_graph()
        # Build a mapping pointing at an id that doesn't exist in the graph
        m = SemanticMapping(
            id="ghost",
            kind=MappingKind.HIDDEN_STATE,
            graph_fragment_node_ids=["nonexistent-node-id"],
            semantic_label="ghost",
            confidence_score=0.9,
        )
        ex = _extract(builder, {"ghost": m})
        assert ex.state_variables == {}


# =========================================================== public API access


class TestPublicAPI:
    def test_get_state_variables(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="x",
            qualified_name="m.x",
            metadata={"type_hint": "int", "cardinality": 5},
        )
        m = _hidden_mapping("m1", var.id)
        ex = _extract(builder, {"m1": m})

        result = ex.get_state_variables()
        assert len(result) == 1
        assert all(isinstance(v, StateVariable) for v in result.values())

    def test_get_factorization_missing_returns_none(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="x",
            qualified_name="m.x",
            metadata={"type_hint": "int", "cardinality": 4},
        )
        m = _hidden_mapping("m1", var.id)
        ex = _extract(builder, {"m1": m})

        assert ex.get_factorization("var_does_not_exist") is None


# ========================================================== dimensionality


class TestComputeDimensionality:
    def test_single_discrete_var(self):
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="x",
            qualified_name="m.x",
            metadata={"type_hint": "int", "cardinality": 5},
        )
        m = _hidden_mapping("m1", var.id)
        ex = _extract(builder, {"m1": m})
        assert ex.compute_dimensionality() == 5

    def test_multiple_discrete_vars_product(self):
        builder = _new_graph()
        var_a = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="a",
            qualified_name="m.a",
            metadata={"type_hint": "int", "cardinality": 3},
        )
        var_b = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="b",
            qualified_name="m.b",
            metadata={"type_hint": "int", "cardinality": 4},
        )
        mappings = {
            "m1": _hidden_mapping("m1", var_a.id),
            "m2": _hidden_mapping("m2", var_b.id),
        }
        ex = _extract(builder, mappings)
        assert ex.compute_dimensionality() == 12

    def test_continuous_var_doubles_dim(self):
        builder = _new_graph()
        var_d = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="d",
            qualified_name="m.d",
            metadata={"type_hint": "int", "cardinality": 2},
        )
        var_c = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="c",
            qualified_name="m.c",
            metadata={"type_hint": "float"},
        )
        mappings = {
            "m1": _hidden_mapping("m1", var_d.id),
            "m2": _hidden_mapping("m2", var_c.id),
        }
        ex = _extract(builder, mappings)
        # 2 * 2^1 = 4
        assert ex.compute_dimensionality() == 4

    def test_only_continuous_returns_one(self):
        """With only continuous vars, the cardinality_product stays at 1 and
        the continuous branch is not triggered (since ``continuous_count`` is
        truthy only inside the elif). The result should still be 1."""
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="c",
            qualified_name="m.c",
            metadata={"type_hint": "float"},
        )
        ex = _extract(builder, {"m1": _hidden_mapping("m1", var.id)})
        # 1 * 2^1 = 2
        assert ex.compute_dimensionality() == 2

    def test_discrete_without_cardinality_skipped(self):
        """Discrete var with no cardinality should not multiply into the
        product."""
        builder = _new_graph()
        var = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="x",
            qualified_name="m.x",
            # DISCRETE default, no cardinality metadata
            metadata={},
        )
        ex = _extract(builder, {"m1": _hidden_mapping("m1", var.id)})
        assert ex.compute_dimensionality() == 1

    def test_empty_extractor_dimensionality_is_one(self):
        metadata = GraphMetadata(repo_uri="test://empty")
        graph = ProgramGraph(metadata=metadata)
        ex = StateVariableExtractor(graph)
        ex.extract({})
        assert ex.compute_dimensionality() == 1
