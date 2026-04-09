"""Semantic mapping and provenance schema definitions."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


class MappingKind(str, Enum):
    """Types of semantic mappings."""
    # Observation and action modalities
    OBSERVATION = "observation"
    ACTION = "action"
    HIDDEN_STATE = "hidden_state"
    CONTEXT = "context"

    # Policy and control structures
    POLICY = "policy"
    CONSTRAINT = "constraint"
    PREFERENCE = "preference"

    # Data and control flow
    DATA_FLOW = "data_flow"
    CONTROL_FLOW = "control_flow"
    ERROR_HANDLING = "error_handling"

    # System patterns
    ORCHESTRATION = "orchestration"
    RETRY_PATTERN = "retry_pattern"
    CIRCUIT_BREAKER = "circuit_breaker"
    FEATURE_FLAG = "feature_flag"


class ConfidenceTier(str, Enum):
    """Confidence tiers for semantic mappings."""
    STATIC_ONLY = "static_only"
    """Based only on static analysis."""

    STATIC_PLUS_RUNTIME = "static_plus_runtime"
    """Combines static and runtime evidence."""

    RUNTIME_ONLY = "runtime_only"
    """Based only on runtime/dynamic evidence."""

    HUMAN_REVIEWED = "human_reviewed"
    """Manually reviewed and approved."""


@dataclass
class ProvenanceRecord:
    """Record of where evidence for a mapping came from."""

    source: str
    """Source of evidence (e.g., 'static_analysis', 'dynamic_trace', 'manual_review')."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    """When the evidence was collected."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional provenance metadata."""

    confidence: float = 0.5
    """Confidence of this evidence (0.0 to 1.0)."""


@dataclass
class SemanticMapping:
    """Maps a program graph fragment to semantic concepts."""

    id: str
    """Unique mapping identifier."""

    kind: MappingKind
    """Type of semantic mapping."""

    graph_fragment_node_ids: List[str] = field(default_factory=list)
    """IDs of graph nodes involved in this mapping."""

    graph_fragment_edge_ids: List[str] = field(default_factory=list)
    """IDs of graph edges involved in this mapping."""

    semantic_label: str = ""
    """Human-readable semantic label."""

    description: str = ""
    """Description of the mapping."""

    confidence_score: float = 0.0
    """Overall confidence (0.0 to 1.0)."""

    confidence_tier: ConfidenceTier = ConfidenceTier.STATIC_ONLY
    """Tier of confidence based on evidence sources."""

    provenance: List[ProvenanceRecord] = field(default_factory=list)
    """Evidence records supporting this mapping."""

    evidence_count: int = 0
    """Count of total evidence pieces."""

    evidence_diversity: float = 0.0
    """Score for diversity of evidence sources (0.0 to 1.0)."""

    parser_certainty: float = 0.0
    """Parser/static analysis certainty (0.0 to 1.0)."""

    conflict_penalties: List[float] = field(default_factory=list)
    """Penalties applied for conflicting evidence."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional mapping metadata."""

    status: str = "auto_proposed"
    """Status: auto_proposed, accepted, rejected, edited, split, merged."""

    review_feedback: Optional[str] = None
    """Feedback from human review."""

    reviewed_by: Optional[str] = None
    """User who reviewed this mapping."""

    reviewed_at: Optional[datetime] = None
    """When the mapping was reviewed."""

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    """Creation timestamp."""

    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    """Last update timestamp."""

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemanticMapping):
            return NotImplemented
        return self.id == other.id

    def compute_confidence(self) -> float:
        """Compute overall confidence from components.

        Returns:
            Computed confidence score (0.0 to 1.0).
        """
        if not self.provenance:
            return 0.0

        # Average confidence from evidence
        avg_evidence = sum(p.confidence for p in self.provenance) / len(self.provenance)

        # Apply diversity bonus
        diversity_bonus = self.evidence_diversity * 0.1

        # Apply parser certainty factor
        certainty_factor = self.parser_certainty

        # Apply conflict penalties
        conflict_penalty = sum(self.conflict_penalties) * 0.05

        confidence = (avg_evidence + diversity_bonus) * certainty_factor - conflict_penalty
        return max(0.0, min(1.0, confidence))
