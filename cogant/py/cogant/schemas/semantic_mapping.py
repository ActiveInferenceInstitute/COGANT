"""
SemanticMapping: Mappings between program graph elements and semantic model roles.

Bridges source code representations to domain-specific semantic models
(e.g., MDP states, POMDP observations, control system components).
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import ConfigDict, Field

from .base import (
    CogantBaseModel,
    ConfidenceMetric,
    EvidenceRef,
    StableID,
)


class SemanticRole(StrEnum):
    """
    Roles that program graph elements can play in semantic models.
    Enables flexible mapping to diverse target formalisms.
    """

    # MDP/POMDP structure
    HIDDEN_STATE = "hidden_state"  # Unobservable program state
    OBSERVATION = "observation"  # Observable state component
    ACTION = "action"  # Agent action in MDP/POMDP
    POLICY = "policy"  # Decision-making policy

    # Preferences & objectives
    PREFERENCE = "preference"  # User/system preference
    UTILITY = "utility"  # Utility/reward function
    OBJECTIVE = "objective"  # System objective

    # Model structure
    CONTEXT = "context"  # Contextual information
    FACTOR = "factor"  # Factor in probabilistic model
    PARAMETER = "parameter"  # Model parameter
    PRECISION = "precision"  # Precision/uncertainty measure

    # Temporal structure
    TEMPORAL_INDEX = "temporal_index"  # Timestamp or sequence position
    PROCESS_STAGE = "process_stage"  # Stage in process model
    TRANSITION = "transition"  # State transition
    OUTCOME = "outcome"  # Outcome/result of action

    # System structure
    COMPONENT = "component"  # System component
    INTERFACE = "interface"  # Component interface
    CONFIGURATION = "configuration"  # Configuration parameter
    CONSTRAINT = "constraint"  # System constraint


class MappingRule(CogantBaseModel):
    """
    Rule describing how source elements map to semantic roles.
    """

    rule_type: str = Field(
        ...,
        description="Type of mapping rule (e.g., 'pattern_match', 'type_constraint', 'annotation')",
    )
    source_pattern: str = Field(
        ...,
        description="Pattern or query identifying source elements (e.g., 'functions with @action decorator')",
    )
    target_role: SemanticRole = Field(..., description="Target semantic role")
    transformation: str | None = Field(
        default=None,
        description="Optional transformation to apply (e.g., 'extract_return_value')",
    )
    priority: int = Field(
        default=100, description="Priority for rule application (higher = earlier)"
    )


class SourceGraphElement(CogantBaseModel):
    """
    Reference to an element in the program graph.
    """

    element_id: StableID = Field(..., description="ID of node or edge in program graph")
    element_type: str = Field(..., description="'node' or 'edge'")
    label: str = Field(..., description="Human-readable label of element")
    element_kind: str = Field(..., description="Kind of element (e.g., 'function', 'imports')")


class TargetSemanticElement(CogantBaseModel):
    """
    Element in the target semantic model.
    """

    semantic_id: str = Field(..., description="Unique identifier in semantic model")
    role: SemanticRole = Field(..., description="Semantic role in model")
    label: str = Field(..., description="Human-readable label")
    model_type: str = Field(
        ..., description="Type of semantic model (e.g., 'mdp', 'pomdp', 'markov_chain')"
    )
    domain_specific_properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Domain-specific properties (e.g., state_space_size, action_range)",
    )


class ReviewStatus(StrEnum):
    """Status of semantic mapping review."""

    UNREVIEWED = "unreviewed"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"  # Requires expert review


class SemanticMapping(CogantBaseModel):
    """
    Bidirectional mapping between program graph elements and semantic model roles.

    Enables translation from code structure to mathematical/formal models
    for downstream analysis (verification, optimization, learning).
    """

    mapping_id: StableID = Field(..., description="Unique identifier for this mapping")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When mapping was created",
    )
    created_by: str | None = Field(default=None, description="User or tool that created mapping")

    # Graph elements
    source_graph_elements: list[SourceGraphElement] = Field(
        ...,
        description="Program graph elements involved in this mapping",
    )
    target_semantic_elements: list[TargetSemanticElement] = Field(
        ...,
        description="Target semantic model elements",
    )

    # Mapping details
    mapping_rule: MappingRule | None = Field(
        default=None,
        description="Rule that generated this mapping (if automated)",
    )
    mapping_type: str = Field(
        default="manual",
        description="How mapping was created ('manual', 'heuristic', 'learned')",
    )
    justification: str | None = Field(
        default=None, description="Explanation of why this mapping is valid"
    )

    # Confidence & quality
    confidence: ConfidenceMetric = Field(
        ...,
        description="Confidence that mapping is semantically correct",
    )

    # Review & validation
    review_status: ReviewStatus = Field(
        default=ReviewStatus.UNREVIEWED,
        description="Review and approval status",
    )
    review_notes: str | None = Field(default=None, description="Notes from reviewer")
    reviewed_by: str | None = Field(default=None, description="User who reviewed mapping")
    reviewed_at: datetime | None = Field(default=None, description="When mapping was reviewed")

    # Provenance & evidence
    evidence_references: list[EvidenceRef] = Field(
        default_factory=list,
        description="Evidence supporting mapping validity",
    )

    # Metadata
    tags: list[str] = Field(default_factory=list, description="User-defined tags")
    annotations: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom annotations",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "mapping_id": "map_abc123def456",
                "source_graph_elements": [
                    {
                        "element_id": "func_auth_check",
                        "element_type": "node",
                        "label": "check_authentication",
                        "element_kind": "function",
                    }
                ],
                "target_semantic_elements": [
                    {
                        "semantic_id": "obs_user_authenticated",
                        "role": "observation",
                        "label": "user_authenticated",
                        "model_type": "pomdp",
                        "domain_specific_properties": {
                            "observation_space": "boolean",
                            "probability_distribution": "bernoulli",
                        },
                    }
                ],
                "confidence": {
                    "score": 0.95,
                    "rationale": "Function directly returns boolean auth status",
                    "evidence_types": ["static_analysis", "type_signature"],
                },
                "review_status": "approved",
            }
        }
    )


class SemanticMappingCollection(CogantBaseModel):
    """
    Collection of all semantic mappings for a program.
    """

    collection_id: StableID = Field(..., description="Unique identifier for this collection")
    program_graph_id: StableID = Field(..., description="ID of source program graph")
    mappings: list[SemanticMapping] = Field(
        default_factory=list,
        description="All mappings",
    )
    mapping_statistics: dict[str, Any] = Field(
        default_factory=dict,
        description="Statistics about mappings (coverage, confidence distribution, etc.)",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When collection was created",
    )
