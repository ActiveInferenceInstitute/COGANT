from .gnn import GNNConfig as GNNConfig
from .graph import GraphConfig as GraphConfig
from .ingest import IngestConfig as IngestConfig
from .reverse import ReverseConfig as ReverseConfig
from .statespace import StatespaceConfig as StatespaceConfig
from .translate import TranslateConfig as TranslateConfig
from _typeshed import Incomplete
from pathlib import Path
from pydantic import BaseModel
from typing import Any, ClassVar

class PipelineConfig(BaseModel):
    stages: list[str]
    skip_stages: list[str]
    skip_dynamic: bool
    output_dir: str
    layout_output: bool
    verbose: bool
    dry_run: bool
    coverage_path: str | None
    trace_path: str | None
    plugins: dict[str, dict[str, Any]]
    ingest: IngestConfig
    graph: GraphConfig
    translate: TranslateConfig
    statespace: StatespaceConfig
    gnn: GNNConfig
    reverse: ReverseConfig
    model_config: ClassVar[Incomplete]
    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PipelineConfig: ...
    @classmethod
    def from_yaml(cls, path: str | Path) -> PipelineConfig: ...
    @classmethod
    def from_json(cls, path: str | Path) -> PipelineConfig: ...
    def to_dict(self) -> dict[str, Any]: ...
    def to_yaml(self, path: str | Path) -> None: ...
    def to_json(self, path: str | Path) -> None: ...
    def override(self, **kwargs: Any) -> PipelineConfig: ...
