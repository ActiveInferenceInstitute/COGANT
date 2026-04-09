"""
GNNExportBundle: Comprehensive export format for Generalized Notation Notation (GNN).

"GNN" here refers to the Active Inference Institute's Generalized Notation Notation
(https://github.com/ActiveInferenceInstitute/GeneralizedNotationNotation), a structured
notation for Active Inference state-space and process models — not graph neural networks.

Packages all analysis artifacts (graph structure, semantic mappings, state space,
process model, provenance, confidence) into a format suitable for downstream
GNN tooling, renderers, and simulation.
"""

from typing import Optional, Dict, Any, List, Literal
from enum import Enum
from datetime import datetime, timezone

from pydantic import BaseModel, Field, ConfigDict

from .base import CogantBaseModel, StableID


class GNNMetadata(CogantBaseModel):
    """Metadata about the GNN export."""

    export_id: str = Field(..., description="Unique export identifier")
    bundle_id: str = Field(..., description="Source bundle ID")
    export_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When export was created",
    )
    export_version: str = Field(
        default="1.0.0", description="GNN export format version"
    )
    source_graph_version: str = Field(
        default="1.0.0", description="Program graph schema version"
    )
    gnn_framework: Optional[str] = Field(
        default=None,
        description="Target GNN framework (e.g., 'pytorch_geometric', 'dgl', 'spektral')",
    )


class RepositoryMetadata(CogantBaseModel):
    """Metadata about the analyzed repository."""

    repository_name: str = Field(..., description="Name of repository")
    repository_url: Optional[str] = Field(
        default=None, description="URL of repository"
    )
    commit_hash: Optional[str] = Field(
        default=None, description="Commit hash analyzed"
    )
    primary_language: str = Field(..., description="Primary programming language")
    supported_languages: List[str] = Field(
        default_factory=list, description="All languages in repository"
    )
    analysis_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Date of analysis",
    )


class SourceCoverage(CogantBaseModel):
    """Coverage metrics for source code analysis."""

    total_files: int = Field(default=0, description="Total files analyzed")
    total_lines: int = Field(default=0, description="Total lines of code")
    analyzed_files: int = Field(
        default=0, description="Files included in analysis"
    )
    analyzed_lines: int = Field(
        default=0, description="Lines included in analysis"
    )
    coverage_percentage: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Coverage percentage"
    )
    excluded_patterns: List[str] = Field(
        default_factory=list,
        description="Patterns excluded from analysis (e.g., 'test_*.py')",
    )


class GraphSection(CogantBaseModel):
    """Graph structure exported in GNN format."""

    node_count: int = Field(default=0, description="Number of nodes")
    edge_count: int = Field(default=0, description="Number of edges")
    node_features: Dict[str, Any] = Field(
        default_factory=dict,
        description="Node feature specifications",
    )
    edge_features: Dict[str, Any] = Field(
        default_factory=dict,
        description="Edge feature specifications",
    )
    edge_list: List[List[int]] = Field(
        default_factory=list,
        description="Edge list as node index pairs",
    )
    node_types: Dict[int, str] = Field(
        default_factory=dict,
        description="Map from node index to type",
    )
    edge_types: Dict[int, str] = Field(
        default_factory=dict,
        description="Map from edge index to type",
    )


class ObservationModalitySection(CogantBaseModel):
    """Observation modalities in GNN format."""

    modality_id: str = Field(..., description="Modality identifier")
    name: str = Field(..., description="Human-readable name")
    observation_space_size: Optional[int] = Field(
        default=None, description="Dimension of observation space"
    )
    observation_space_type: str = Field(
        default="continuous",
        description="Type of observation space",
    )
    noise_characteristics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Noise model and parameters",
    )


class ActionPolicySection(CogantBaseModel):
    """Actions and policies in GNN format."""

    action_id: str = Field(..., description="Action identifier")
    action_name: str = Field(..., description="Human-readable name")
    action_space_size: Optional[int] = Field(
        default=None, description="Dimension of action space"
    )
    action_space_type: str = Field(
        default="discrete",
        description="Type of action space",
    )
    action_cost: Optional[float] = Field(
        default=None, description="Cost of action execution"
    )


