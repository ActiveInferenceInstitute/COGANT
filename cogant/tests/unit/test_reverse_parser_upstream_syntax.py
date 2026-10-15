"""Reverse parsing of upstream GNN syntax and COGANT's hand-authored zoo models.

The parser promises to accept upstream GNN files and to leave fields it cannot
recover empty rather than inventing semantics.  These tests pin the behaviour
for the canonical upstream POMDP example (bare ``s``/``o``/``u`` names, inline
``#`` comments, plain multi-line ``A={ ... }`` parameter blocks, action-major
``B``) and for the zoo examples (named ``D_prior``/``A_likelihood`` keys,
``identity(...)`` transitions, observation/control declaration blocks), while
COGANT's own forward bundles keep their aggregate per-variable dimensions.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest
import typer
from typer.testing import CliRunner

from cogant.reverse.cli import reverse_command, roundtrip_command
from cogant.reverse.matrices import render_matrices_module
from cogant.reverse.parser import ReverseGNNModel, parse_gnn

ZOO = Path(__file__).resolve().parents[2] / "examples" / "zoo"

# Condensed copy of the upstream ``actinf_pomdp_agent.md`` example: section
# structure, inline comments, and parameter literals are kept verbatim.
UPSTREAM_POMDP = """\
# GNN Example: Active Inference POMDP Agent
# GNN Version: 1.0

## GNNSection
ActInfPOMDP

## GNNVersionAndFlags
GNN v1

## ModelName
Active Inference POMDP Agent

## StateSpaceBlock
# Likelihood matrix: A[observation_outcomes, hidden_states]
A[3,3,type=float]   # Likelihood mapping hidden states to observations

# Transition matrix: B[next_state, previous_state, actions]
B[3,3,3,type=float]   # State transitions given previous state and action

# Preference vector: C[observation_outcomes]
C[3,type=float]       # Log-preferences over observations

# Prior vector: D[states]
D[3,type=float]       # Prior over initial hidden states

# Habit vector: E[actions]
E[3,type=float]       # Initial policy prior (habit) over actions

# Hidden State
s[3,1,type=float]     # Current hidden state distribution
s_prime[3,1,type=float] # Next hidden state distribution
F[π,type=float]       # Variational Free Energy for belief updating from observations

# Observation
o[3,1,type=int]     # Current observation (integer index)

# Policy and Control
π[3,type=float]       # Policy (distribution over actions), no planning
u[1,type=int]         # Action taken
G[π,type=float]       # Expected Free Energy (per policy)

# Time
t[1,type=int]         # Discrete time step

## Connections
D>s
s-A
s>s_prime
A-o
s-B
C>G
E>π
G>π
π>u
B>u
u>s_prime

## InitialParameterization
# A: 3 observations x 3 hidden states. Rows are observations, columns are hidden states.
A={
  (0.9, 0.05, 0.05),
  (0.05, 0.9, 0.05),
  (0.05, 0.05, 0.9)
}

# B: per-action slices are column-stochastic: rows are next states, columns are previous states.
B={
  ( (1.0,0.0,0.0), (0.0,1.0,0.0), (0.0,0.0,1.0) ),
  ( (0.0,1.0,0.0), (1.0,0.0,0.0), (0.0,0.0,1.0) ),
  ( (0.0,0.0,1.0), (0.0,1.0,0.0), (1.0,0.0,0.0) )
}

# C: 3 observations. Preference in terms of log-probabilities over observations.
C={(0.1, 0.1, 1.0)}

# D: 3 states. Uniform prior over hidden states.
D={(0.33333, 0.33333, 0.33333)}

# E: 3 actions. Uniform habit used as initial policy prior.
E={(0.33333, 0.33333, 0.33333)}

## Time
Time=t
Dynamic
Discrete
ModelTimeHorizon=Unbounded # The agent is defined for an unbounded time horizon.

## ActInfOntologyAnnotation
A=LikelihoodMatrix
B=TransitionMatrix
C=LogPreferenceVector
D=PriorOverHiddenStates
E=Habit
F=VariationalFreeEnergy
G=ExpectedFreeEnergy
s=HiddenState
s_prime=NextHiddenState
o=Observation
π=PolicyVector # Distribution over actions
u=Action       # Chosen action
t=Time

