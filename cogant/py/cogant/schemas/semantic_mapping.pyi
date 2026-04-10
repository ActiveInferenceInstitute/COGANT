from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar

from _typeshed import Incomplete as Incomplete

from .base import CogantBaseModel as CogantBaseModel
from .base import ConfidenceMetric as ConfidenceMetric
from .base import EvidenceRef as EvidenceRef
from .base import StableID as StableID

class SemanticRole(StrEnum):
    HIDDEN_STATE = 'hidden_state'
    OBSERVATION = 'observation'
    ACTION = 'action'
    POLICY = 'policy'
    PREFERENCE = 'preference'
    UTILITY = 'utility'
    OBJECTIVE = 'objective'
    CONTEXT = 'context'
    FACTOR = 'factor'
    PARAMETER = 'parameter'
    PRECISION = 'precision'
    TEMPORAL_INDEX = 'temporal_index'
    PROCESS_STAGE = 'process_stage'
    TRANSITION = 'transition'
    OUTCOME = 'outcome'
    COMPONENT = 'component'
    INTERFACE = 'interface'
    CONFIGURATION = 'configuration'
    CONSTRAINT = 'constraint'

class MappingRule(CogantBaseModel):
    rule_type: str
    source_pattern: str
    target_role: SemanticRole
    transformation: str | None
    priority: int

class SourceGraphElement(CogantBaseModel):
    element_id: StableID
    element_type: str
    label: str
    element_kind: str

class TargetSemanticElement(CogantBaseModel):
    semantic_id: str
    role: SemanticRole
    label: str
    model_type: str
    domain_specific_properties: dict[str, Any]

class ReviewStatus(StrEnum):
    UNREVIEWED = 'unreviewed'
    REVIEWED = 'reviewed'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    FLAGGED = 'flagged'

class SemanticMapping(CogantBaseModel):
    mapping_id: StableID
    created_at: datetime
    created_by: str | None
    source_graph_elements: list[SourceGraphElement]
    target_semantic_elements: list[TargetSemanticElement]
    mapping_rule: MappingRule | None
    mapping_type: str
    justification: str | None
    confidence: ConfidenceMetric
    review_status: ReviewStatus
    review_notes: str | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    evidence_references: list[EvidenceRef]
    tags: list[str]
    annotations: dict[str, Any]
    model_config: ClassVar[Incomplete]

class SemanticMappingCollection(CogantBaseModel):
    collection_id: StableID
    program_graph_id: StableID
    mappings: list[SemanticMapping]
    mapping_statistics: dict[str, Any]
    created_at: datetime
