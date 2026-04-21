import enum
from collections.abc import Callable as Callable
from dataclasses import dataclass, field
from typing import Any

class StageStatus(enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"

@dataclass
class Stage:
    name: str
    fn: Callable[[dict[str, Any]], dict[str, Any]]
    deps: list[str] = field(default_factory=list)
    timeout: float = ...

@dataclass
class StageResult:
    name: str
    status: StageStatus
    elapsed: float = ...
    error: str | None = ...
    output: dict[str, Any] = field(default_factory=dict)

@dataclass
class DAGResult:
    stage_results: dict[str, StageResult] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    elapsed: float = ...

class PipelineDAG:
    def __init__(self) -> None: ...
    def add_stage(self, stage: Stage) -> None: ...
    def run(self, context: dict[str, Any]) -> DAGResult: ...
