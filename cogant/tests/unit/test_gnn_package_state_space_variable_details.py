"""``state_space.json`` / ``factors.json`` carry the compiled variable details.

``StateSpaceModel.variables`` is a ``dict[str, StateVariable]`` and
``ObservationModality`` exposes its channel class as ``modality_type``.
The package builder must serialise those real objects instead of falling
back to opaque ``{"id", "name": id, "type": "variable"}`` stubs, a single
synthetic ``"default"`` factor, and a hard-coded ``"symbolic"`` modality.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cogant.gnn.package import GNNPackageBuilder
from cogant.process.extractor import ProcessModel
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.statespace.compiler import ObservationModality, StateSpaceModel
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import ConfidenceLevel, StateVariable, StateVariableType


def _state_space() -> StateSpaceModel:
    hidden = StateVariable(
        id="var_calc",
        name="Calculator - Hidden State",
        var_type=StateVariableType.DISCRETE,
        node_id="node_calc",
        cardinality=3,
        domain=["idle", "typing", "done"],
        factors=["arith"],
        confidence=ConfidenceLevel.HIGH,
        description="calculator display state",
    )
    unfactored = StateVariable(
        id="var_mode",
        name="Mode - Hidden State",
        var_type=StateVariableType.BOOLEAN,
        node_id="node_mode",
        cardinality=2,
    )
    obs = ObservationModality(
        id="obs_display",
        name="get_display - Observation",
        source_node_id="node_display",
        modality_type="sensor",
        cardinality=4,
    )
    return StateSpaceModel(
        id="ss",
        schema_name="current",
        variables={hidden.id: hidden, unfactored.id: unfactored},
        observations={obs.id: obs},
        actions={},
        transitions={},
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


def _builder() -> GNNPackageBuilder:
    return GNNPackageBuilder(
        graph=ProgramGraph(metadata=GraphMetadata(repo_uri="test", languages={"python"})),
        state_space=_state_space(),
        process_model=ProcessModel(id="pm", schema_name="current", stages={}, connections={}),
        mappings={},
    )


@pytest.mark.unit
def test_state_variables_serialise_compiled_fields() -> None:
    by_id = {v["id"]: v for v in _builder()._extract_state_variables()}

    calc = by_id["var_calc"]
    assert calc["name"] == "Calculator - Hidden State"
    assert calc["var_type"] == "discrete"
    assert calc["cardinality"] == 3
    assert calc["domain"] == ["idle", "typing", "done"]
    assert calc["factors"] == ["arith"]
    assert calc["node_id"] == "node_calc"
    assert calc["confidence"] == "high"
    assert "type" not in calc or calc["type"] != "variable"

    assert by_id["var_mode"]["name"] == "Mode - Hidden State"
    assert by_id["var_mode"]["var_type"] == "boolean"


@pytest.mark.unit
def test_factorization_groups_variables_by_compiled_factors() -> None:
    factorization = _builder()._extract_factorization()
    groups = {f["id"]: f["variables"] for f in factorization["factors"]}

    assert groups["arith"] == ["var_calc"]
    # Variables without a factor keep the documented "default" bucket.
    assert groups["default"] == ["var_mode"]
    assert factorization["variable_count"] == 2


@pytest.mark.unit
def test_observation_space_reports_modality_type() -> None:
    (obs,) = _builder()._extract_observation_space()

    assert obs["modality"] == "sensor"
    assert obs["modality_type"] == "sensor"
    assert obs["source_node_id"] == "node_display"
    assert obs["cardinality"] == 4


@pytest.mark.unit
def test_built_package_state_space_matches_model_variables(tmp_path: Path) -> None:
    _builder().build(str(tmp_path))

    state_space = json.loads((tmp_path / "state_space.json").read_text(encoding="utf-8"))
    model = json.loads((tmp_path / "model.gnn.json").read_text(encoding="utf-8"))

    model_vars = model["state_space"]["variables"]
    for entry in state_space["variables"]:
        assert entry["name"] == model_vars[entry["id"]]["name"]
        assert entry["cardinality"] == model_vars[entry["id"]]["cardinality"]
    assert {o["modality"] for o in state_space["observations"]} == {"sensor"}

    factors = json.loads((tmp_path / "factors.json").read_text(encoding="utf-8"))
    assert {f["id"] for f in factors["factors"]} == {"arith", "default"}
