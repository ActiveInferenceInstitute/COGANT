from dataclasses import dataclass, field

from _typeshed import Incomplete as Incomplete

from cogant.schemas.graph import ProgramGraph as ProgramGraph

logger: Incomplete

@dataclass
class Stage:
    id: str
    name: str
    description: str | None = ...
    node_ids: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    exit_points: list[str] = field(default_factory=list)
    side_effects: list[str] = field(default_factory=list)
    expected_duration: float | None = ...
    confidence: float = ...
    pattern_type: str | None = ...

@dataclass
class ProcessConnection:
    id: str
    source_stage_id: str
    target_stage_id: str
    trigger: str | None = ...
    condition: str | None = ...
    success_rate: float | None = ...

@dataclass
class ProcessModel:
    id: str
    schema_name: str
    stages: dict[str, Stage]
    connections: dict[str, ProcessConnection]
    entry_stage_id: str | None = ...
    exit_stage_ids: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)

class ProcessExtractor:
    graph: Incomplete
    schema_name: Incomplete
    stages: dict[str, Stage]
    connections: dict[str, ProcessConnection]
    def __init__(self, program_graph: ProgramGraph, schema_name: str) -> None: ...
    def extract(self) -> ProcessModel: ...
    def set_entry_stage(self, stage_id: str) -> None: ...
    def add_stage_dependency(self, source_stage_id: str, target_stage_id: str, trigger: str | None = None) -> None: ...
