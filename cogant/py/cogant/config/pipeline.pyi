from pathlib import Path
from typing import Any, ClassVar

from _typeshed import Incomplete
from pydantic import BaseModel

from .gnn import GNNConfig as GNNConfig
from .graph import GraphConfig as GraphConfig
from .ingest import IngestConfig as IngestConfig
from .reverse import ReverseConfig as ReverseConfig
from .statespace import StatespaceConfig as StatespaceConfig
from .translate import TranslateConfig as TranslateConfig

class PipelineConfig(BaseModel):
    stages: list[str]
    skip_stages: list[str]
    skip_dynamic: bool
    output_dir: str
    layout_output: bool
    verbose: bool
    dry_run: bool
    render_visualizations: bool
    incremental_since: str | None
    cache_dir: str | None
    min_confidence: float
    profiling_enabled: bool
    upstream_gnn_validation: bool
    upstream_gnn_pipeline: bool
    upstream_gnn_only_steps: list[int] | None
    upstream_gnn_skip_steps: list[int]
    upstream_gnn_output_dir: str | None
    upstream_gnn_frameworks: str
    upstream_gnn_llm_model: str | None
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
    def __init__(self, **data: Any) -> None: ...
    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PipelineConfig: ...
    @classmethod
    def from_yaml(cls, path: str | Path) -> PipelineConfig: ...
    @classmethod
    def from_json(cls, path: str | Path) -> PipelineConfig: ...
    def to_dict(self) -> dict[str, Any]: ...
    def to_yaml(self, path: str | Path) -> None: ...
    def to_json(self, path: str | Path) -> None: ...
    def validate(self) -> list[str]: ...  # type: ignore[override]
    def with_profiling(self) -> PipelineConfig: ...
    def override(self, **kwargs: Any) -> PipelineConfig: ...
