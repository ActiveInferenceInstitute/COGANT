from _typeshed import Incomplete
from cogant.process.extractor import ProcessModel as ProcessModel
from cogant.schemas.core import EdgeKind as EdgeKind, NodeKind as NodeKind
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.schemas.semantic import MappingKind as MappingKind
from cogant.statespace.compiler import StateSpaceModel as StateSpaceModel
from typing import Any

logger: Incomplete

class _MetadataSectionsMixin:
    graph: ProgramGraph
    state_space: StateSpaceModel
    process: ProcessModel
    mappings: dict[str, Any]
