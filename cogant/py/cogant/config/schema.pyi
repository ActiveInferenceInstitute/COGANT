from _typeshed import Incomplete
from enum import StrEnum
from pydantic import BaseModel
from typing import Any, Literal, ClassVar

class CogantBaseConfig(BaseModel):
    model_config: ClassVar[Incomplete]

class LogLevel(StrEnum):
    DEBUG = 'debug'
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'

class CogantConfig(CogantBaseConfig):
    version: str
    environment: Literal['development', 'staging', 'production']
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

class PipelineConfig(CogantBaseConfig):
    name: str
    description: str | None
    run_stages: list[str]
    parallel_stages: list[list[str]]
    stages: dict[str, PipelineStage]
    languages: list[LanguageConfig]
    include_patterns: list[str]
    exclude_patterns: list[str]
    analyze_tests: bool
    analyze_dependencies: bool
    follow_imports: bool
    max_import_depth: int
    model_config: ClassVar[Incomplete]

class ExportFormat(StrEnum):
    JSON = 'json'
    JSON_LINES = 'jsonl'
    PARQUET = 'parquet'
    PROTOBUF = 'protobuf'

class ExportConfig(CogantBaseConfig):
    primary_format: ExportFormat
    additional_formats: list[ExportFormat]
    output_dir: str
    create_bundle: bool
    bundle_name: str
    compression: Literal['none', 'gzip', 'zstd']
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
    LENIENT = 'lenient'
    MODERATE = 'moderate'
    STRICT = 'strict'
    PARANOID = 'paranoid'

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
