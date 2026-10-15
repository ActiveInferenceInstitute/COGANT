"""Reverse synthesis of models that declare actions but no hidden states.

COGANT's forward pass regularly emits stateless modules whose functions are
classified as ACTION with no hidden state and no transition tensor.  The GNN
validator requires ``B`` to be empty when there are no hidden states, so the
reverse path must accept that shape instead of demanding a ``B`` that no
value can satisfy.  Round-trip verifiers must also report a synthesis failure
as a ``FAILED`` result rather than raising (and leaking their temp dir).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from cogant.reverse import idempotency
from cogant.reverse.idempotency import (
    ROUNDTRIP_STATUS_FAILED,
    verify_repo_roundtrip,
    verify_roundtrip,
)
from cogant.reverse.matrices import render_matrices_module
from cogant.reverse.parser import ReverseGNNModel, ReverseModelError, parse_gnn
from cogant.reverse.planner import plan_package
from cogant.reverse.synthesizer import synthesize_package

# Upstream header emitted by the forward formatter for a stateless module
# whose two functions were classified as ACTION (e.g. the data_pipeline
# control-positive fixture).
ACTION_ONLY_GNN = """\
## GNNSection
data_pipeline

## GNNVersionAndFlags
GNN v2.0.0

## ModelName
data_pipeline

## StateSpaceBlock
u_c0[1,1,type=int] # action control
u_c1[1,1,type=int] # action control
t[1,1,type=int]

## Connections
# No connections derivable from empty state space

## InitialParameterization
# No parameters to emit; code-derived values live in state_space.json

## ActInfOntologyAnnotation
u_c0=Action
u_c1=Action
t=Time
"""

# Observation + action modules without hidden state (plugin_architecture shape).
OBSERVATION_ACTION_GNN = """\
## ModelName
plugin_architecture

## StateSpaceBlock
o_m0[2,1,type=int] # observation modality
u_c0[1,1,type=int] # action control
A_m0[2,2,type=float]

## InitialParameterization
A_m0={ ((1.0, 0.0), (0.0, 1.0)) }

## ActInfOntologyAnnotation
o_m0=Observation
u_c0=Action
"""

# Hidden state, observation and actions present, D does not sum to 1.0.
INVALID_PRIOR_GNN = """\
## ModelName
bad

## StateSpaceBlock
s_f0[2,1,type=int]
o_m0[2,1,type=int]

```gnn-matrices
A[[rows=2][cols=2]]
  0.9 0.1
  0.1 0.9

B[[rows=2][cols=2][depth=1]]
  # action=0
  1 0
  0 1

C[[rows=2]]
  0
  1

D[[rows=2]]
  0.5
  0.9
```
"""


def _render_constants(model: ReverseGNNModel) -> dict[str, object]:
    namespace: dict[str, object] = {}
    exec(compile(render_matrices_module(model), "matrices.py", "exec"), namespace)
    return namespace


def test_action_only_model_validates_without_transition_tensor() -> None:
    model = parse_gnn(ACTION_ONLY_GNN)

    assert model.actions == ["u_c0", "u_c1"]
    assert model.hidden_states == []
    assert model.validate() == []


def test_action_only_model_renders_empty_transition_matrices() -> None:
    namespace = _render_constants(parse_gnn(ACTION_ONLY_GNN))

    assert namespace["N_HIDDEN_STATES"] == 0
    assert namespace["N_ACTIONS"] == 2
    assert namespace["B"] == []
    assert namespace["D"] == []
    transition = namespace["transition"]
    assert callable(transition)
    with pytest.raises(ValueError, match="prior D"):
        transition([], 0)


def test_observation_action_model_without_hidden_states_renders() -> None:
    namespace = _render_constants(parse_gnn(OBSERVATION_ACTION_GNN))

    assert namespace["N_HIDDEN_STATES"] == 0
    assert namespace["A"] == []
    assert namespace["B"] == []


def test_action_only_model_synthesizes_package(tmp_path: Path) -> None:
    model = parse_gnn(ACTION_ONLY_GNN)
    package = synthesize_package(plan_package(model), model, tmp_path)

    assert (package / "matrices.py").is_file()
    assert (package / "act.py").is_file()


def test_transition_tensor_still_required_when_hidden_states_and_actions_exist() -> None:
    model = ReverseGNNModel(
        hidden_states=["s_f0"],
        actions=["u_c0"],
        cardinalities={"s_f0": 2, "u_c0": 1},
        A=[],
        C=[],
        D=[0.5, 0.5],
    )

    assert "B is required when hidden-state and action variables are declared" in (model.validate())
    with pytest.raises(ReverseModelError, match="B is required"):
        render_matrices_module(model)


def test_verify_roundtrip_reports_failed_synthesis_without_leaking_tmp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gnn = tmp_path / "bad.gnn.md"
    gnn.write_text(INVALID_PRIOR_GNN, encoding="utf-8")
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))

    result = verify_roundtrip(gnn)

    assert result.roundtrip_status == ROUNDTRIP_STATUS_FAILED
    assert not result.role_preserved
    assert any("D must sum to 1.0" in error for error in result.errors)
    assert result.package_path is None
    assert list(scratch.iterdir()) == []


def test_verify_repo_roundtrip_reports_failed_synthesis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "agent.py").write_text(
        "class Agent:\n"
        "    def __init__(self) -> None:\n"
        "        self.count = 0\n\n"
        "    def observe_count(self) -> int:\n"
        "        return self.count\n\n"
        "    def update_count(self, value: int) -> None:\n"
        "        self.count = value\n",
        encoding="utf-8",
    )

    def refuse(*_args: object, **_kwargs: object) -> Path:
        raise ReverseModelError("synthetic synthesis refusal")

    monkeypatch.setattr(idempotency, "synthesize_package", refuse)
    monkeypatch.setattr(idempotency, "synthesize_stable_minimal_package", refuse)

    result = verify_repo_roundtrip(repo, output_dir=tmp_path / "out")

    assert result.roundtrip_status == ROUNDTRIP_STATUS_FAILED
    assert not result.role_preserved
    assert any("synthetic synthesis refusal" in error for error in result.errors)
    assert result.original_roles
