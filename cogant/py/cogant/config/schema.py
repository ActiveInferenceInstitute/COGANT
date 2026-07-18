"""
COGANT Configuration Schemas

Pydantic v2 models for system-wide configuration, pipeline configuration,
export settings, and validation configuration.
"""

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .pipeline import PipelineConfig as CanonicalPipelineConfig

CURRENT_CONFIG_SCHEMA_VERSION = "1.0"


def _validate_path_text(value: str, field_name: str) -> str:
    if not value.strip() or "\x00" in value:
        raise ValueError(f"{field_name} must be non-empty and NUL-free")
    if ".." in Path(value).parts:
        raise ValueError(f"{field_name} must not contain path traversal components")
    return value


class CogantBaseConfig(BaseModel):
    """Base configuration class for all COGANT configs."""

    model_config = ConfigDict(
        use_enum_values=False,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        extra="forbid",
        validate_default=True,
    )


class LogLevel(StrEnum):
    """Logging verbosity levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class CogantConfig(CogantBaseConfig):
    """
    Top-level COGANT system configuration.

    Controls system-wide behavior including logging, caching,
    resource limits, and feature flags.
    """

    # System identification
    version: str = Field(default="1.0.0", description="COGANT framework version")
    environment: Literal["development", "staging", "production"] = Field(
        default="production", description="Deployment environment"
    )

    # Logging
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging verbosity")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format",
    )
    log_file: str | None = Field(default=None, description="Log file path (None = stdout only)")

    # Resource limits
    max_workers: int = Field(default=4, ge=1, description="Maximum parallel workers")
    max_memory_mb: int = Field(default=4096, ge=512, description="Maximum memory usage (MB)")
    max_graph_nodes: int = Field(default=100000, ge=1, description="Maximum nodes in program graph")
    timeout_seconds: float = Field(default=300.0, gt=0, description="Operation timeout (seconds)")

    # Caching
    enable_caching: bool = Field(default=True, description="Enable result caching")
    cache_dir: str | None = Field(default=None, description="Cache directory path")
    cache_ttl_hours: int = Field(default=24, ge=1, description="Cache time-to-live (hours)")

    # Feature flags
    enable_provenance_tracking: bool = Field(default=True, description="Track provenance evidence")
    enable_validation: bool = Field(default=True, description="Run validation checks")
    enable_gnn_export: bool = Field(default=True, description="Generate GNN export")
    enable_incremental_analysis: bool = Field(
        default=False, description="Use incremental analysis mode"
    )

    # Strictness knobs (off by default unless explicitly opted in).
    strict_schema_validation: bool = Field(
        default=True,
        description="Enforce strict schema validation",
    )
    fail_on_warnings: bool = Field(default=False, description="Treat warnings as errors")
    preserve_source_formatting: bool = Field(
        default=True,
        description="Preserve original source formatting in exports",
    )

    @field_validator("log_file", "cache_dir")
    @classmethod
    def validate_paths(cls, value: str | None) -> str | None:
        return None if value is None else _validate_path_text(value, "configuration path")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "version": "1.0.0",
                "environment": "production",
                "log_level": "info",
                "max_workers": 4,
                "max_memory_mb": 4096,
                "enable_caching": True,
            }
        }
    )


class LanguageConfig(CogantBaseConfig):
    """Configuration for language-specific analyzers."""

    language: str = Field(..., description="Language identifier (e.g., 'python')")
    enabled: bool = Field(default=True, description="Whether to analyze this language")
    analyzer_name: str = Field(..., description="Name of analyzer tool")
    analyzer_version: str = Field(default="1.0.0", description="Version of analyzer")
    analyzer_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Language-specific analyzer configuration",
    )


class PipelineStage(CogantBaseConfig):
    """Configuration for a single pipeline stage."""

    name: str = Field(..., description="Stage name (e.g., 'ingest', 'analyze')")
    enabled: bool = Field(default=True, description="Whether stage is active")
    timeout_seconds: float = Field(default=300.0, gt=0, description="Stage timeout")
    retry_count: int = Field(default=0, ge=0, description="Number of retries on failure")
    skip_on_error: bool = Field(
        default=False,
        description="Continue pipeline if stage fails",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Stage-specific parameters",
    )


# The pipeline model is defined once in ``config.pipeline``.  Keep this
# import path as a direct alias so there cannot be two accepted schemas.
PipelineConfig = CanonicalPipelineConfig


class ExportFormat(StrEnum):
    """Supported export formats."""

    JSON = "json"
    JSON_LINES = "jsonl"
    PARQUET = "parquet"
    PROTOBUF = "protobuf"


class ExportConfig(CogantBaseConfig):
    """
    Configuration for exporting analysis results.

    Controls output formats, compression, and how data is serialized.
    """

    # Output format
    primary_format: ExportFormat = Field(
        default=ExportFormat.JSON,
        description="Primary export format",
    )
    additional_formats: list[ExportFormat] = Field(
        default_factory=list,
        description="Additional export formats",
    )

    # Output location
    output_dir: str = Field(
        default="./cogant_output",
        description="Output directory path",
    )
    create_bundle: bool = Field(
        default=True,
        description="Package exports into single bundle",
    )
    bundle_name: str = Field(
        default="cogant_bundle",
        description="Name for output bundle",
    )

    # Compression
    compression: Literal["none", "gzip", "zstd"] = Field(
        default="gzip",
        description="Compression algorithm",
    )
    compression_level: int = Field(default=6, ge=1, le=9, description="Compression level (1-9)")

    # Content control
    include_provenance: bool = Field(
        default=True,
        description="Include provenance data in export",
    )
    include_metadata: bool = Field(default=True, description="Include metadata")
    include_statistics: bool = Field(default=True, description="Include statistics")
    minify_json: bool = Field(
        default=False,
        description="Remove whitespace from JSON",
    )

    # GNN-specific options
    gnn_format: str | None = Field(
        default=None,
        description="Target GNN framework (pytorch_geometric, dgl, etc.)",
    )
    gnn_include_features: bool = Field(default=True, description="Include node/edge features")
    gnn_split_train_test: bool = Field(
        default=False,
        description="Split graph for train/test",
    )
    gnn_train_test_split: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Train/test split ratio",
    )

    @field_validator("output_dir", "bundle_name")
    @classmethod
    def validate_paths(cls, value: str) -> str:
        return _validate_path_text(value, "export path")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "primary_format": "json",
                "output_dir": "./output",
                "create_bundle": True,
                "compression": "gzip",
                "include_provenance": True,
            }
        }
    )


class ValidationLevel(StrEnum):
    """Validation strictness levels."""

    LENIENT = "lenient"  # Only critical checks
    MODERATE = "moderate"  # Standard checks
    STRICT = "strict"  # All checks enabled
    PARANOID = "paranoid"  # Extra checks + all warnings



class ValidationConfig(CogantBaseConfig):
    """Configuration for validation checks."""

    level: ValidationLevel = Field(default=ValidationLevel.MODERATE)
    validate_schema: bool = Field(default=True)
    validate_references: bool = Field(default=True)
    validate_graph_structure: bool = Field(default=True)
    min_provenance_coverage: float = Field(default=0.8, ge=0.0, le=1.0)
    min_mean_confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    check_missing_mappings: bool = Field(default=True)
    check_unobservable_state: bool = Field(default=True)
    check_unreachable_code: bool = Field(default=False)
    warn_on_large_graph: bool = Field(default=True)
    large_graph_threshold: int = Field(default=50_000, ge=1)
    generate_report: bool = Field(default=True)
    fail_on_error: bool = Field(default=False)
    use_upstream_gnn_validator: bool = Field(default=False)
    auto_fix_warnings: bool = Field(default=False)


class ServerConfig(CogantBaseConfig):
    """Local-safe settings for the HTTP analysis service."""

    host: str = Field(default="127.0.0.1", min_length=1)
    port: int = Field(default=8000, ge=1, le=65_535)
    workspace_root: str = Field(default=".", min_length=1)
    allow_absolute_paths: bool = False
    auth_token: str | None = Field(default=None, min_length=1)
    max_request_bytes: int = Field(default=2_000_000, ge=1_024)
    max_gnn_text_bytes: int = Field(default=1_000_000, ge=1_024)
    max_archive_bytes: int = Field(default=25_000_000, ge=1_024)
    max_archive_files: int = Field(default=1_000, ge=1)
    max_concurrent_requests: int = Field(default=4, ge=1)
    request_timeout_seconds: float = Field(default=300.0, gt=0)
    rate_limit_requests: int = Field(default=10, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)
    rate_limit_paths: list[str] = Field(
        default_factory=lambda: ["/analyze", "/roundtrip", "/reverse"]
    )

    @field_validator("workspace_root")
    @classmethod
    def validate_workspace_root(cls, value: str) -> str:
        return _validate_path_text(value, "server workspace_root")

    @field_validator("auth_token")
    @classmethod
    def validate_auth_token(cls, value: str | None) -> str | None:
        if value is not None and (not value.strip() or "\x00" in value):
            raise ValueError("server auth_token must be non-empty and NUL-free")
        return value

    @model_validator(mode="after")
    def require_auth_for_non_loopback(self) -> "ServerConfig":
        loopback_hosts = {"127.0.0.1", "::1", "localhost"}
        if self.host not in loopback_hosts and not self.auth_token:
            raise ValueError("auth_token is required when server host is not loopback")
        return self


class BatchTargetConfig(CogantBaseConfig):
    """One source repository in a batch execution."""

    id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    path: str | None = None
    git_url: str | None = None
    git_ref: str | None = None
    explain: str | None = None
    roundtrip_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    roundtrip_note: str | None = None

    @field_validator("path", "git_url", "git_ref", "explain", "roundtrip_note")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_path_text(value, "batch target value")

    @model_validator(mode="after")
    def require_one_source(self) -> "BatchTargetConfig":
        if bool(self.path) == bool(self.git_url):
            raise ValueError("each batch target must define exactly one of path or git_url")
        return self


class BatchRemoteConfig(CogantBaseConfig):
    """Remote source acquisition policy for batch execution."""

    shallow_clone: bool = True
    refresh: bool = False


class BatchManuscriptConfig(CogantBaseConfig):
    """Optional manuscript regeneration stage settings."""

    enabled: bool = False
    regenerate_metrics: bool = False
    strict: bool = False


class BatchStepsConfig(CogantBaseConfig):
    """Explicitly typed batch stages and their format selectors."""

    doctor: bool = False
    translate: bool = True
    layout_output: bool = True
    no_dynamic: bool = True
    scan_json: bool = True
    graph_stdout: bool = True
    export_gnn: bool = True
    export_gnn_format: str = Field(default="all", min_length=1)
    render_site: bool = True
    viz_png: bool = True
    validate_run_dir: bool = True
    validate_no_upstream_gnn: bool = False
    roundtrip: bool = True
    analyze_graph: bool = True
    analyze_static: bool = True
    export_multi: bool = True
    export_multi_formats: str = Field(default="json,jsonlines", min_length=1)
    visualize_diagrams: bool = True
    visualize_format: str = Field(default="mermaid", min_length=1)
    inspection_artifacts: bool = True
    batch_dashboard: bool = True


class BatchConfig(CogantBaseConfig):
    """Typed settings for multi-target execution and reporting."""

    package_root: str = Field(default="cogant", min_length=1)
    output_root: str = Field(default="output", min_length=1)
    remote: BatchRemoteConfig = Field(default_factory=BatchRemoteConfig)
    targets: list[BatchTargetConfig] = Field(default_factory=list)
    steps: BatchStepsConfig = Field(default_factory=BatchStepsConfig)
    manuscript: BatchManuscriptConfig = Field(default_factory=BatchManuscriptConfig)
    target_ids: list[str] = Field(default_factory=list)
    enabled_steps: list[str] = Field(
        default_factory=lambda: ["translate", "export", "render", "visualize", "validate"]
    )
    dashboard: bool = True
    max_targets: int = Field(default=100, ge=1)
    max_archive_files: int = Field(default=1_000, ge=1)
    max_archive_bytes: int = Field(default=25_000_000, ge=1_024)

    @field_validator("package_root", "output_root")
    @classmethod
    def validate_output_root(cls, value: str) -> str:
        return _validate_path_text(value, "batch path")


class ProjectConfig(CogantBaseConfig):
    """Fully typed configuration consumed by all COGANT entry points."""

    schema_version: str = Field(
        default=CURRENT_CONFIG_SCHEMA_VERSION,
        pattern=r"^1\.\d+$",
        description="Version of the canonical project configuration schema",
    )
    cogant: CogantConfig = Field(default_factory=CogantConfig)
    pipeline: CanonicalPipelineConfig = Field(default_factory=CanonicalPipelineConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    batch: BatchConfig = Field(default_factory=BatchConfig)

    def __getitem__(self, key: str) -> Any:
        """Expose named sections for read-only boundary adapters."""
        if key not in type(self).model_fields:
            raise KeyError(key)
        return getattr(self, key)

    def __contains__(self, key: object) -> bool:
        """Support legacy section-membership checks without exposing a dict.

        Presets now contain canonical :class:`ProjectConfig` models rather
        than duplicated raw dictionaries.  A small mapping-compatible
        membership surface keeps older integrations such as ``"cogant" in
        PRESETS["default"]`` working during the deprecation cycle.
        """
        return isinstance(key, str) and key in type(self).model_fields

    def keys(self) -> tuple[str, ...]:
        """Return section names for structured adapters, not raw config data."""
        return tuple(type(self).model_fields)
