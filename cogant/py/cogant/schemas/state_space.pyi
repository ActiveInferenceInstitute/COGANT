from .base import CogantBaseModel as CogantBaseModel, ConfidenceMetric as ConfidenceMetric, EvidenceRef as EvidenceRef, StableID as StableID, TypeInfo as TypeInfo
from _typeshed import Incomplete
from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar, Literal

class StateSpaceKind(StrEnum):
    DISCRETE = 'discrete'
    CONTINUOUS = 'continuous'
    HYBRID = 'hybrid'

class StateVariable(CogantBaseModel):
    var_id: str
    name: str
    description: str | None
    value_type: TypeInfo
    domain: dict[str, Any]
    default_value: Any | None
    is_observable: bool
    is_controllable: bool
    is_discrete: bool
    provenance: list[EvidenceRef]

class ObservationModality(CogantBaseModel):
    modality_id: str
    name: str
    description: str | None
    observation_type: TypeInfo
    observation_space: dict[str, Any]
    noise_model: str | None
    noise_parameters: dict[str, float]
    observation_frequency: float | None
    latency: float | None
    observes_state_vars: list[str]
    model_config: ClassVar[Incomplete]

class Action(CogantBaseModel):
    action_id: str
    name: str
    description: str | None
    action_type: TypeInfo
    action_space: dict[str, Any]
    affects_state_vars: list[str]
    effect_description: str | None
    preconditions: list[str]
    cost: float | None
    is_deterministic: bool
    execution_time: float | None
    model_config: ClassVar[Incomplete]

class Transition(CogantBaseModel):
    transition_id: str
    source_state_id: str | None
    target_state_id: str | None
    trigger_action: str | None
    trigger_condition: str | None
    state_updates: dict[str, Any]
    is_deterministic: bool
    probability: float | None

class Likelihood(CogantBaseModel):
    likelihood_id: str
    kind: Literal['observation_likelihood', 'transition_probability']
    conditioned_on: list[str]
    distribution_type: str
    parameters: dict[str, Any]
    is_learned: bool
    learning_data_count: int | None
    confidence: ConfidenceMetric | None

class StateSpaceModel(CogantBaseModel):
    model_id: StableID
    kind: StateSpaceKind
    name: str
    description: str | None
    is_continuous_time: bool
    time_step: float | None
    max_episode_length: int | None
    state_variables: list[StateVariable]
    observation_modalities: list[ObservationModality]
    actions: list[Action]
    transitions: list[Transition]
    likelihoods: list[Likelihood]
    preferences: dict[str, Any] | None
    constraints: list[str]
    provenance: list[EvidenceRef]
    source_graph_id: StableID | None
    created_at: datetime
    tags: list[str]
    model_config: ClassVar[Incomplete]