## ModelParameters
num_hidden_states: 3  # s[3]
num_obs: 3           # o[3]
num_actions: 3       # B actions_dim=3 (controlled by π)
"""

UPSTREAM_A = [[0.9, 0.05, 0.05], [0.05, 0.9, 0.05], [0.05, 0.05, 0.9]]
# Action-major source slices: UPSTREAM_B_SLICES[action][next_state][previous_state].
UPSTREAM_B_SLICES = [
    [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
    [[0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
    [[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0]],
]


def _render(model: ReverseGNNModel) -> dict[str, object]:
    namespace: dict[str, object] = {}
    exec(compile(render_matrices_module(model), "matrices.py", "exec"), namespace)
    return namespace


def _approx_matrix(actual: list[list[float]], expected: list[list[float]]) -> None:
    assert len(actual) == len(expected)
    for row, expected_row in zip(actual, expected, strict=True):
        assert row == pytest.approx(expected_row)


def test_trailing_comments_do_not_hide_declarations_or_annotations() -> None:
    model = parse_gnn(
        "## ModelName\nm\n\n## StateSpaceBlock\n"
        "s_f0[10,1,type=int] # state factor\n"
        "o_m0[2,1,type=int]   # observation modality\n\n"
        "## ActInfOntologyAnnotation\n"
        "s_f0=HiddenState # the factor\n"
        "o_m0=Observation\n"
    )

    assert model.hidden_states == ["s_f0"]
    assert model.cardinalities["s_f0"] == 10
    assert model.cardinalities["o_m0"] == 2
    assert model.types["s_f0"] == "int"
    assert model.annotations["s_f0"] == "HiddenState"


def test_upstream_pomdp_keeps_bare_role_names() -> None:
    model = parse_gnn(UPSTREAM_POMDP)

    assert model.hidden_states == ["s"]
    assert model.observations == ["o"]
    assert model.actions == ["u"]
    assert model.cardinalities["s"] == 3
    assert model.cardinalities["o"] == 3
    assert model.annotations["u"] == "Action"


def test_upstream_pomdp_recovers_source_matrices() -> None:
    model = parse_gnn(UPSTREAM_POMDP)

    assert not model.degraded
    _approx_matrix(model.A, UPSTREAM_A)
    assert model.C == pytest.approx([0.1, 0.1, 1.0])
    assert model.D == pytest.approx([1 / 3, 1 / 3, 1 / 3])
    assert len(model.B) == 3 and len(model.B[0]) == 3 and len(model.B[0][0]) == 3
    for action, slice_ in enumerate(UPSTREAM_B_SLICES):
        for next_state in range(3):
            for previous_state in range(3):
                assert (
                    model.B[next_state][previous_state][action]
                    == slice_[next_state][previous_state]
                )


def test_upstream_pomdp_renders_source_dimensions() -> None:
    namespace = _render(parse_gnn(UPSTREAM_POMDP))

    assert namespace["N_HIDDEN_STATES"] == 3
    assert namespace["N_OBSERVATIONS"] == 3
    assert namespace["N_ACTIONS"] == 3
    assert namespace["DEGRADED_SOURCE_PROJECTION"] is False
    assert namespace["C"] == pytest.approx([0.1, 0.1, 1.0])
    _approx_matrix(namespace["A"], UPSTREAM_A)  # type: ignore[arg-type]


def test_multiline_parameter_blocks_and_bracket_rows_parse() -> None:
    model = parse_gnn(
        "## ModelName\nm\n\n## StateSpaceBlock\ns[2,1,type=int]\no[2,1,type=int]\n\n"
        "## InitialParameterization\n"
        "A={\n  [0.75, 0.25],  # first outcome\n  [0.25, 0.75]\n}\n"
        "C={ (0.0,\n  2.0) }\n"
        "D={ (0.5, 0.5) }\n\n"
        "## ActInfOntologyAnnotation\ns=HiddenState\no=Observation\n"
    )

    _approx_matrix(model.A, [[0.75, 0.25], [0.25, 0.75]])
    assert model.C == pytest.approx([0.0, 2.0])
    assert model.D == pytest.approx([0.5, 0.5])
    assert not model.degraded


def test_pathologically_nested_parameter_literal_is_ignored_not_recursed() -> None:
    depth = 5_000
    model = parse_gnn(
        "## ModelName\nm\n\n## StateSpaceBlock\ns[2,1,type=int]\n\n"
        f"## InitialParameterization\nD={'{' * depth}0.5, 0.5{'}' * depth}\n\n"
        "## ActInfOntologyAnnotation\ns=HiddenState\n"
    )

    # The literal is rejected as unparseable; the declared factor still
    # yields its (uniform) prior instead of a RecursionError.
    assert model.D == pytest.approx([0.5, 0.5])


def test_zoo_full_pomdp_recovers_named_parameters() -> None:
    model = parse_gnn(ZOO / "12_full_pomdp" / "model.gnn.md")

    assert model.hidden_states == ["s_hidden"]
    assert model.observations == ["o_sensor"]
    assert model.actions == ["u_action"]
    assert model.C == pytest.approx([0.05, 0.05, 0.80, 0.05, 0.05])
    assert model.D == pytest.approx([0.2] * 5)
    for row in range(5):
        expected = [0.8 if row == col else 0.05 for col in range(5)]
        assert model.A[row] == pytest.approx(expected)
    namespace = _render(model)
    assert namespace["N_HIDDEN_STATES"] == 5
    assert namespace["N_OBSERVATIONS"] == 5
    assert namespace["N_ACTIONS"] == 3


def test_zoo_pomdp_minimal_reads_observation_and_control_blocks() -> None:
    model = parse_gnn(ZOO / "04_pomdp_minimal" / "model.gnn.md")

    assert model.hidden_states == ["s_beliefs"]
    assert model.observations == ["o_sensor"]
    assert model.actions == ["u_action"]
    assert model.cardinalities["o_sensor"] == 3
    assert model.cardinalities["u_action"] == 2
    for row in range(3):
        expected = [0.8 if row == col else 0.1 for col in range(3)]
        assert model.A[row] == pytest.approx(expected)
    # The source declares no preferences: C is the flagged zero projection.
    assert model.C == [0.0, 0.0, 0.0]
    assert model.degraded
    namespace = _render(model)
    assert namespace["N_HIDDEN_STATES"] == 3
    assert namespace["N_OBSERVATIONS"] == 3


def test_zoo_hierarchical_keeps_both_hidden_factors() -> None:
    model = parse_gnn(ZOO / "06_hierarchical" / "model.gnn.md")

    assert model.hidden_states == ["s_planner", "s_executor"]
    assert model.cardinalities["s_planner"] == 3
    assert model.cardinalities["s_executor"] == 4
    assert len(model.D) == 12
    assert sum(model.D) == pytest.approx(1.0)
    assert _render(model)["N_HIDDEN_STATES"] == 12


def test_cogant_forward_bundle_keeps_aggregate_dimensions_without_cartesian_blowup() -> None:
    # COGANT's forward formatter comments every factor declaration and puts
    # the authoritative aggregate (one row per variable) matrices in the
    # ``gnn-matrices`` fence.  The 2*9*8*2**8 Cartesian product of these
    # cardinalities must never be materialized.
    cards = [2, 9, 8, 2, 2, 2, 2, 2, 2, 2, 2]
    n = len(cards)
    declarations = "\n".join(
        f"s_f{i}[{card},1,type=int] # state factor" for i, card in enumerate(cards)
    )
    priors = "\n".join(
        f"D_f{i}={{ ({', '.join([str(round(1 / card, 4))] * card)}) }}"
        for i, card in enumerate(cards)
    )
    ontology = "\n".join(f"s_f{i}=HiddenState" for i in range(n))
    b_rows = "\n".join(
        "  " + " ".join("1" if row == col else "0" for col in range(n)) for row in range(n)
    )
    text = (
        "## ModelName\nbig\n\n## StateSpaceBlock\n"
        f"{declarations}\no_m0[2,1,type=int] # observation modality\n"
        "u_c0[1,1,type=int] # action control\n\n"
        f"## InitialParameterization\n{priors}\n\n"
        "## ActInfOntologyAnnotation\n"
        f"{ontology}\no_m0=Observation\nu_c0=Action\n\n"
        "## State Space\n\n```gnn-matrices\n"
        f"A[[rows=1][cols={n}]]\n  {' '.join(['1'] * n)}\n\n"
        f"B[[rows={n}][cols={n}][depth=1]]\n  # action=0\n{b_rows}\n\n"
        "C[[rows=1]]\n  0\n\n"
        f"D[[rows={n}]]\n" + "\n".join(f"  {1 / n!r}" for _ in range(n)) + "\n```\n"
    )

    started = time.perf_counter()
    model = parse_gnn(text)

    assert time.perf_counter() - started < 5.0
    assert [model.cardinalities[f"s_f{i}"] for i in range(n)] == cards
    assert model.n_states == n
    assert model.n_obs == 1
    assert model.n_actions == 1
    assert not model.degraded
    assert model.matrix_source == "fenced"


def _reverse_json(gnn: Path, out_dir: Path) -> dict[str, Any]:
    app = typer.Typer()
    app.command("reverse")(reverse_command)
    app.command("roundtrip")(roundtrip_command)
    result = CliRunner().invoke(app, ["reverse", str(gnn), "--output", str(out_dir), "--json"])
    assert result.exit_code == 0, result.stdout
    start, end = result.stdout.find("{"), result.stdout.rfind("}")
    payload: dict[str, Any] = json.loads(result.stdout[start : end + 1])
    return payload


def test_reverse_cli_reports_upstream_roles_without_degradation(tmp_path: Path) -> None:
    gnn = tmp_path / "actinf_pomdp_agent.md"
    gnn.write_text(UPSTREAM_POMDP, encoding="utf-8")

    payload = _reverse_json(gnn, tmp_path / "out")

    assert payload["hidden_states"] == 1
    assert payload["observations"] == 1
    assert payload["actions"] == 1
    assert payload["degraded_source_projection"] is False
    assert payload["diagnostics"] == []


def test_reverse_cli_flags_projected_matrices(tmp_path: Path) -> None:
    payload = _reverse_json(ZOO / "04_pomdp_minimal" / "model.gnn.md", tmp_path / "out")

    assert payload["degraded_source_projection"] is True
    assert any("C declarations" in item for item in payload["diagnostics"])
