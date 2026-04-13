from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

class MappingKind(StrEnum):
    OBSERVATION = 'observation'
    ACTION = 'action'
    HIDDEN_STATE = 'hidden_state'
    CONTEXT = 'context'
    POLICY = 'policy'
    CONSTRAINT = 'constraint'
    PREFERENCE = 'preference'
    DATA_FLOW = 'data_flow'
    CONTROL_FLOW = 'control_flow'
    ERROR_HANDLING = 'error_handling'
    ORCHESTRATION = 'orchestration'
    RETRY_PATTERN = 'retry_pattern'
    CIRCUIT_BREAKER = 'circuit_breaker'
    FEATURE_FLAG = 'feature_flag'

class ConfidenceTier(StrEnum):
    STATIC_ONLY = 'static_only'
    STATIC_PLUS_RUNTIME = 'static_plus_runtime'
    RUNTIME_ONLY = 'runtime_only'
    HUMAN_REVIEWED = 'human_reviewed'

@dataclass
class ProvenanceRecord:
    source: str
    timestamp: datetime = field(default_factory=Incomplete)
    metadata: dict[str, Any] = field(default_factory=dict)
    confidence: float = ...

@dataclass
class SemanticMapping:
    id: str
    kind: MappingKind
    graph_fragment_node_ids: list[str] = field(default_factory=list)
    graph_fragment_edge_ids: list[str] = field(default_factory=list)
    semantic_label: str = ...
    description: str = ...
    confidence_score: float = ...
    confidence_tier: ConfidenceTier = ...
    provenance: list[ProvenanceRecord] = field(default_factory=list)
    evidence_count: int = ...
    evidence_diversity: float = ...
    parser_certainty: float = ...
    conflict_penalties: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = ...
    review_feedback: str | None = ...
    reviewed_by: str | None = ...
    reviewed_at: datetime | None = ...
    created_at: datetime = field(default_factory=Incomplete)
    updated_at: datetime = field(default_factory=Incomplete)
    def __hash__(self) -> int: ...
    def __eq__(self, other: object) -> bool: ...
    def compute_confidence(self) -> float: ...
