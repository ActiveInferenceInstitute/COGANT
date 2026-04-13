from __future__ import annotations

from typing import Any

from cogant.process.extractor import ProcessModel as ProcessModel
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.statespace.compiler import StateSpaceModel as StateSpaceModel

class GNNJSONExporter:
    graph: Any
    state_space: Any
    process: Any
    mappings: Any
    def __init__(self, program_graph: ProgramGraph, state_space_model: StateSpaceModel, process_model: ProcessModel, semantic_mappings: dict[str, Any]) -> None: ...
    def export(self) -> dict[str, Any]: ...
    def export_to_string(self, indent: int | None = 2) -> str: ...

def export_for_pymdp(bundle: dict[str, Any]) -> dict[str, Any]: ...
def export_summary(bundle: dict[str, Any]) -> dict[str, Any]: ...
