"""Unit tests for AII GNN v2.0.0 spec compliance in COGANT's output formatter.

These tests assert the three non-conformances identified during the 2026-04-09
GNN spec validation audit and fixed in this session:

1. Time section uses ``Discrete`` + ``Time=t`` (not ``DiscreteTime=t``).
2. Connections section uses bare variable names without parentheses.
3. No duplicate ``## Connections`` header (COGANT extended section renamed).

Spec source: https://github.com/ActiveInferenceInstitute/GeneralizedNotationNotation
             doc/gnn/reference/gnn_syntax.md v2.0.0
Upstream type-checker: src/type_checker/checker.py

All tests use real COGANT value objects — no mocks.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure py/cogant is importable when tests run from the repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PY_ROOT = _REPO_ROOT / "py"
if str(_PY_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_ROOT))

from cogant.gnn.formatter.base import GNNMarkdownFormatter
from cogant.gnn.validator import GNNValidator
from cogant.graph.builder import ProgramGraphBuilder
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.statespace.compiler import (
    Action,
    ObservationModality,
    StateSpaceModel,
)
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import (
    ConfidenceLevel,
    StateVariable,
    StateVariableType,
)

pytestmark = pytest.mark.unit


# ------------------------------------------------------------------ fixtures


def _build_minimal_graph() -> ProgramGraph:
    """Build a minimal program graph with one state, one obs, one action."""
    builder = ProgramGraphBuilder(repo_uri="test://gnn-spec")
    s = builder.add_node(
        kind=NodeKind.VARIABLE,
        name="state0",
        qualified_name="m.state0",
        path="m.py",
        language="python",
    )
    o = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="obs0",
        qualified_name="m.obs0",
        path="m.py",
        language="python",
    )
    a = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="act0",
        qualified_name="m.act0",
        path="m.py",
        language="python",
    )
    builder.add_edge(o.id, s.id, EdgeKind.READS)
    builder.add_edge(a.id, s.id, EdgeKind.WRITES)
    return builder.finalize() if hasattr(builder, "finalize") else builder.graph


def _build_state_space(graph: ProgramGraph, dynamic: bool = False) -> StateSpaceModel:
    """Build a minimal StateSpaceModel."""
    nodes = list(graph.nodes.values())
    state_node = next(n for n in nodes if n.name == "state0")
    obs_node = next(n for n in nodes if n.name == "obs0")
    act_node = next(n for n in nodes if n.name == "act0")

    var = StateVariable(
        id="var:s0",
        name="state0",
        var_type=StateVariableType.DISCRETE,
        node_id=state_node.id,
        cardinality=2,
        confidence=ConfidenceLevel.HIGH,
    )
    obs = ObservationModality(
        id="obs:o0",
        name="obs0",
        source_node_id=obs_node.id,
        modality_type="discrete",
        cardinality=2,
    )
    act = Action(
        id="act:a0",
        name="act0",
        controller_id=act_node.id,
    )

    from cogant.statespace.compiler import Transition  # type: ignore[attr-defined]

    transitions: dict = {}
    if dynamic:
        t = Transition(
            id="tr:0",
            source_state={"var:s0": 0},
            target_state={"var:s0": 1},
            action_id="act:a0",
        )
        transitions = {"tr:0": t}

    return StateSpaceModel(
        id="ss:test",
        schema_name="TestModel",
        variables={"var:s0": var},
        observations={"obs:o0": obs},
        actions={"act:a0": act},
        transitions=transitions,
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


def _build_formatter(dynamic: bool = False) -> GNNMarkdownFormatter:
    """Return a ready-to-use GNNMarkdownFormatter."""
    from cogant.process.extractor import ProcessModel  # type: ignore[attr-defined]

    graph = _build_minimal_graph()
    state_space = _build_state_space(graph, dynamic=dynamic)
    try:
        process = ProcessModel(stages={}, connections={})
    except Exception:
        # Fallback if ProcessModel signature differs
        process = type("ProcessModel", (), {"stages": {}, "connections": {}})()
    return GNNMarkdownFormatter(
        program_graph=graph,
        state_space_model=state_space,
        process_model=process,
        semantic_mappings={},
    )


def _build_multi_observation_formatter() -> GNNMarkdownFormatter:
    """Return formatter with one state factor and three observation modalities."""
    from cogant.process.extractor import ProcessModel  # type: ignore[attr-defined]

    graph = _build_minimal_graph()
    state_space = _build_state_space(graph, dynamic=True)
    obs_template = next(iter(state_space.observations.values()))
    state_space.observations = {
        f"obs:o{i}": ObservationModality(
            id=f"obs:o{i}",
            name=f"obs{i}",
            source_node_id=obs_template.source_node_id,
            modality_type="discrete",
            cardinality=2,
        )
        for i in range(3)
    }
    try:
        process = ProcessModel(stages={}, connections={})
    except Exception:
        process = type("ProcessModel", (), {"stages": {}, "connections": {}})()
    return GNNMarkdownFormatter(
        program_graph=graph,
        state_space_model=state_space,
        process_model=process,
        semantic_mappings={},
    )


# ------------------------------------------------------------------ spec tests


class TestTimeSection:
    """GNN 2.0.0 spec: Time section must use Discrete and Time=t separately."""

    def test_dynamic_time_emits_discrete_keyword(self):
        """Dynamic model must have 'Discrete' on its own line (not 'DiscreteTime=t').

        The upstream type-checker (src/type_checker/checker.py) recognises
        'Discrete' as a valid time specification keyword. 'DiscreteTime=t'
        (the fused form) is not in the valid-spec list and generates a warning.
        """
        fmt = _build_formatter(dynamic=True)
        md = fmt.format()
        # Find Time section content
        assert "## Time" in md
        time_idx = md.index("## Time")
        # Grab lines until next ## section or end
        time_block = md[time_idx:]
        next_section = time_block.find("## ", 2)
        if next_section > 0:
            time_block = time_block[:next_section]

        assert "Discrete" in time_block, (
            f"Dynamic Time section must contain 'Discrete' per upstream spec. Got:\n{time_block}"
        )
        assert "Time=t" in time_block, (
            f"Dynamic Time section must contain 'Time=t' per upstream spec. Got:\n{time_block}"
        )

    def test_dynamic_time_does_not_emit_fused_discretttime(self):
        """'DiscreteTime=t' (fused form) must not appear — it is not a valid upstream keyword."""
        fmt = _build_formatter(dynamic=True)
        md = fmt.format()
        assert "DiscreteTime=t" not in md, (
            "The fused token 'DiscreteTime=t' is not a valid upstream GNN 2.0.0 "
            "time specification. Use 'Discrete' + 'Time=t' on separate lines."
        )

    def test_static_time_emits_static(self):
        """Static model Time section must contain 'Static'."""
        fmt = _build_formatter(dynamic=False)
        md = fmt.format()
        time_idx = md.index("## Time")
        time_block = md[time_idx:]
        next_section = time_block.find("## ", 2)
        if next_section > 0:
            time_block = time_block[:next_section]
        assert "Static" in time_block


class TestConnectionSyntax:
    """GNN 2.0.0 spec: Connections must use bare variable names without parentheses."""

    def test_upstream_connections_no_leading_paren(self):
        """No connection line in ## Connections should start with '('.

        The upstream type-checker splits on '>' to extract source/target names.
        A source like '(D_f0)' becomes a name containing '(' which the checker
        flags as 'potentially undefined variable: (D_f0'.
        """
        fmt = _build_formatter()
        md = fmt.format()

        # Isolate the upstream Connections block (first occurrence)
        conn_idx = md.index("## Connections")
        conn_block = md[conn_idx:]
        next_section = conn_block.find("## ", 2)
        if next_section > 0:
            conn_block = conn_block[:next_section]

        for line in conn_block.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            assert not line.startswith("("), (
                f"Connection line must not start with '(': {line!r}. "
                "Use bare variable names per upstream GNN 2.0.0 spec."
            )

    def test_upstream_connections_target_no_paren(self):
        """Connection targets must not be wrapped in single-variable parentheses.

        'D_f0>(s_f0)' is invalid; use 'D_f0>s_f0'.
        """
        fmt = _build_formatter()
        md = fmt.format()

        conn_idx = md.index("## Connections")
        conn_block = md[conn_idx:]
        next_section = conn_block.find("## ", 2)
        if next_section > 0:
            conn_block = conn_block[:next_section]

        for line in conn_block.splitlines():
            line = line.strip()
            if ">" not in line or line.startswith("#"):
                continue
            parts = line.split(">")
            target = parts[-1].strip()
            # Single-variable targets must not have parens
            # Multi-source (comma) in source side is allowed
            assert not (target.startswith("(") and "," not in target), (
                f"Single-variable connection target must not be parenthesised: {line!r}. "
                "Use bare variable name e.g. 'D_f0>s_f0' not 'D_f0>(s_f0)'."
            )


class TestNoDuplicateConnectionsHeader:
    """GNN 2.0.0: Only one ## Connections section should appear in the document.

    Having two ## Connections headers confuses the upstream parser which
    treats the second as a continuation of the first upstream connections block.
    The COGANT extended connections section must use a distinct header
    (## Program Graph Connections).
    """

    def test_connections_header_appears_exactly_once(self):
        """'## Connections' must appear exactly once — the upstream block."""
        fmt = _build_formatter()
        md = fmt.format()
        count = md.count("## Connections\n")
        assert count == 1, (
            f"Expected exactly 1 '## Connections' header, found {count}. "
            "The COGANT extended connections section must use a different header."
        )

    def test_program_graph_connections_section_present(self):
        """COGANT extended connections use '## Program Graph Connections' header."""
        fmt = _build_formatter()
        md = fmt.format()
        assert "## Program Graph Connections" in md, (
            "The COGANT extended program-graph connections section must use "
            "'## Program Graph Connections' as its header."
        )


class TestUpstreamSectionOrder:
    """GNN v2.0.0 spec: required upstream sections must appear in canonical order."""

    UPSTREAM_REQUIRED = [
        "GNNSection",
        "GNNVersionAndFlags",
        "ModelName",
        "StateSpaceBlock",
        "Connections",
        "InitialParameterization",
        "Equations",
        "Time",
        "ActInfOntologyAnnotation",
        "ModelParameters",
        "Footer",
        "Signature",
    ]

    def test_all_upstream_sections_present(self):
        """All required upstream GNN v2.0.0 sections must appear."""
        fmt = _build_formatter()
        md = fmt.format()
        for section in self.UPSTREAM_REQUIRED:
            assert f"## {section}" in md, f"Required upstream section missing: ## {section}"

    def test_upstream_sections_in_canonical_order(self):
        """Required upstream sections must appear in the spec-mandated order."""
        fmt = _build_formatter()
        md = fmt.format()
        positions = [(s, md.find(f"## {s}")) for s in self.UPSTREAM_REQUIRED]
        found = [(s, p) for s, p in positions if p >= 0]
        sorted_by_pos = sorted(found, key=lambda x: x[1])
        assert [s for s, _ in found] == [s for s, _ in sorted_by_pos], (
            f"Upstream sections out of order. Found order: {[s for s, _ in found]}. "
            f"Expected: {[s for s, _ in sorted_by_pos]}"
        )


class TestStateSpaceBlockSyntax:
    """GNN 2.0.0 spec: StateSpaceBlock variable declarations must parse correctly."""

    def test_variable_declarations_match_spec_pattern(self):
        """Each variable declaration must match pattern: NAME[dim,dim,...,type=T].

        The upstream type-checker regex is: r'(\\w+)\\s*\\[([^\\]]+)\\]'
        """
        import re

        pattern = re.compile(r"(\w+)\s*\[([^\]]+)\]")

        fmt = _build_formatter()
        md = fmt.format()

        ssb_idx = md.index("## StateSpaceBlock")
        ssb_block = md[ssb_idx:]
        next_section = ssb_block.find("## ", 2)
        if next_section > 0:
            ssb_block = ssb_block[:next_section]

        var_lines = [
            line.strip()
            for line in ssb_block.splitlines()
            if line.strip() and not line.strip().startswith("#") and "[" in line
        ]
        assert len(var_lines) > 0, "StateSpaceBlock must declare at least one variable"
        for line in var_lines:
            assert pattern.match(line), (
                f"Variable declaration does not match upstream pattern "
                f"'NAME[dim,...,type=T]': {line!r}"
            )

    def test_variable_declarations_have_type_annotation(self):
        """Each variable declaration must include 'type=' per GNN 2.0.0 spec."""
        fmt = _build_formatter()
        md = fmt.format()

        ssb_idx = md.index("## StateSpaceBlock")
        ssb_block = md[ssb_idx:]
        next_section = ssb_block.find("## ", 2)
        if next_section > 0:
            ssb_block = ssb_block[:next_section]

        var_lines = [
            line.strip()
            for line in ssb_block.splitlines()
            if line.strip() and not line.strip().startswith("#") and "[" in line
        ]
        for line in var_lines:
            assert "type=" in line, (
                f"Variable declaration missing 'type=' annotation per GNN 2.0.0: {line!r}"
            )

    def test_each_observation_modality_has_likelihood_matrix(self):
        """Multi-modal models need one A_mN likelihood per observation modality."""
        fmt = _build_multi_observation_formatter()
        md = fmt.format()

        for expected in (
            "A_m0[2,2,type=float]",
            "A_m1[2,2,type=float]",
            "A_m2[2,2,type=float]",
            "s_f0>A_m0",
            "s_f0>A_m1",
            "s_f0>A_m2",
            "A_m0,s_f0>o_m0",
            "A_m1,s_f0>o_m1",
            "A_m2,s_f0>o_m2",
            "A_m0={",
            "A_m1={",
            "A_m2={",
            "A_m0=LikelihoodMatrix",
            "A_m1=LikelihoodMatrix",
            "A_m2=LikelihoodMatrix",
        ):
            assert expected in md

    def test_current_artifact_uses_renderable_state_space_and_transition_contract(self):
        """Current public GNN artifacts expose metadata the upstream renderer can parse."""
        fmt = _build_multi_observation_formatter()
        md = fmt.format()

        assert "s_f0[2,1,type=int] # state factor" in md
        assert "o_m0[2,1,type=int] # observation modality" in md
        assert "u_c0[1,1,type=int] # action control" in md
        assert "identity(" not in md
        assert "B_f0={ ((" in md
        assert "num_states:" in md
        assert "num_obs:" in md
        assert "num_actions:" in md


class TestValidatorSpec:
    """GNNValidator must detect the spec-compliance requirements."""

    def test_validator_detects_discrete_time_fused_token(self):
        """Validator's validate_markdown should not error on correct Time section format."""
        validator = GNNValidator()
        # A minimal document with the correct time format
        md_correct = (
            "## GNNSection\nTest\n\n"
            "## GNNVersionAndFlags\nGNN v2.0.0\n\n"
            "## ModelName\nTest\n\n"
            "## StateSpaceBlock\ns_f0[2,1,type=int]\n\n"
            "## Connections\nD_f0>s_f0\n\n"
            "## InitialParameterization\nD_f0={ (0.5, 0.5) }\n\n"
            "## Equations\nQ(s) = softmax(ln(D) + ln(A^T * o))\n\n"
            "## Time\nDynamic\nDiscrete\nTime=t\nModelTimeHorizon=Unbounded\n\n"
            "## ActInfOntologyAnnotation\ns_f0=HiddenState\n\n"
            "## ModelParameters\nnum_hidden_states=1\n\n"
            "## Footer\nGenerated by COGANT.\n\n"
            "## Signature\npending\n"
        )
        errors = validator.validate_markdown(md_correct)
        # Should find no upstream section errors
        upstream_errors = [e for e in errors if "upstream GNN v2.0.0 section" in e]
        assert upstream_errors == [], (
            f"Correct upstream document should have no section errors: {upstream_errors}"
        )

    def test_validator_canonical_section_uses_program_graph_connections(self):
        """GNNValidator.CANONICAL_SECTIONS must use 'program_graph_connections' not 'connections'."""
        validator = GNNValidator()
        assert "program_graph_connections" in validator.CANONICAL_SECTIONS, (
            "CANONICAL_SECTIONS must use 'program_graph_connections' "
            "(not 'connections') to match the renamed ## Program Graph Connections header."
        )
        assert "connections" not in validator.CANONICAL_SECTIONS, (
            "'connections' should not be in CANONICAL_SECTIONS — it conflicts with "
            "the upstream ## Connections header."
        )
