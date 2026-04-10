from typing import Any

from _typeshed import Incomplete as Incomplete

from cogant.process.extractor import ProcessModel as ProcessModel
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.statespace.compiler import StateSpaceModel as StateSpaceModel

logger: Incomplete

class GNNJSONExporter:
    graph: Incomplete
    state_space: Incomplete
    process: Incomplete
    mappings: Incomplete
    def __init__(self, program_graph: ProgramGraph, state_space_model: StateSpaceModel, process_model: ProcessModel, semantic_mappings: dict[str, Any]) -> None: ...
    def export(self) -> dict[str, Any]: ...
    def export_to_string(self, indent: int | None = 2) -> str: ...
