"""Canonical typed defaults for every COGANT entry point."""

from __future__ import annotations

from .pipeline import PipelineConfig
from .schema import (
    CogantConfig,
    ExportConfig,
    ExportFormat,
    LanguageConfig,
    LogLevel,
    ProjectConfig,
    ValidationConfig,
    ValidationLevel,
)

DEFAULT_COGANT_CONFIG = CogantConfig(
    version="1.0.0",
    environment="production",
    log_level=LogLevel.INFO,
    max_workers=4,
    max_memory_mb=4096,
    max_graph_nodes=100_000,
    timeout_seconds=300.0,
    enable_caching=True,
    cache_ttl_hours=24,
    enable_provenance_tracking=True,
    enable_validation=True,
    enable_gnn_export=True,
    strict_schema_validation=True,
    fail_on_warnings=False,
)

DEFAULT_PYTHON_CONFIG = LanguageConfig(
    language="python",
    analyzer_name="python-ast",
    analyzer_config={"follow_imports": True, "analyze_type_hints": True},
)
DEFAULT_JAVASCRIPT_CONFIG = LanguageConfig(
    language="javascript",
    analyzer_name="javascript-structural",
    analyzer_config={"parse_typescript": True},
)
DEFAULT_JAVA_CONFIG = LanguageConfig(
    language="java",
    analyzer_name="java-structural",
    analyzer_config={"follow_imports": True},
)
DEFAULT_LANGUAGE_CONFIGS = {
    "python": DEFAULT_PYTHON_CONFIG,
    "javascript": DEFAULT_JAVASCRIPT_CONFIG,
    "java": DEFAULT_JAVA_CONFIG,
}

DEFAULT_STAGES = [
    "ingest",
    "static",
    "normalize",
    "graph",
    "dynamic",
    "translate",
    "statespace",
    "process",
    "export",
    "validate",
]

DEFAULT_PIPELINE_CONFIG = PipelineConfig(
    stages=DEFAULT_STAGES,
    ingest={"follow_symlinks": False},
    graph={"max_nodes": 100_000, "max_edges": 500_000},
    render_visualizations=True,
)
MINIMAL_PIPELINE_CONFIG = PipelineConfig(
    stages=["ingest", "static", "normalize", "graph", "export", "validate"],
    skip_dynamic=True,
    render_visualizations=False,
    output_dir="output",
)
COMPREHENSIVE_PIPELINE_CONFIG = DEFAULT_PIPELINE_CONFIG

DEFAULT_EXPORT_CONFIG = ExportConfig(
    primary_format=ExportFormat.JSON,
    output_dir="output",
    create_bundle=True,
    compression="gzip",
    include_provenance=True,
    include_metadata=True,
    include_statistics=True,
)
MINIMAL_EXPORT_CONFIG = ExportConfig(
    primary_format=ExportFormat.JSON,
    output_dir="output",
    create_bundle=False,
    compression="none",
    include_provenance=True,
    include_metadata=True,
    include_statistics=False,
)
GNN_EXPORT_CONFIG = DEFAULT_EXPORT_CONFIG

DEFAULT_VALIDATION_CONFIG = ValidationConfig(
    level=ValidationLevel.STRICT,
    validate_schema=True,
    validate_references=True,
    validate_graph_structure=True,
    min_provenance_coverage=0.8,
    min_mean_confidence=0.7,
    check_missing_mappings=True,
    check_unobservable_state=True,
    generate_report=True,
    fail_on_error=True,
    use_upstream_gnn_validator=False,
)
STRICT_VALIDATION_CONFIG = DEFAULT_VALIDATION_CONFIG
LENIENT_VALIDATION_CONFIG = ValidationConfig(
    level=ValidationLevel.MODERATE,
    validate_schema=True,
    validate_references=True,
    min_provenance_coverage=0.5,
    min_mean_confidence=0.5,
    check_missing_mappings=False,
    check_unobservable_state=False,
    generate_report=True,
    fail_on_error=True,
    use_upstream_gnn_validator=False,
)

DEFAULT_PROJECT_CONFIG = ProjectConfig(
    cogant=DEFAULT_COGANT_CONFIG,
    pipeline=DEFAULT_PIPELINE_CONFIG,
    export=DEFAULT_EXPORT_CONFIG,
    validation=DEFAULT_VALIDATION_CONFIG,
)

# A single registry is exposed from this module for callers that historically
# imported defaults.  The values are typed ProjectConfig instances.
from .presets import PRESETS  # noqa: E402


def get_preset(name: str) -> ProjectConfig:
    """Return a validated project configuration for a named preset."""
    if name not in PRESETS:
        available = ", ".join(PRESETS)
        raise ValueError(f"Unknown preset '{name}'. Available: {available}")
    return PRESETS[name]
