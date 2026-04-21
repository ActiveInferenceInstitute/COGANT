"""Behavioral tests for cogant.gnn.formatter.base.GNNMarkdownFormatter.

These tests feed the formatter real (non-mocked) ProgramGraph,
StateSpaceModel, ProcessModel, and SemanticMapping objects and assert
on the structural properties of the emitted markdown.
"""

from __future__ import annotations

from cogant.gnn.formatter.base import GNNMarkdownFormatter
from cogant.process.extractor import ProcessConnection, ProcessModel, Stage
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.schemas.semantic import (
    ConfidenceTier,
    MappingKind,
    ProvenanceRecord,
    SemanticMapping,
)
from cogant.statespace.compiler import (
    Action,
    Likelihood,
    ObservationModality,
    Preference,
    StateSpaceModel,
    Transition,
)
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import StateVariable, StateVariableType

# --------------------------- builders ----------------------------------- #


def _node(nid: str, kind: NodeKind, name: str | None = None) -> Node:
    return Node(
        id=nid,
        kind=kind,
        name=name or nid,
        qualified_name=f"pkg.{name or nid}",
        path="pkg/file.py",
    )


def _edge(eid: str, src: str, tgt: str, kind: EdgeKind, weight: float = 1.0) -> Edge:
    return Edge(id=eid, source_id=src, target_id=tgt, kind=kind, weight=weight)


def _graph() -> ProgramGraph:
    meta = GraphMetadata(repo_uri="file:///tmp/repo")
    meta.languages = {"python"}
    meta.evidence_sources = ["static"]
    g = ProgramGraph(metadata=meta)
    g.add_node(_node("mod1", NodeKind.MODULE, name="app"))
    g.add_node(_node("cls1", NodeKind.CLASS, name="Service"))
    g.add_node(_node("fn1", NodeKind.FUNCTION, name="do_work"))
    g.add_node(_node("fn2", NodeKind.FUNCTION, name="helper"))
    g.add_edge(_edge("e1", "mod1", "cls1", EdgeKind.CONTAINS))
    g.add_edge(_edge("e2", "cls1", "fn1", EdgeKind.CONTAINS))
    # Heavy CALLS edges from fn1 so _derive_probability_from_edges has
    # something to work with.
    g.add_edge(_edge("e3", "fn1", "fn2", EdgeKind.CALLS, weight=4.0))
    g.add_edge(_edge("e4", "fn1", "fn2", EdgeKind.WRITES, weight=6.0))
    return g


def _state_space() -> StateSpaceModel:
    return StateSpaceModel(
        id="m_1",
        schema_name="test_schema",
        variables={
            "v1": StateVariable(
                id="v1",
                name="busy",
                var_type=StateVariableType.BOOLEAN,
                node_id="fn1",
                description="Is the worker busy",
            ),
        },
        observations={
            "o1": ObservationModality(
                id="o1",
                name="heartbeat",
                source_node_id="fn1",
                modality_type="event",
            )
        },
        actions={
            "a1": Action(
                id="a1",
                name="fn1",  # matches graph node 'fn1' so probability derivation hits
                controller_id="cls1",
                effects=["v1"],
            ),
        },
        transitions={
            "t1": Transition(
                id="t1",
                source_state={"v1": "pre"},
                target_state={"v1": "post"},
                action_id="a1",
            )
        },
        likelihoods={
            "l1": Likelihood(
                id="l1",
                variable_id="v1",
                distribution_type="bernoulli",
                parameters={"p": 0.5},
            )
        },
        preferences={
            "p1": Preference(
                id="p1",
                name="stay_busy",
                description="prefer busy state",
                scope=["v1"],
                expression="v1 == True",
            )
        },
        time_regime=TimeRegime.SYNCHRONOUS,
        metadata={"pipeline_stages": ["ingest", "static"], "extraction_time_ms": 42},
    )


def _process() -> ProcessModel:
    return ProcessModel(
        id="pm_1",
        schema_name="test_schema",
        stages={
            "s1": Stage(id="s1", name="ingest"),
            "s2": Stage(id="s2", name="process"),
        },
        connections={
            "c1": ProcessConnection(
                id="c1",
                source_stage_id="s1",
                target_stage_id="s2",
                trigger="next",
            )
        },
    )


def _mappings() -> dict[str, SemanticMapping]:
    return {
        "m1": SemanticMapping(
            id="m1",
            kind=MappingKind.ACTION,
            graph_fragment_node_ids=["fn1"],
            graph_fragment_edge_ids=["e3"],
            semantic_label="do_work_action",
            confidence_score=0.85,
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(source="static_analysis", confidence=0.8),
                ProvenanceRecord(source="dynamic_trace", confidence=0.9),
            ],
        ),
    }


