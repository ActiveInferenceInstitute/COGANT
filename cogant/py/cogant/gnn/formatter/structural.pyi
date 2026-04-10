from _typeshed import Incomplete
from cogant.gnn.matrices import GNNMatrices as GNNMatrices
from cogant.process.extractor import ProcessModel as ProcessModel
from cogant.schemas.core import NodeKind as NodeKind
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.schemas.semantic import MappingKind as MappingKind
from cogant.statespace.compiler import StateSpaceModel as StateSpaceModel
from typing import Any

logger: Incomplete

class _StructuralSectionsMixin:
    graph: ProgramGraph
    state_space: StateSpaceModel
    process: ProcessModel
    mappings: dict[str, Any]
