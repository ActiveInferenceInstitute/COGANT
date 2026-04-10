from typing import Any

from _typeshed import Incomplete as Incomplete

from cogant.process.extractor import ProcessModel as ProcessModel
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.statespace.compiler import StateSpaceModel as StateSpaceModel

logger: Incomplete

class _DynamicsSectionsMixin:
    graph: ProgramGraph
    state_space: StateSpaceModel
    process: ProcessModel
    mappings: dict[str, Any]
