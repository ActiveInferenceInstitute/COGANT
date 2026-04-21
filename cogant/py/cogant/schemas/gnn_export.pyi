from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar, Literal

from _typeshed import Incomplete

from .base import CogantBaseModel as CogantBaseModel

class GNNMetadata(CogantBaseModel):
    export_id: str
    bundle_id: str
    export_timestamp: datetime
    export_version: str
    source_graph_version: str
    gnn_framework: str | None

class RepositoryMetadata(CogantBaseModel):
    repository_name: str
    repository_url: str | None
    commit_hash: str | None
    primary_language: str
    supported_languages: list[str]
    analysis_date: datetime

class SourceCoverage(CogantBaseModel):
    total_files: int
    total_lines: int
    analyzed_files: int
    analyzed_lines: int
    coverage_percentage: float
    excluded_patterns: list[str]

class GraphSection(CogantBaseModel):
    node_count: int
    edge_count: int
    node_features: dict[str, Any]
    edge_features: dict[str, Any]
    edge_list: list[list[int]]
    node_types: dict[int, str]
    edge_types: dict[int, str]

class ObservationModalitySection(CogantBaseModel):
    modality_id: str
    name: str
    observation_space_size: int | None
    observation_space_type: str
    noise_characteristics: dict[str, Any]

class ActionPolicySection(CogantBaseModel):
    action_id: str
    action_name: str
    action_space_size: int | None
    action_space_type: str
    action_cost: float | None

class ConnectionSection(CogantBaseModel):
    source_node_index: int
    target_node_index: int
    edge_type: str
    edge_weight: float
    edge_attributes: dict[str, Any]

class FactorSection(CogantBaseModel):
    factor_id: str
    factor_type: str
    variables: list[str]
    cardinalities: list[int]
    potentials: list[float] | None

class TransitionStructureSection(CogantBaseModel):
    source_state_id: str | None
    target_state_id: str | None
    trigger_action: str | None
    transition_probability: float | None

class LikelihoodStructureSection(CogantBaseModel):
    kind: Literal["observation_likelihood", "transition_probability"]
    distribution_type: str
    parameters: dict[str, float]
    conditioned_on: list[str]

class PreferenceConstraintSection(CogantBaseModel):
    constraint_id: str
    constraint_type: str
    expression: str
    variables: list[str]
    priority: Literal["low", "medium", "high", "critical"]

class TimeSettingSection(CogantBaseModel):
    is_continuous_time: bool
    time_unit: str | None
    time_step: float | None
    max_episode_length: int | None

class ParameterizationSection(CogantBaseModel):
    parameters: dict[str, Any]
    parameter_ranges: dict[str, dict[str, float]]

class OntologyMappingSection(CogantBaseModel):
    mapping_id: str
    source_element_id: str
    target_semantic_role: str
    confidence_score: float
    justification: str | None

class ProvenanceSection(CogantBaseModel):
    total_evidence_count: int
    evidence_by_kind: dict[str, int]
    provenance_coverage: float

class ConfidenceSection(CogantBaseModel):
    mean_confidence: float
    min_confidence: float
    confidence_distribution: dict[str, int]
    unresolved_elements: int

class RenderingHints(CogantBaseModel):
    recommended_layout: str | None
    node_color_scheme: str | None
    edge_color_scheme: str | None
    node_size_metric: str | None
    edge_width_metric: str | None

class ValidationNotes(CogantBaseModel):
    is_valid: bool
    validation_timestamp: datetime
    issues: list[str]
    warnings: list[str]
    recommendations: list[str]

class GNNExportBundle(CogantBaseModel):
    metadata: GNNMetadata
    repository_metadata: RepositoryMetadata
    source_coverage: SourceCoverage
    graph_section: GraphSection
    connections: list[ConnectionSection]
    state_space: dict[str, Any] | None
    observation_modalities: list[ObservationModalitySection]
    actions_policies: list[ActionPolicySection]
    factors: list[FactorSection]
    transition_structure: list[TransitionStructureSection]
    likelihood_structure: list[LikelihoodStructureSection]
    preferences_constraints: list[PreferenceConstraintSection]
    time_settings: TimeSettingSection
    parameterization: ParameterizationSection
    ontology_mapping: list[OntologyMappingSection]
    provenance_section: ProvenanceSection
    confidence_section: ConfidenceSection
    rendering_hints: RenderingHints
    validation_notes: ValidationNotes
    model_config: ClassVar[Incomplete]
