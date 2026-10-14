"""Upstream ``## InitialParameterization`` values and their derivation cost.

The block emits per-factor placeholders (uniform ``D_f``, identity ``B_f``,
column-stochastic identity-like ``A_m``) plus the derived log-preference
``C`` broadcast over each modality. Only ``C`` comes from
:class:`cogant.gnn.matrices.GNNMatrices`, so emitting the block must not
build the (potentially multi-million entry) A/B arrays just to discard
them. The pinned literal guards the emitted text against drift.
"""

from __future__ import annotations

import pytest

from cogant.gnn.formatter import GNNMarkdownFormatter
from cogant.gnn.matrices import GNNMatrices
from cogant.process.extractor import ProcessModel
from cogant.schemas.core import Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.schemas.semantic import MappingKind, SemanticMapping
from cogant.statespace.compiler import Action, ObservationModality, Preference, StateSpaceModel
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import StateVariable, StateVariableType

pytestmark = pytest.mark.unit


def _formatter() -> GNNMarkdownFormatter:
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///t"))
    for nid in ("s0", "s1", "o0", "a0", "a1"):
        graph.add_node(Node(id=nid, kind=NodeKind.FUNCTION, name=nid, qualified_name=nid))
    variables = {
        "var_s0": StateVariable(
            id="var_s0", name="s0", var_type=StateVariableType.DISCRETE, node_id="s0", cardinality=3
        ),
        "var_s1": StateVariable(
            id="var_s1", name="s1", var_type=StateVariableType.BOOLEAN, node_id="s1", cardinality=2
        ),
    }
    obs = ObservationModality(
        id="obs_o0", name="o0", source_node_id="o0", modality_type="log", cardinality=2
    )
    actions = {
        f"act_{a}": Action(id=f"act_{a}", name=a, controller_id=a) for a in ("a0", "a1")
    }
    pref = Preference(
        id="pref", name="pref", description="", scope=["var_s0"], expression="ok"
    )
    state_space = StateSpaceModel(
        id="ss",
        schema_name="current",
        variables=variables,
        observations={obs.id: obs},
        actions=actions,
        transitions={},
        likelihoods={},
        preferences={pref.id: pref},
        time_regime=TimeRegime.SYNCHRONOUS,
    )
    constraint = SemanticMapping(
        id="c0",
        kind=MappingKind.CONSTRAINT,
        graph_fragment_node_ids=["o0"],
        semantic_label="display stays valid",
        confidence_score=0.8,
    )
    return GNNMarkdownFormatter(
        graph,
        state_space,
        ProcessModel(id="pm", schema_name="current", stages={}, connections={}),
        {constraint.id: constraint},
    )


EXPECTED = "\n".join(
    [
        "## InitialParameterization",
        "D_f0={ (0.3333, 0.3333, 0.3333) }",
        "D_f1={ (0.5, 0.5) }",
        "A_m0={ (1.0, 0.0, 0.5), (0.0, 1.0, 0.5) }",
        "B_f0={ ((1.0, 1.0), (0.0, 0.0), (0.0, 0.0)), ((0.0, 0.0), (1.0, 1.0), (0.0, 0.0)), "
        "((0.0, 0.0), (0.0, 0.0), (1.0, 1.0)) }",
        "B_f1={ ((1.0, 1.0), (0.0, 0.0)), ((0.0, 0.0), (1.0, 1.0)) }",
        "C_m0={ (0.8, 0.8) }",
    ]
)


def test_initial_parameterization_literal_is_stable() -> None:
    assert _formatter()._format_initial_parameterization() == EXPECTED


def test_initial_parameterization_does_not_build_unused_matrices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _unused(self: GNNMatrices) -> list[object]:
        raise AssertionError("InitialParameterization only needs the C vector")

    monkeypatch.setattr(GNNMatrices, "compute_A", _unused)
    monkeypatch.setattr(GNNMatrices, "compute_B", _unused)
    monkeypatch.setattr(GNNMatrices, "compute_D", _unused)

    assert _formatter()._format_initial_parameterization() == EXPECTED
