from _typeshed import Incomplete
from cogant.gnn.formatter import GNNMarkdownFormatter as GNNMarkdownFormatter
from cogant.gnn.json_export import GNNJSONExporter as GNNJSONExporter
from cogant.markov import MarkovBlanketExtractor as MarkovBlanketExtractor, build_blanket_network as build_blanket_network, serialize_blanket as serialize_blanket
from cogant.process.extractor import ProcessModel as ProcessModel
from cogant.schemas.core import NodeKind as NodeKind
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.schemas.semantic import MappingKind as MappingKind
from cogant.statespace.compiler import StateSpaceModel as StateSpaceModel
from typing import Any

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