class ConnectionSection(CogantBaseModel):
    """Connectivity structure for GNN."""

    source_node_index: int = Field(..., description="Source node index")
    target_node_index: int = Field(..., description="Target node index")
    edge_type: str = Field(..., description="Type of edge")
    edge_weight: float = Field(default=1.0, description="Edge weight")
    edge_attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional edge attributes",
    )


class FactorSection(CogantBaseModel):
    """Factors in probabilistic model."""

    factor_id: str = Field(..., description="Factor identifier")
    factor_type: str = Field(
        ...,
        description="Type of factor (e.g., 'unary', 'pairwise', 'higher_order')",
    )
    variables: List[str] = Field(
        ..., description="Variable IDs in factor"
    )
    cardinalities: List[int] = Field(
        ..., description="Cardinality of each variable"
    )
    potentials: Optional[List[float]] = Field(
        default=None,
        description="Factor potential values",
    )


class TransitionStructureSection(CogantBaseModel):
    """State transition structure."""

    source_state_id: Optional[str] = Field(default=None)
    target_state_id: Optional[str] = Field(default=None)
    trigger_action: Optional[str] = Field(default=None)
    transition_probability: Optional[float] = Field(default=None)


class LikelihoodStructureSection(CogantBaseModel):
    """Observation likelihood and transition probabilities."""

    kind: Literal["observation_likelihood", "transition_probability"]
    distribution_type: str = Field(
        ...,
        description="Distribution type (gaussian, categorical, etc.)",
    )
    parameters: Dict[str, float] = Field(
        default_factory=dict,
        description="Distribution parameters",
    )
    conditioned_on: List[str] = Field(
        default_factory=list,
        description="Variables this is conditioned on",
    )


class PreferenceConstraintSection(CogantBaseModel):
    """Preferences and constraints."""

    constraint_id: str = Field(..., description="Constraint identifier")
    constraint_type: str = Field(
        ...,
        description="Type (e.g., 'reward', 'safety', 'liveness')",
    )
    expression: str = Field(
        ..., description="Constraint expression"
    )
    variables: List[str] = Field(
        default_factory=list,
        description="Variables involved",
    )
    priority: Literal["low", "medium", "high", "critical"] = Field(
        default="medium",
        description="Priority level",
    )


class TimeSettingSection(CogantBaseModel):
    """Time model and temporal structure."""

    is_continuous_time: bool = Field(
        default=False, description="Continuous or discrete time"
    )
    time_unit: Optional[str] = Field(
        default=None,
        description="Unit of time (seconds, steps, etc.)",
    )
    time_step: Optional[float] = Field(
        default=None, description="Time step size"
    )
    max_episode_length: Optional[int] = Field(
        default=None, description="Maximum steps per episode"
    )


class ParameterizationSection(CogantBaseModel):
    """Model parameters."""

    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameter name -> value mapping",
    )
    parameter_ranges: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Parameter name -> {min, max, default} ranges",
    )


class OntologyMappingSection(CogantBaseModel):
    """Mappings between code and semantic ontology."""

    mapping_id: str = Field(..., description="Mapping identifier")
    source_element_id: str = Field(..., description="Code element ID")
    target_semantic_role: str = Field(
        ..., description="Target semantic role"
    )
    confidence_score: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence [0, 1]"
    )
    justification: Optional[str] = Field(default=None)


class ProvenanceSection(CogantBaseModel):
    """Provenance and evidence information."""

    total_evidence_count: int = Field(default=0)
    evidence_by_kind: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of evidence by kind",
    )
    provenance_coverage: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of elements with provenance",
    )


