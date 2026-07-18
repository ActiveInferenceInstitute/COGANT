from enum import StrEnum
from typing import Any, ClassVar, Literal

from _typeshed import Incomplete
from pydantic import BaseModel

from .pipeline import PipelineConfig as PipelineConfig

CURRENT_CONFIG_SCHEMA_VERSION: str

class CogantBaseConfig(BaseModel):
    model_config: ClassVar[Incomplete]

class LogLevel(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class CogantConfig(CogantBaseConfig):
    version: str
    environment: Literal["development", "staging", "production"]
    log_level: LogLevel
    log_format: str
    log_file: str | None
    max_workers: int
    max_memory_mb: int
    max_graph_nodes: int
    timeout_seconds: float
    enable_caching: bool
    cache_dir: str | None
    cache_ttl_hours: int
    enable_provenance_tracking: bool
    enable_validation: bool
    enable_gnn_export: bool
    enable_incremental_analysis: bool
    strict_schema_validation: bool
    fail_on_warnings: bool
    preserve_source_formatting: bool
    model_config: ClassVar[Incomplete]

class LanguageConfig(CogantBaseConfig):
    language: str
    enabled: bool
    analyzer_name: str
    analyzer_version: str
    analyzer_config: dict[str, Any]

class PipelineStage(CogantBaseConfig):
    name: str
    enabled: bool
    timeout_seconds: float
    retry_count: int
    skip_on_error: bool
    parameters: dict[str, Any]

class ExportFormat(StrEnum):
    JSON = "json"
    JSON_LINES = "jsonl"
    PARQUET = "parquet"
    PROTOBUF = "protobuf"

class ExportConfig(CogantBaseConfig):
    primary_format: ExportFormat
    additional_formats: list[ExportFormat]
    output_dir: str
    create_bundle: bool
    bundle_name: str
    compression: Literal["none", "gzip", "zstd"]
    compression_level: int
    include_provenance: bool
    include_metadata: bool
    include_statistics: bool
    minify_json: bool
    gnn_format: str | None
    gnn_include_features: bool
    gnn_split_train_test: bool
    gnn_train_test_split: float
    model_config: ClassVar[Incomplete]

class ValidationLevel(StrEnum):
    LENIENT = "lenient"
    MODERATE = "moderate"
    STRICT = "strict"
    PARANOID = "paranoid"

class ValidationConfig(CogantBaseConfig):
    level: ValidationLevel
    validate_schema: bool
    validate_references: bool
    validate_graph_structure: bool
    min_provenance_coverage: float
    min_mean_confidence: float
    check_missing_mappings: bool
    check_unobservable_state: bool
    check_unreachable_code: bool
    warn_on_large_graph: bool
    large_graph_threshold: int
    generate_report: bool
    fail_on_error: bool
    auto_fix_warnings: bool
    model_config: ClassVar[Incomplete]

class ServerConfig(CogantBaseConfig):
    host: str
    port: int
    workspace_root: str
    allow_absolute_paths: bool
    auth_token: str | None
    max_request_bytes: int
    max_gnn_text_bytes: int
    max_archive_bytes: int
    max_archive_files: int
    max_concurrent_requests: int
    request_timeout_seconds: float
    rate_limit_requests: int
    rate_limit_window_seconds: int
    rate_limit_paths: list[str]

class BatchConfig(CogantBaseConfig):
    package_root: str
    output_root: str
    remote: BatchRemoteConfig
    targets: list[BatchTargetConfig]
    steps: BatchStepsConfig
    manuscript: BatchManuscriptConfig
    target_ids: list[str]
    enabled_steps: list[str]
    dashboard: bool
    max_targets: int
    max_archive_files: int
    max_archive_bytes: int

class BatchTargetConfig(CogantBaseConfig):
    id: str
    path: str | None
    git_url: str | None
    git_ref: str | None
    explain: str | None
    roundtrip_threshold: float | None
    roundtrip_note: str | None

class BatchRemoteConfig(CogantBaseConfig):
    shallow_clone: bool
    refresh: bool

class BatchManuscriptConfig(CogantBaseConfig):
    enabled: bool
    regenerate_metrics: bool
    strict: bool

class BatchStepsConfig(CogantBaseConfig):
    doctor: bool
    translate: bool
    layout_output: bool
    no_dynamic: bool
    scan_json: bool
    graph_stdout: bool
    export_gnn: bool
    export_gnn_format: str
    render_site: bool
    viz_png: bool
    validate_run_dir: bool
    validate_no_upstream_gnn: bool
    roundtrip: bool
    analyze_graph: bool
    analyze_static: bool
    export_multi: bool
    export_multi_formats: str
    visualize_diagrams: bool
    visualize_format: str
    inspection_artifacts: bool
    batch_dashboard: bool

class ProjectConfig(CogantBaseConfig):
    schema_version: str
    cogant: CogantConfig
    pipeline: PipelineConfig
    export: ExportConfig
    validation: ValidationConfig
    server: ServerConfig
    batch: BatchConfig
    def __contains__(self, key: object) -> bool: ...
    def __getitem__(self, key: str) -> Any: ...
