from typing import Any

from _typeshed import Incomplete

from cogant.process.extractor import ProcessModel as ProcessModel
from cogant.schemas.core import EdgeKind as EdgeKind
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.schemas.semantic import MappingKind as MappingKind
from cogant.statespace.compiler import StateSpaceModel as StateSpaceModel

logger: Incomplete

class _DynamicsSectionsMixin:
    graph: ProgramGraph
    state_space: StateSpaceModel
    process: ProcessModel
    mappings: dict[str, Any]