class ConfidenceSection(CogantBaseModel):
    """Confidence metrics and uncertainty quantification."""

    mean_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Mean confidence"
    )
    min_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Minimum confidence"
    )
    confidence_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Histogram of confidence scores",
    )
    unresolved_elements: int = Field(
        default=0,
        description="Count of elements with incomplete information",
    )


class RenderingHints(CogantBaseModel):
    """Hints for visualization and rendering."""

    recommended_layout: Optional[str] = Field(
        default=None,
        description="Recommended graph layout (force-directed, hierarchical, etc.)",
    )
    node_color_scheme: Optional[str] = Field(
        default=None, description="Color scheme by node type"
    )
    edge_color_scheme: Optional[str] = Field(
        default=None, description="Color scheme by edge type"
    )
    node_size_metric: Optional[str] = Field(
        default=None,
        description="Metric for sizing nodes (degree, betweenness, etc.)",
    )
    edge_width_metric: Optional[str] = Field(
        default=None, description="Metric for edge widths"
    )


class ValidationNotes(CogantBaseModel):
    """Validation and quality notes."""

    is_valid: bool = Field(default=True)
    validation_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When validation was performed",
    )
    issues: List[str] = Field(
        default_factory=list, description="Any issues found"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Non-fatal warnings"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Recommendations for improvement",
    )


class GNNExportBundle(CogantBaseModel):
    """
    Comprehensive GNN export bundle containing all analysis artifacts.

    Packages program graph, semantic mappings, state space models, process models,
    and validation results in a format optimized for downstream Generalized Notation
    Notation (Active Inference) tooling: renderers, simulators, and validators.
    """

    # Metadata
    metadata: GNNMetadata = Field(..., description="Export metadata")
    repository_metadata: RepositoryMetadata = Field(
        ..., description="Repository information"
    )
    source_coverage: SourceCoverage = Field(
        default_factory=SourceCoverage,
        description="Source code coverage metrics",
    )

    # Graph structure
    graph_section: GraphSection = Field(
        default_factory=GraphSection,
        description="Graph nodes and edges",
    )
    connections: List[ConnectionSection] = Field(
        default_factory=list,
        description="Detailed edge information",
    )

    # Semantic model
    state_space: Optional[Dict[str, Any]] = Field(
        default=None, description="State space specification"
    )
    observation_modalities: List[ObservationModalitySection] = Field(
        default_factory=list,
        description="Observable signals",
    )
    actions_policies: List[ActionPolicySection] = Field(
        default_factory=list,
        description="Actions and policies",
    )

    # Probabilistic structure
    factors: List[FactorSection] = Field(
        default_factory=list,
        description="Probabilistic factors",
    )
    transition_structure: List[TransitionStructureSection] = Field(
        default_factory=list,
        description="State transitions",
    )
    likelihood_structure: List[LikelihoodStructureSection] = Field(
        default_factory=list,
        description="Likelihoods and probabilities",
    )

    # Constraints and preferences
    preferences_constraints: List[PreferenceConstraintSection] = Field(
        default_factory=list,
        description="System preferences and constraints",
    )

    # Time and parameters
    time_settings: TimeSettingSection = Field(
        default_factory=TimeSettingSection,
        description="Temporal structure",
    )
    parameterization: ParameterizationSection = Field(
        default_factory=ParameterizationSection,
        description="Model parameters",
    )

    # Mappings
    ontology_mapping: List[OntologyMappingSection] = Field(
        default_factory=list,
        description="Code to semantic mappings",
    )

    # Quality & validation
    provenance_section: ProvenanceSection = Field(
        default_factory=ProvenanceSection,
        description="Provenance information",
    )
    confidence_section: ConfidenceSection = Field(
        default_factory=ConfidenceSection,
        description="Confidence metrics",
    )
    rendering_hints: RenderingHints = Field(
        default_factory=RenderingHints,
        description="Visualization hints",
    )
    validation_notes: ValidationNotes = Field(
        default_factory=ValidationNotes,
        description="Validation and quality notes",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Comprehensive GNN export bundle",
            "version": "1.0.0",
        }
    )
