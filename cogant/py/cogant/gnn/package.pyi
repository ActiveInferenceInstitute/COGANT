from typing import Any

from _typeshed import Incomplete as Incomplete

from cogant.process.extractor import ProcessModel as ProcessModel
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.statespace.compiler import StateSpaceModel as StateSpaceModel

logger: Incomplete

class GNNPackageBuilder:
    PACKAGE_VERSION: str
    REQUIRED_FILES: Incomplete
    graph: Incomplete
    state_space: Incomplete
    process_model: Incomplete
    mappings: Incomplete
    config: Incomplete
    timestamp: Incomplete
    checksums: dict[str, str]
    def __init__(self, graph: ProgramGraph, state_space: StateSpaceModel, process_model: ProcessModel, mappings: dict[str, Any], config: dict[str, Any] | None = None) -> None: ...
    def build(self, output_dir: str) -> dict[str, Any]: ...
