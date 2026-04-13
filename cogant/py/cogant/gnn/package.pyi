from typing import Any

from cogant.process.extractor import ProcessModel as ProcessModel
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.statespace.compiler import StateSpaceModel as StateSpaceModel

class GNNPackageBuilder:
    PACKAGE_VERSION: str
    REQUIRED_FILES: Any
    graph: Any
    state_space: Any
    process_model: Any
    mappings: Any
    config: Any
    timestamp: Any
    checksums: dict[str, str]
    def __init__(self, graph: ProgramGraph, state_space: StateSpaceModel, process_model: ProcessModel, mappings: dict[str, Any], config: dict[str, Any] | None = None) -> None: ...
    def build(self, output_dir: str) -> dict[str, Any]: ...
