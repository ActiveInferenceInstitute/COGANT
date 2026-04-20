from dataclasses import dataclass, field
from typing import Any

from cogant.process.extractor import ProcessModel as ProcessModel

@dataclass
class GanttStage:
    stage_id: str
    name: str
    start_time: float = ...
    duration: float = ...
    dependencies: list[str] = field(default_factory=list)
    criticality: float = ...

@dataclass
class Timeline:
    stages: list[GanttStage]
    total_duration: float
    critical_path: list[str]
    parallel_groups: list[list[str]]

class TimelineBuilder:
    process_model: Any
    gantt_stages: dict[str, GanttStage]
    timeline: Timeline | None
    def __init__(self, process_model: ProcessModel) -> None: ...
    def build(self) -> Timeline: ...
    def get_timeline(self) -> Timeline | None: ...
    def get_stage_at_time(self, time: float) -> str | None: ...
    def get_stages_in_range(self, start_time: float, end_time: float) -> list[str]: ...
    def export_gantt_data(self) -> dict[str, object]: ...
