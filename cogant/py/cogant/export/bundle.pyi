from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from cogant.process.extractor import ProcessModel as ProcessModel
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.statespace.compiler import StateSpaceModel as StateSpaceModel

@dataclass
class BundleManifest:
    bundle_id: str
    schema_name: str
    created_at: datetime
    files: dict[str, str]
    checksums: dict[str, str]
    metadata: dict[str, Any]

class BundleExporter:
    FORMATS: list[str]
    graph: ProgramGraph
    state_space: StateSpaceModel
    process: ProcessModel
    mappings: dict[str, Any]
    output_dir: Path
    def __init__(
        self,
        program_graph: ProgramGraph,
        state_space_model: StateSpaceModel,
        process_model: ProcessModel,
        semantic_mappings: dict[str, Any],
        output_dir: Path,
    ) -> None: ...
    def export(self, formats: list[str] | None = None) -> Path: ...
    def export_zip(self, output_path: str) -> str: ...
    def export_with_provenance(
        self, bundle: dict[str, Any], pipeline_config: dict[str, Any], output_path: str
    ) -> str: ...
