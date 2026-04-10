from typing import Any

from _typeshed import Incomplete

from cogant.gnn.formatter.dynamics import _DynamicsSectionsMixin
from cogant.gnn.formatter.metadata import _MetadataSectionsMixin
from cogant.gnn.formatter.semantic import _SemanticSectionsMixin
from cogant.gnn.formatter.structural import _StructuralSectionsMixin
from cogant.gnn.formatter.upstream import _UpstreamSectionsMixin
from cogant.process.extractor import ProcessModel as ProcessModel
from cogant.schemas.core import EdgeKind as EdgeKind
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.statespace.compiler import StateSpaceModel as StateSpaceModel

logger: Incomplete

class GNNMarkdownFormatter(_UpstreamSectionsMixin, _MetadataSectionsMixin, _StructuralSectionsMixin, _DynamicsSectionsMixin, _SemanticSectionsMixin):
    SECTION_ORDER: Incomplete
    graph: Incomplete
    state_space: Incomplete
    process: Incomplete
    mappings: Incomplete
    def __init__(self, program_graph: ProgramGraph, state_space_model: StateSpaceModel, process_model: ProcessModel, semantic_mappings: dict[str, Any]) -> None: ...
    def format(self) -> str: ...
    def format_section(self, section_name: str) -> str | None: ...
