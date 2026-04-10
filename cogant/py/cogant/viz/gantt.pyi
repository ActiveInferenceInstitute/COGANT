from typing import Any

from _typeshed import Incomplete as Incomplete

from cogant.process.timeline import Timeline as Timeline

logger: Incomplete

class GanttRenderer:
    stages: list[dict[str, Any]]
    dependencies: list[dict[str, Any]]
    timeline: list[dict[str, Any]]
    critical_path: list[str]
    parallel_groups: list[list[str]]
    def __init__(self) -> None: ...
    def from_process_model(self, process_model: dict[str, Any]) -> GanttRenderer: ...
    def from_timeline(self, timeline: Timeline) -> GanttRenderer: ...
    def render_html(self, output_path: str) -> str: ...
    def render_json(self) -> str: ...
