from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from cogant.markov.blanket import MarkovBlanket as MarkovBlanket
from cogant.schemas.graph import ProgramGraph as ProgramGraph

logger: Any

class ExportFormat(Enum):
    JSON = "json"
    GRAPHML = "graphml"
    PARQUET = "parquet"
    SVG = "svg"
    PNG = "png"
    PDF = "pdf"
    MERMAID = "mermaid"
    DOT = "dot"
    JSONLINES = "jsonlines"

@dataclass
class ExportConfig:
    formats: list[ExportFormat]
    output_dir: str
    prefix: str
    overwrite: bool

class MultiFormatExporter:
    typed_exporter: Any
    graphml_exporter_class: Any
    parquet_exporter_class: Any
    svg_exporter: Any
    schema_exporter: Any
    def __init__(self) -> None: ...
    def export_all(
        self, pipeline_result: dict[str, Any], config: ExportConfig
    ) -> dict[ExportFormat, str]: ...
    def export_graph(
        self, graph: ProgramGraph, config: ExportConfig
    ) -> dict[ExportFormat, str]: ...
    def export_gnn_bundle(
        self, bundle: dict[str, Any], config: ExportConfig
    ) -> dict[ExportFormat, str]: ...
    def _export_format(
        self,
        pipeline_result: dict[str, Any],
        fmt: ExportFormat,
        output_dir: Path,
        prefix: str,
    ) -> str | None: ...
    def _export_graph_format(
        self,
        graph: ProgramGraph,
        fmt: ExportFormat,
        output_dir: Path,
        prefix: str,
    ) -> str | None: ...
    def _export_bundle_format(
        self,
        bundle: dict[str, Any],
        fmt: ExportFormat,
        output_dir: Path,
        prefix: str,
    ) -> str | None: ...
    def _export_pipeline_json(
        self, pipeline_result: dict[str, Any], output_dir: Path, prefix: str
    ) -> str: ...
    def _export_pipeline_jsonlines(
        self, pipeline_result: dict[str, Any], output_dir: Path, prefix: str
    ) -> str: ...
