from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from _typeshed import Incomplete

from cogant.export.graphml import GraphMLExporter as GraphMLExporter
from cogant.export.parquet import ParquetExporter as ParquetExporter
from cogant.gnn.formatter import GNNMarkdownFormatter as GNNMarkdownFormatter
from cogant.gnn.json_export import GNNJSONExporter as GNNJSONExporter
from cogant.process.extractor import ProcessModel as ProcessModel
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.statespace.compiler import StateSpaceModel as StateSpaceModel

logger: Incomplete

@dataclass
class BundleManifest:
    bundle_id: str
    schema_name: str
    created_at: datetime
    files: dict[str, str]
    checksums: dict[str, str]
    metadata: dict[str, Any]

class BundleExporter:
    FORMATS: Incomplete
    graph: Incomplete
    state_space: Incomplete
    process: Incomplete
    mappings: Incomplete
    output_dir: Incomplete
    def __init__(self, program_graph: ProgramGraph, state_space_model: StateSpaceModel, process_model: ProcessModel, semantic_mappings: dict[str, Any], output_dir: Path) -> None: ...
    def export(self, formats: list[str] | None = None) -> Path: ...
