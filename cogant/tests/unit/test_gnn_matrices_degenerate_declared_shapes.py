"""Declared matrix shapes follow the dimensions for degenerate models.

A model with zero hidden states (or zero observations) has empty A/B/D
(or A/C) arrays. ``GNNMatrices.to_dict()`` must still declare the logical
shapes ``A=[n_obs, n_states]`` and ``B=[n_states, n_states, n_actions]``
so the package validator's degenerate-model path reports the package as
valid with a warning, instead of failing on shapes like ``[0, 0]``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cogant.gnn.matrices import GNNMatrices
from cogant.gnn.package import GNNPackageBuilder
from cogant.gnn.validator import GNNValidator
from cogant.process.extractor import ProcessModel
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.statespace.compiler import Action, ObservationModality, StateSpaceModel
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import StateVariable, StateVariableType


def _graph() -> ProgramGraph:
    return ProgramGraph(metadata=GraphMetadata(repo_uri="file:///t"))


def _state_space(n_vars: int, n_obs: int, n_actions: int) -> StateSpaceModel:
    variables = {
        f"var_{i}": StateVariable(
            id=f"var_{i}",
            name=f"v{i}",
            var_type=StateVariableType.DISCRETE,
            node_id=f"n_v{i}",
            cardinality=2,
        )
        for i in range(n_vars)
    }
    observations = {
        f"obs_{i}": ObservationModality(
            id=f"obs_{i}", name=f"o{i}", source_node_id=f"n_o{i}", modality_type="log"
        )
        for i in range(n_obs)
    }
    actions = {
        f"act_{k}": Action(id=f"act_{k}", name=f"a{k}", controller_id=f"n_a{k}")
        for k in range(n_actions)
    }
    return StateSpaceModel(
        id="ss",
        schema_name="current",
        variables=variables,
        observations=observations,
        actions=actions,
        transitions={},
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("n_vars", "n_obs", "n_actions", "expected"),
    [
        (0, 3, 3, {"A": [3, 0], "B": [0, 0, 3], "C": [3], "D": [0]}),
        (2, 0, 1, {"A": [0, 2], "B": [2, 2, 1], "C": [0], "D": [2]}),
        (0, 0, 0, {"A": [0, 0], "B": [0, 0, 0], "C": [0], "D": [0]}),
    ],
)
def test_declared_shapes_follow_dimensions(
    n_vars: int, n_obs: int, n_actions: int, expected: dict[str, list[int]]
) -> None:
    payload = GNNMatrices(_graph(), {}, _state_space(n_vars, n_obs, n_actions)).to_dict()
    assert payload["shapes"] == expected
    assert GNNValidator().validate_matrices(payload) == []


@pytest.mark.unit
def test_zero_hidden_state_package_is_valid_with_degenerate_warning(tmp_path: Path) -> None:
    GNNPackageBuilder(
        graph=_graph(),
        state_space=_state_space(0, 3, 3),
        process_model=ProcessModel(id="pm", schema_name="current", stages={}, connections={}),
        mappings={},
    ).build(str(tmp_path))

    result = GNNValidator().validate_package(str(tmp_path), upstream_gnn=False)

    assert [e for e in result.errors if e.startswith("Matrix validation")] == []
    assert result.valid is True
    assert any("no hidden-state variables" in w for w in result.warnings)
