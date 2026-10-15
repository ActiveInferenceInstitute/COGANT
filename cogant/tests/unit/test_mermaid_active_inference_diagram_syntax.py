from __future__ import annotations

import re

from cogant.statespace.compiler import Action, ObservationModality, StateSpaceModel
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import StateVariable, StateVariableType
from cogant.viz.mermaid import MermaidGenerator

_NODE_DECL = re.compile(r"^\s*([A-Za-z0-9_]+)\[(.*)\]\s*$")
_EDGE_LABEL = re.compile(r"-->\|(.*?)\|\s")


def _space() -> StateSpaceModel:
    return StateSpaceModel(
        id="m",
        schema_name="m",
        variables={
            "var_8fcf": StateVariable(
                id="var_8fcf",
                name="Calculator - Hidden State",
                var_type=StateVariableType.CATEGORICAL,
                node_id="n1",
            )
        },
        observations={
            "obs_fb57": ObservationModality(
                id="obs_fb57",
                name="get_display - Observation",
                source_node_id="n2",
                modality_type="sensor",
            )
        },
        actions={
            "act_8dd6": Action(id="act_8dd6", name="__init__ - Action", controller_id="n3"),
            "act_c92a": Action(id="act_c92a", name="__init__ - Action", controller_id="n4"),
        },
        transitions={},
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


def _declarations(diagram: str) -> dict[str, str]:
    declared: dict[str, str] = {}
    for line in diagram.splitlines():
        if "-->" in line:
            continue
        match = _NODE_DECL.match(line)
        if match:
            declared[match.group(1)] = match.group(2)
    return declared


def _edge_endpoints(diagram: str) -> set[str]:
    endpoints: set[str] = set()
    for line in diagram.splitlines():
        if "-->" not in line:
            continue
        stripped = re.sub(r'\|"[^"]*"\|', " ", line)
        for token in stripped.split("-->"):
            token = token.strip()
            if token:
                endpoints.add(token)
    return endpoints


def test_chain_nodes_are_the_labelled_variable_observation_and_action_nodes() -> None:
    diagram = MermaidGenerator().generate_active_inference_diagram(_space())

    declared = _declarations(diagram)
    undeclared = sorted(_edge_endpoints(diagram) - set(declared))
    assert undeclared == [], f"edges reference unlabelled nodes: {undeclared}\n{diagram}"
    assert '"Calculator - Hidden State"' in declared.values()
    assert '"get_display - Observation"' in declared.values()


def test_actions_sharing_a_name_keep_distinct_nodes() -> None:
    diagram = MermaidGenerator().generate_active_inference_diagram(_space())

    action_labels = [
        label for label in _declarations(diagram).values() if label == '"__init__ - Action"'
    ]
    assert len(action_labels) == 2


def test_node_and_edge_text_with_mermaid_metacharacters_is_quoted() -> None:
    diagram = MermaidGenerator().generate_active_inference_diagram(_space())

    for node_id, label in _declarations(diagram).items():
        assert label.startswith('"') and label.endswith('"'), (node_id, label)
    edge_labels = _EDGE_LABEL.findall(diagram)
    assert edge_labels, diagram
    for label in edge_labels:
        assert label.startswith('"') and label.endswith('"'), label
    assert '"Beliefs<br/>(Posterior)"' in diagram
    assert 'HS -->|"Likelihood:<br/>P(o|h)"| OBS' in diagram
