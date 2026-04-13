from typing import Any

from cogant.process.extractor import ProcessModel as ProcessModel
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.statespace.compiler import StateSpaceModel as StateSpaceModel

UPSTREAM_REQUIRED_SECTIONS: list[str]
UPSTREAM_OPTIONAL_SECTIONS: list[str]

class _UpstreamSectionsMixin:
    graph: ProgramGraph
    state_space: StateSpaceModel
    process: ProcessModel
    mappings: dict[str, Any]
