"""
ProcessModel: Specification of program processes, pipelines, and workflows.

Models sequential and parallel execution patterns, event-driven architectures,
and business processes extracted from program code.
"""

from typing import Optional, Dict, Any, List, Literal
from enum import Enum
from datetime import datetime, timezone

from pydantic import BaseModel, Field, ConfigDict

from .base import (
    CogantBaseModel,
    StableID,
    EvidenceRef,
    ConfidenceMetric,
)


class ProcessKind(str, Enum):
    """Types of processes."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    RECURSIVE = "recursive"
    EVENT_DRIVEN = "event_driven"
    PIPELINE = "pipeline"
    STATE_MACHINE = "state_machine"


class TriggerKind(str, Enum):
    """How a process stage is triggered."""

    MANUAL = "manual"
    AUTOMATIC = "automatic"
    TIME_BASED = "time_based"
    EVENT = "event"
    CONDITION = "condition"
    MESSAGE = "message"


class SideEffect(CogantBaseModel):
    """
    A side effect produced by a process stage.
    """

    effect_id: str = Field(..., description="Unique identifier")
    description: str = Field(..., description="Description of side effect")
    effect_type: str = Field(
        ..., description="Type of effect (e.g., 'log', 'database_write', 'api_call')"
    )
    is_persistent: bool = Field(
        default=False,
        description="Whether effect persists beyond process completion",
    )
    is_reversible: bool = Field(
        default=False, description="Whether effect can be undone/compensated"
    )


class ProcessStage(CogantBaseModel):
    """
    A single stage or step in a process.
    """

    stage_id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(default=None)

    # Execution
    kind: ProcessKind = Field(
        default=ProcessKind.SEQUENTIAL,
        description="Type of process stage",
    )
    entry_point_id: Optional[StableID] = Field(
        default=None, description="ID of program graph node implementing stage"
    )

    # Relationships
    predecessors: List[str] = Field(
        default_factory=list,
        description="IDs of preceding stages",
    )
    successors: List[str] = Field(
        default_factory=list,
        description="IDs of following stages",
    )

    # Triggering
    trigger_kind: TriggerKind = Field(
        default=TriggerKind.AUTOMATIC,
        description="How stage is triggered",
    )
    trigger_description: Optional[str] = Field(
        default=None, description="Description of trigger condition"
    )

    # Inputs/outputs
    input_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Input parameter specifications",
    )
    output_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Output parameter specifications",
    )

    # Effects
    side_effects: List[SideEffect] = Field(
        default_factory=list,
        description="Side effects produced by this stage",
    )

    # Timing
    typical_duration: Optional[float] = Field(
        default=None, description="Typical execution time (seconds)"
    )
    timeout: Optional[float] = Field(
        default=None, description="Timeout for stage execution (seconds)"
    )

    # Error handling
    error_handlers: Dict[str, str] = Field(
        default_factory=dict,
        description="Error type -> handler mapping",
    )
    is_compensatable: bool = Field(
        default=False, description="Whether stage has compensation logic"
    )
    compensation_stage_id: Optional[str] = Field(
        default=None, description="ID of compensation/rollback stage"
    )

    # Provenance
    provenance: List[EvidenceRef] = Field(
        default_factory=list,
        description="Evidence for stage",
    )


class ProcessPolicy(CogantBaseModel):
    """
    A policy or strategy for executing process stages.
    """

    policy_id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(default=None)

    # Policy type
    policy_type: str = Field(
        ...,
        description="Type of policy (e.g., 'scheduling', 'load_balancing', 'retry')",
    )

    # Applicability
    applies_to_stages: List[str] = Field(
        default_factory=list,
        description="Stage IDs this policy applies to",
    )

    # Specification
    rules: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Policy rules/conditions",
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Policy parameters",
    )

    # Examples of policies:
    # - Retry policy: max_retries=3, backoff_strategy='exponential'
    # - Load balancing: algorithm='round_robin', max_queue_size=100
    # - Scheduling: priority='high', deadline='soft'


class ProcessTimeline(CogantBaseModel):
    """
    Temporal specification of a process.
    """

    timeline_id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Human-readable name")

    # Time model
    is_real_time: bool = Field(
        default=False, description="Whether process has real-time constraints"
    )
    time_unit: str = Field(
        default="milliseconds",
        description="Unit of time measurement",
    )

    # Deadlines & constraints
    start_time: Optional[float] = Field(
        default=None, description="Start time relative to process begin"
    )
    end_time: Optional[float] = Field(
        default=None, description="End time relative to process begin"
    )
    deadline: Optional[float] = Field(
        default=None, description="Deadline for process completion"
    )
    deadline_type: Literal["hard", "soft", "firm"] = Field(
        default="soft",
        description="Type of deadline",
    )

    # Scheduling
    period: Optional[float] = Field(
        default=None, description="If periodic, the period"
    )
    jitter: Optional[float] = Field(
        default=None, description="Allowed jitter/variance in timing"
    )

    # Stage timings
    stage_timings: Dict[str, float] = Field(
        default_factory=dict,
        description="Expected duration for each stage (stage_id -> duration)",
    )


class ProcessModel(CogantBaseModel):
    """
    Specification of a program process, pipeline, or workflow.

    Captures the sequential and parallel execution structure, event-driven
    patterns, error handling, timing constraints, and policies that govern
    program execution.
    """

    process_id: StableID = Field(..., description="Unique identifier")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(
        default=None, description="Detailed description"
    )

    # Process structure
    kind: ProcessKind = Field(
        ..., description="Type of process"
    )
    stages: List[ProcessStage] = Field(
        ...,
        description="All stages in process",
    )
    root_stage_id: Optional[str] = Field(
        default=None, description="ID of root/entry stage"
    )
    leaf_stage_ids: List[str] = Field(
        default_factory=list,
        description="IDs of terminal/exit stages",
    )

    # Execution policies
    policies: List[ProcessPolicy] = Field(
        default_factory=list,
        description="Policies governing execution",
    )

    # Timing
    timelines: List[ProcessTimeline] = Field(
        default_factory=list,
        description="Temporal specifications",
    )

    # Global constraints
    concurrency_constraints: Dict[str, Any] = Field(
        default_factory=dict,
        description="Constraints on parallel execution",
    )
    resource_constraints: Dict[str, Any] = Field(
        default_factory=dict,
        description="Resource limits (memory, connections, etc.)",
    )

    # Provenance
    provenance: List[EvidenceRef] = Field(
        default_factory=list,
        description="Evidence supporting process model",
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
            "example": {
                "process_id": "proc_http_request_flow",
                "name": "HTTP Request Processing Pipeline",
                "kind": "pipeline",
                "stages": [
                    {
                        "stage_id": "parse_request",
                        "name": "Parse HTTP Request",
                        "predecessors": [],
                        "successors": ["route_request"],
                    },
                    {
                        "stage_id": "route_request",
                        "name": "Route to Handler",
                        "predecessors": ["parse_request"],
                        "successors": ["execute_handler"],
                    },
                    {
                        "stage_id": "execute_handler",
                        "name": "Execute Handler Logic",
                        "predecessors": ["route_request"],
                        "successors": ["serialize_response"],
                    },
                    {
                        "stage_id": "serialize_response",
                        "name": "Serialize Response",
                        "predecessors": ["execute_handler"],
                        "successors": [],
                    },
                ],
            }
        }
    )
