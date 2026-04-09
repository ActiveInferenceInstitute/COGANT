"""
StateSpaceModel: Formal specification of system state, observations, and actions.

Models discretized, continuous, and hybrid state spaces with observation
and action modalities for use in MDP, POMDP, and control system analysis.
"""

from typing import Optional, Dict, Any, List, Literal, Union
from enum import Enum
from datetime import datetime, timezone

from pydantic import BaseModel, Field, ConfigDict

from .base import (
    CogantBaseModel,
    StableID,
    TypeInfo,
    EvidenceRef,
    ConfidenceMetric,
)


class StateSpaceKind(str, Enum):
    """Types of state spaces."""

    DISCRETE = "discrete"
    CONTINUOUS = "continuous"
    HYBRID = "hybrid"


class StateVariable(CogantBaseModel):
    """
    A single variable in the state space.
    """

    var_id: str = Field(..., description="Unique identifier for variable")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(
        default=None, description="Detailed description"
    )

    # Type information
    value_type: TypeInfo = Field(
        ..., description="Type of state variable values"
    )

    # Domain specification
    domain: Dict[str, Any] = Field(
        default_factory=dict,
        description="Domain specification (min/max for continuous, discrete values list)",
    )
    default_value: Optional[Any] = Field(
        default=None, description="Default initial value"
    )

    # Properties
    is_observable: bool = Field(
        default=False,
        description="Whether this state is directly observable",
    )
    is_controllable: bool = Field(
        default=False,
        description="Whether variable is directly controllable",
    )
    is_discrete: bool = Field(
        default=False,
        description="Whether variable takes discrete values",
    )

    # Provenance
    provenance: List[EvidenceRef] = Field(
        default_factory=list,
        description="Evidence for this variable",
    )


class ObservationModality(CogantBaseModel):
    """
    An observable signal or sensor reading in the environment.
    """

    modality_id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Human-readable name (e.g., 'camera', 'lidar')")
    description: Optional[str] = Field(default=None)

    # Observation structure
    observation_type: TypeInfo = Field(
        ..., description="Type of observations from this modality"
    )
    observation_space: Dict[str, Any] = Field(
        default_factory=dict,
        description="Specification of observation space (dimensions, ranges, etc.)",
    )

    # Noise & uncertainty
    noise_model: Optional[str] = Field(
        default=None, description="Noise model (e.g., 'gaussian', 'poisson')"
    )
    noise_parameters: Dict[str, float] = Field(
        default_factory=dict,
        description="Noise parameters (e.g., stddev, rate)",
    )

    # Temporal properties
    observation_frequency: Optional[float] = Field(
        default=None, description="Observation frequency (Hz)"
    )
    latency: Optional[float] = Field(
        default=None, description="Observation latency (seconds)"
    )

    # Relationships
    observes_state_vars: List[str] = Field(
        default_factory=list,
        description="IDs of state variables this modality observes",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "modality_id": "obs_api_response",
                "name": "API Response Time",
                "observation_type": {
                    "base_type": "float",
                    "is_optional": False,
                    "is_generic": False,
                },
                "observation_space": {
                    "min": 0.0,
                    "max": 10000.0,
                    "unit": "milliseconds",
                },
                "noise_model": "gaussian",
                "noise_parameters": {"stddev": 50.0},
                "observation_frequency": 100.0,
            }
        }
    )


class Action(CogantBaseModel):
    """
    A controllable action in the system.
    """

    action_id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(default=None)

    # Action specification
    action_type: TypeInfo = Field(
        ..., description="Type of action values"
    )
    action_space: Dict[str, Any] = Field(
        default_factory=dict,
        description="Specification of action space (dimensions, ranges, discrete values)",
    )

    # Effects
    affects_state_vars: List[str] = Field(
        default_factory=list,
        description="IDs of state variables affected by this action",
    )
    effect_description: Optional[str] = Field(
        default=None, description="Description of action's effects"
    )

    # Constraints
    preconditions: List[str] = Field(
        default_factory=list,
        description="Conditions that must hold for action to be valid",
    )
    cost: Optional[float] = Field(
        default=None, description="Action cost (e.g., energy, time)"
    )

    # Execution properties
    is_deterministic: bool = Field(
        default=True,
        description="Whether action has deterministic effects",
    )
    execution_time: Optional[float] = Field(
        default=None, description="Expected execution time (seconds)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "action_id": "act_retry_request",
                "name": "Retry API Request",
                "description": "Re-execute failed API request",
                "action_type": {"base_type": "void", "is_optional": False},
                "action_space": {"max_retries": 3, "backoff_strategy": "exponential"},
                "affects_state_vars": ["attempt_count", "last_response_code"],
                "cost": 0.1,
                "preconditions": ["last_request_failed", "attempt_count < 3"],
            }
        }
    )


