from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar, Literal

from .base import CogantBaseModel as CogantBaseModel
from .base import EvidenceRef as EvidenceRef
from .base import StableID as StableID

class ProcessKind(StrEnum):
    SEQUENTIAL = 'sequential'
    PARALLEL = 'parallel'
    CONDITIONAL = 'conditional'
    LOOP = 'loop'
    RECURSIVE = 'recursive'
    EVENT_DRIVEN = 'event_driven'
    PIPELINE = 'pipeline'
    STATE_MACHINE = 'state_machine'

class TriggerKind(StrEnum):
    MANUAL = 'manual'
    AUTOMATIC = 'automatic'
    TIME_BASED = 'time_based'
    EVENT = 'event'
    CONDITION = 'condition'
    MESSAGE = 'message'

class SideEffect(CogantBaseModel):
    effect_id: str
    description: str
    effect_type: str
    is_persistent: bool
    is_reversible: bool

class ProcessStage(CogantBaseModel):
    stage_id: str
    name: str
    description: str | None
    kind: ProcessKind
    entry_point_id: StableID | None
    predecessors: list[str]
    successors: list[str]
    trigger_kind: TriggerKind
    trigger_description: str | None
    input_parameters: dict[str, Any]
    output_parameters: dict[str, Any]
    side_effects: list[SideEffect]
    typical_duration: float | None
    timeout: float | None
    error_handlers: dict[str, str]
    is_compensatable: bool
    compensation_stage_id: str | None
    provenance: list[EvidenceRef]

class ProcessPolicy(CogantBaseModel):
    policy_id: str
    name: str
    description: str | None
    policy_type: str
    applies_to_stages: list[str]
    rules: list[dict[str, Any]]
    parameters: dict[str, Any]

class ProcessTimeline(CogantBaseModel):
    timeline_id: str
    name: str
    is_real_time: bool
    time_unit: str
    start_time: float | None
    end_time: float | None
    deadline: float | None
    deadline_type: Literal['hard', 'soft', 'firm']
    period: float | None
    jitter: float | None
    stage_timings: dict[str, float]

class ProcessModel(CogantBaseModel):
    process_id: StableID
    name: str
    description: str | None
    kind: ProcessKind
    stages: list[ProcessStage]
    root_stage_id: str | None
    leaf_stage_ids: list[str]
    policies: list[ProcessPolicy]
    timelines: list[ProcessTimeline]
    concurrency_constraints: dict[str, Any]
    resource_constraints: dict[str, Any]
    provenance: list[EvidenceRef]
    source_graph_id: StableID | None
    created_at: datetime
    tags: list[str]
    model_config: ClassVar[Incomplete]