def _make_formatter() -> GNNMarkdownFormatter:
    return GNNMarkdownFormatter(
        program_graph=_graph(),
        state_space_model=_state_space(),
        process_model=_process(),
        semantic_mappings=_mappings(),
    )


# --------------------------- format() ----------------------------------- #


def test_format_emits_all_canonical_sections():
    """format() walks the SECTION_ORDER and returns a joined markdown string."""
    out = _make_formatter().format()

    # Every canonical section header should appear somewhere in the output.
    for header in [
        "## Model Metadata",
        "## Repository Metadata",
        "## Source Coverage",
        "## Rendering Hints",
        "## Validation Notes",
    ]:
        assert header in out, f"missing section header {header!r}"

    # Model schema name and repo URI are rendered.
    assert "test_schema" in out
    assert "file:///tmp/repo" in out


def test_format_tolerates_mapping_list_and_coerces_to_dict():
    """If a list of mappings is passed, format() converts it to a dict."""
    mappings_list = list(_mappings().values())
    f = GNNMarkdownFormatter(
        program_graph=_graph(),
        state_space_model=_state_space(),
        process_model=_process(),
        semantic_mappings=mappings_list,  # type: ignore[arg-type]
    )
    out = f.format()
    # The list was coerced — mappings is now a dict, and the semantic
    # label from m1 should appear.
    assert isinstance(f.mappings, dict)
    assert "do_work_action" in out


def test_format_handles_unsupported_mappings_type_gracefully():
    """A non-dict, non-list mappings argument becomes an empty dict."""
    f = GNNMarkdownFormatter(
        program_graph=_graph(),
        state_space_model=_state_space(),
        process_model=_process(),
        semantic_mappings="not-a-mapping",  # type: ignore[arg-type]
    )
    out = f.format()
    assert f.mappings == {}
    # Output still emits headers even with no mappings.
    assert "## Model Metadata" in out


# --------------------------- derive probability ------------------------- #


def test_derive_probability_from_edges_normalizes_and_caps_at_one():
    """Outgoing CALLS/WRITES/RETURNS edges contribute to the probability."""
    f = _make_formatter()
    # action_id 'fn1' matches the node id directly
    prob = f._derive_probability_from_edges("fn1")
    # (4.0 + 6.0) / 2 / 10 = 0.5
    assert prob is not None
    assert 0.0 <= prob <= 1.0
    assert prob == 0.5


def test_derive_probability_with_unknown_action_returns_none():
    """No matching node yields None."""
    f = _make_formatter()
    assert f._derive_probability_from_edges("does_not_exist") is None


def test_derive_probability_with_none_action_returns_none():
    """None action_id short-circuits to None."""
    f = _make_formatter()
    assert f._derive_probability_from_edges(None) is None


def test_derive_probability_with_no_qualifying_edges_returns_none():
    """A node without CALLS/WRITES/RETURNS outgoing edges returns None."""
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///tmp/r"))
    g.add_node(_node("lonely", NodeKind.FUNCTION))
    # Only an inheriting edge — which is not in the allow-list.
    g.add_node(_node("other", NodeKind.FUNCTION))
    g.add_edge(_edge("e_inh", "lonely", "other", EdgeKind.INHERITS))
    f = GNNMarkdownFormatter(
        program_graph=g,
        state_space_model=_state_space(),
        process_model=_process(),
        semantic_mappings={},
    )
    assert f._derive_probability_from_edges("lonely") is None


# --------------------------- action effects ----------------------------- #


def test_action_effects_reads_effects_attribute():
    """When action.effects is set, it is returned as a list."""
    action = Action(id="a", name="a", controller_id="c", effects=["v1", "v2"])
    assert GNNMarkdownFormatter._action_effects(action) == ["v1", "v2"]


def test_action_effects_falls_back_to_affects_state_vars():
    """When 'effects' is missing but 'affects_state_vars' is present it is used."""

    class _Legacy:
        affects_state_vars = ["a", "b"]

    assert GNNMarkdownFormatter._action_effects(_Legacy()) == ["a", "b"]


def test_action_effects_empty_when_neither_attribute_present():
    """An object with no relevant attributes yields an empty list."""

    class _Bare:
        pass

    assert GNNMarkdownFormatter._action_effects(_Bare()) == []


# --------------------------- format_section dispatcher ------------------ #


def test_format_section_dispatches_to_format_method():
    """format_section('model_metadata') calls _format_model_metadata."""
    f = _make_formatter()
    result = f.format_section("model_metadata")
    assert result is not None
    assert "## Model Metadata" in result
    assert "test_schema" in result


def test_format_section_returns_none_for_unknown_name():
    """Unknown section name returns None (no AttributeError)."""
    assert _make_formatter().format_section("nonexistent_section") is None
