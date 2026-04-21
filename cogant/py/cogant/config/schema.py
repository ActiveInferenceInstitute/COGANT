"""
COGANT Configuration Schemas

Pydantic v2 models for system-wide configuration, pipeline configuration,
export settings, and validation configuration.
"""

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CogantBaseConfig(BaseModel):
    """Base configuration class for all COGANT configs."""

    model_config = ConfigDict(
        use_enum_values=False,
        validate_assignment=True,
        arbitrary_types_allowed=True,
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

    # Advanced options
    strict_schema_validation: bool = Field(
        default=True,
        description="Enforce strict schema validation",
    )
    fail_on_warnings: bool = Field(default=False, description="Treat warnings as errors")
    preserve_source_formatting: bool = Field(
        default=True,
        description="Preserve original source formatting in exports",
    )

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


class PipelineConfig(CogantBaseConfig):
    """
    Configuration for the analysis pipeline.

    Specifies which analysis stages run, in what order, and with what settings.
    """

    # Pipeline identity
    name: str = Field(default="default", description="Pipeline name")
    description: str | None = Field(default=None, description="Pipeline description")

    # Execution
    run_stages: list[str] = Field(
        default_factory=lambda: [
            "ingest",
            "static",
            "normalize",
            "graph",
            "dynamic",
            "translate",
            "statespace",
            "process",
            "validate",
            "export",
        ],
        description="Stages to run in order",
    )
    parallel_stages: list[list[str]] = Field(
        default_factory=list,
        description="Groups of stages to run in parallel",
    )

    # Stage configs
    stages: dict[str, PipelineStage] = Field(
        default_factory=dict,
        description="Configuration for each stage",
    )

    # Language support
    languages: list[LanguageConfig] = Field(
        default_factory=list,
        description="Language-specific analyzer configs",
    )

    # Filtering
    include_patterns: list[str] = Field(
        default_factory=list,
        description="File patterns to include (e.g., '*.py')",
    )
    exclude_patterns: list[str] = Field(
        default_factory=list,
        description="File patterns to exclude (e.g., 'test_*.py')",
    )

    # Analysis scope
    analyze_tests: bool = Field(default=True, description="Include test files in analysis")
    analyze_dependencies: bool = Field(
        default=True,
        description="Analyze external dependencies",
    )
    follow_imports: bool = Field(default=True, description="Follow import/include statements")
    max_import_depth: int = Field(default=5, ge=0, description="Maximum import depth to follow")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "default",
                "run_stages": [
                    "ingest",
                    "static",
                    "graph",
                    "translate",
                    "validate",
                    "export",
                ],
                "exclude_patterns": ["**/test_*.py", "**/__pycache__/**"],
                "analyze_tests": True,
            }
        }
    )


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
    """
    Configuration for validation checks.

    Controls which validation checks run and how strict they are.
    """

    # Validation level
    level: ValidationLevel = Field(
        default=ValidationLevel.MODERATE,
        description="Validation strictness",
    )

    # Schema validation
    validate_schema: bool = Field(default=True, description="Validate against schemas")
    validate_references: bool = Field(
        default=True,
        description="Check referential integrity",
    )
    validate_graph_structure: bool = Field(default=True, description="Validate graph structure")

    # Coverage validation
    min_provenance_coverage: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Minimum provenance coverage ratio",
    )
    min_mean_confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum mean confidence score",
    )

    # Completeness checks
    check_missing_mappings: bool = Field(
        default=True,
        description="Warn about unmapped code elements",
    )
    check_unobservable_state: bool = Field(
        default=True,
        description="Warn about unobservable state vars",
    )
    check_unreachable_code: bool = Field(
        default=False,
        description="Detect unreachable code sections",
    )

    # Performance checks
    warn_on_large_graph: bool = Field(
        default=True,
        description="Warn if graph exceeds size threshold",
    )
    large_graph_threshold: int = Field(default=50000, ge=1, description="Graph size threshold")

    # Output
    generate_report: bool = Field(default=True, description="Generate validation report")
    fail_on_error: bool = Field(
        default=False,
        description="Fail bundle if validation errors found",
    )
    use_upstream_gnn_validator: bool = Field(
        default=True,
        description=(
            "Run Active Inference Institute src.gnn checks in addition to COGANT "
            "validators (mirrors pipeline ``upstream_gnn_validation`` when wired)"
        ),
    )
    auto_fix_warnings: bool = Field(
        default=False,
        description="Automatically fix fixable issues",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "level": "moderate",
                "validate_schema": True,
                "validate_references": True,
                "min_mean_confidence": 0.7,
                "fail_on_error": False,
            }
        }
    )
