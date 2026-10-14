"""A top-K truncated B tensor stays valid and aligned with A and D.

When ``n_states² × n_actions`` exceeds ``_MAX_B_ENTRIES``,
:meth:`GNNMatrices.compute_B` keeps only the highest-degree hidden states.
The export must record which states were kept (in A/D axis order) so the
B axis can be realigned, and the package validator must accept the
documented truncation instead of rejecting every large-repo package.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cogant.gnn.matrices import GNNMatrices
from cogant.gnn.package import GNNPackageBuilder
from cogant.gnn.validator import GNNValidator
from cogant.process.extractor import ProcessModel
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.statespace.compiler import Action, ObservationModality, StateSpaceModel
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import StateVariable, StateVariableType

N_STATES = 6
N_ACTIONS = 3
# 6² × 3 = 108 entries > 27, and isqrt(27 // 3) = 3 states are kept.
SMALL_CAP = 27


def _graph() -> ProgramGraph:
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///t"))
    for i in range(N_STATES):
        graph.add_node(Node(id=f"s{i}", kind=NodeKind.CLASS, name=f"s{i}", qualified_name=f"s{i}"))
    for k in range(N_ACTIONS):
        graph.add_node(
            Node(id=f"a{k}", kind=NodeKind.FUNCTION, name=f"a{k}", qualified_name=f"a{k}")
        )
    graph.add_node(Node(id="o0", kind=NodeKind.FUNCTION, name="o0", qualified_name="o0"))
    edges = [
        ("w0", "a0", "s5", EdgeKind.WRITES),
        ("d1", "s5", "s0", EdgeKind.DEPENDS_ON),
        ("d2", "s5", "s2", EdgeKind.DEPENDS_ON),
        ("d3", "s5", "s4", EdgeKind.DEPENDS_ON),
        ("d4", "s3", "s1", EdgeKind.DEPENDS_ON),
        ("d5", "s3", "s1", EdgeKind.CALLS),
        ("d6", "s3", "s1", EdgeKind.CONTAINS),
    ]
    for eid, src, tgt, kind in edges:
        graph.add_edge(Edge(id=eid, source_id=src, target_id=tgt, kind=kind))
    return graph


def _state_space() -> StateSpaceModel:
    variables = {
        f"var_s{i}": StateVariable(
            id=f"var_s{i}",
            name=f"s{i}",
            var_type=StateVariableType.DISCRETE,
            node_id=f"s{i}",
            cardinality=2,
        )
        for i in range(N_STATES)
    }
    actions = {
        f"act_a{k}": Action(id=f"act_a{k}", name=f"a{k}", controller_id=f"a{k}")
        for k in range(N_ACTIONS)
    }
    obs = ObservationModality(id="obs_o0", name="o0", source_node_id="o0", modality_type="log")
    return StateSpaceModel(
        id="ss",
        schema_name="current",
        variables=variables,
        observations={obs.id: obs},
        actions=actions,
        transitions={},
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


@pytest.fixture
def small_b_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(GNNMatrices.compute_B.__globals__, "_MAX_B_ENTRIES", SMALL_CAP)


@pytest.mark.unit
@pytest.mark.usefixtures("small_b_cap")
def test_truncation_records_kept_states_in_original_axis_order() -> None:
    payload = GNNMatrices(_graph(), {}, _state_space()).to_dict()

    truncation = payload["truncation"]
    assert truncation["applied"] is True
    assert truncation["n_states_kept"] == 3
    # Highest degree: s5 (4 edges), s3 (3), s1 (3). Kept in A/D order.
    assert truncation["kept_state_indices"] == [1, 3, 5]
    assert truncation["kept_state_ids"] == ["var_s1", "var_s3", "var_s5"]
    assert payload["shapes"]["B"] == [3, 3, N_ACTIONS]
    assert payload["dimensions"]["n_states"] == N_STATES


@pytest.mark.unit
@pytest.mark.usefixtures("small_b_cap")
def test_truncated_b_axis_maps_back_to_full_state_axis() -> None:
    payload = GNNMatrices(_graph(), {}, _state_space()).to_dict()
    kept = payload["truncation"]["kept_state_indices"]
    B = payload["B"]

    # Action a0 WRITES s5: from current state s1 the direct mass lands on s5.
    nxt, cur = kept.index(5), kept.index(1)
    assert B[nxt][cur][0] == pytest.approx(0.9)
    assert B[cur][cur][0] == pytest.approx(0.1)


@pytest.mark.unit
@pytest.mark.usefixtures("small_b_cap")
def test_pymdp_export_carries_kept_state_indices() -> None:
    from cogant.gnn.json_export import export_for_pymdp

    plain = GNNMatrices(_graph(), {}, _state_space()).to_plain_dict()
    meta = export_for_pymdp({"matrices": plain})["metadata"]["b_truncation"]
    assert meta["kept_state_indices"] == [1, 3, 5]


@pytest.mark.unit
@pytest.mark.usefixtures("small_b_cap")
def test_truncated_matrices_pass_shape_validation() -> None:
    gm = GNNMatrices(_graph(), {}, _state_space())
    ok, errors = gm.validate_shapes()
    assert ok, errors
    assert GNNValidator().validate_matrices(gm.to_dict()) == []


@pytest.mark.unit
@pytest.mark.usefixtures("small_b_cap")
def test_truncated_package_validates(tmp_path: Path) -> None:
    GNNPackageBuilder(
        graph=_graph(),
        state_space=_state_space(),
        process_model=ProcessModel(id="pm", schema_name="current", stages={}, connections={}),
        mappings={},
    ).build(str(tmp_path))

    result = GNNValidator().validate_package(str(tmp_path), upstream_gnn=False)
    assert result.errors == []
    assert result.valid is True
    assert result.details["matrices"]["truncation"]["applied"] is True


@pytest.mark.unit
def test_validator_rejects_truncation_metadata_that_does_not_match_b() -> None:
    payload = {
        "A": [[1.0, 1.0, 1.0]],
        "B": [[[1.0], [0.0]], [[0.0], [1.0]]],
        "C": [0.0],
        "D": [1 / 3, 1 / 3, 1 / 3],
        "shapes": {"A": [1, 3], "B": [2, 2, 1], "C": [1], "D": [3]},
        "dimensions": {"n_states": 3, "n_obs": 1, "n_actions": 1},
        "truncation": {"applied": True, "n_states_kept": 2, "kept_state_indices": [2, 0]},
    }
    errors = GNNValidator().validate_matrices(payload)
    assert any("kept_state_indices" in e for e in errors)

    payload["truncation"] = {"applied": True, "n_states_kept": 5}
    errors = GNNValidator().validate_matrices(payload)
    assert any("n_states_kept" in e for e in errors)