class Transition(CogantBaseModel):
    """
    State transition specification with conditions and effects.
    """

    transition_id: str = Field(..., description="Unique identifier")
    source_state_id: Optional[str] = Field(
        default=None, description="Source state ID (if state-specific)"
    )
    target_state_id: Optional[str] = Field(
        default=None, description="Target state ID (if state-specific)"
    )

    # Trigger
    trigger_action: Optional[str] = Field(
        default=None, description="Action that triggers transition"
    )
    trigger_condition: Optional[str] = Field(
        default=None, description="Condition expression for transition"
    )

    # Effects
    state_updates: Dict[str, Any] = Field(
        default_factory=dict,
        description="State variable updates on transition",
    )

    # Properties
    is_deterministic: bool = Field(
        default=True, description="Whether transition is deterministic"
    )
    probability: Optional[float] = Field(
        default=None, description="Probability if stochastic"
    )


class Likelihood(CogantBaseModel):
    """
    Observation likelihood or transition probability specification.
    """

    likelihood_id: str = Field(..., description="Unique identifier")
    kind: Literal["observation_likelihood", "transition_probability"] = Field(
        ..., description="Type of likelihood"
    )

    # Conditioning variables
    conditioned_on: List[str] = Field(
        default_factory=list,
        description="State/action variables this likelihood depends on",
    )

    # Distribution
    distribution_type: str = Field(
        ...,
        description="Distribution type (e.g., 'gaussian', 'categorical', 'dirichlet')",
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Distribution parameters (mean, variance, alpha, etc.)",
    )

    # Approximation & uncertainty
    is_learned: bool = Field(
        default=False, description="Whether likelihood was learned from data"
    )
    learning_data_count: Optional[int] = Field(
        default=None, description="Number of samples used for learning"
    )
    confidence: Optional[ConfidenceMetric] = Field(
        default=None, description="Confidence in likelihood"
    )


class StateSpaceModel(CogantBaseModel):
    """
    Formal specification of system state space, observations, and actions.

    Defines the mathematical structure used in MDP, POMDP, and control
    system models derived from program analysis.
    """

    model_id: StableID = Field(..., description="Unique identifier")
    kind: StateSpaceKind = Field(
        ..., description="Type of state space (discrete, continuous, hybrid)"
    )
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(
        default=None, description="Detailed description"
    )

    # Time specification
    is_continuous_time: bool = Field(
        default=False, description="Whether time is continuous (else discrete)"
    )
    time_step: Optional[float] = Field(
        default=None, description="Time step size (for discrete time)"
    )
    max_episode_length: Optional[int] = Field(
        default=None, description="Maximum steps per episode"
    )

    # State definition
    state_variables: List[StateVariable] = Field(
        ...,
        description="All state variables",
    )

    # Observations
    observation_modalities: List[ObservationModality] = Field(
        default_factory=list,
        description="Observable signals/sensors",
    )

    # Actions
    actions: List[Action] = Field(
        default_factory=list,
        description="Controllable actions",
    )

    # Dynamics
    transitions: List[Transition] = Field(
        default_factory=list,
        description="State transition specifications",
    )

    # Likelihoods
    likelihoods: List[Likelihood] = Field(
        default_factory=list,
        description="Observation likelihoods and transition probabilities",
    )

    # Preferences & rewards
    preferences: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Preference/reward specification (separate from constraints)",
    )

    # Constraints
    constraints: List[str] = Field(
        default_factory=list,
        description="System constraints (must always hold)",
    )

    # Provenance
    provenance: List[EvidenceRef] = Field(
        default_factory=list,
        description="Evidence supporting model structure",
    )

    # Metadata
    source_graph_id: Optional[StableID] = Field(
        default=None, description="ID of source program graph"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When model was created",
    )
    tags: List[str] = Field(
        default_factory=list, description="User-defined tags"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Formal state space, observation, and action specification",
            "version": "1.0.0",
        }
    )
