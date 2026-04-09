"""
Default configuration values for COGANT system.

Provides sensible defaults that can be overridden by configuration files
and command-line arguments.
"""

from typing import Dict, Any

from .schema import (
    CogantConfig,
    PipelineConfig,
    ExportConfig,
    ValidationConfig,
    LogLevel,
    ExportFormat,
    ValidationLevel,
    LanguageConfig,
    PipelineStage,
)


# Default system configuration
DEFAULT_COGANT_CONFIG = CogantConfig(
    version="1.0.0",
    environment="production",
    log_level=LogLevel.INFO,
    log_format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    log_file=None,
    max_workers=4,
    max_memory_mb=4096,
    max_graph_nodes=100000,
    timeout_seconds=300.0,
    enable_caching=True,
    cache_dir=None,
    cache_ttl_hours=24,
    enable_provenance_tracking=True,
    enable_validation=True,
    enable_gnn_export=True,
    enable_incremental_analysis=False,
    strict_schema_validation=True,
    fail_on_warnings=False,
    preserve_source_formatting=True,
)


# Language-specific configurations
DEFAULT_PYTHON_CONFIG = LanguageConfig(
    language="python",
    enabled=True,
    analyzer_name="ast-analyzer",
    analyzer_version="1.0.0",
    analyzer_config={
        "follow_imports": True,
        "analyze_type_hints": True,
        "extract_docstrings": True,
        "resolve_deferred": True,
    },
)

DEFAULT_JAVASCRIPT_CONFIG = LanguageConfig(
    language="javascript",
    enabled=True,
    analyzer_name="ast-analyzer",
    analyzer_version="1.0.0",
    analyzer_config={
        "parse_typescript": True,
        "follow_imports": True,
        "analyze_jsdoc": True,
    },
)

DEFAULT_JAVA_CONFIG = LanguageConfig(
    language="java",
    enabled=True,
    analyzer_name="ast-analyzer",
    analyzer_version="1.0.0",
    analyzer_config={
        "follow_imports": True,
        "analyze_annotations": True,
        "extract_javadoc": True,
    },
)

DEFAULT_LANGUAGE_CONFIGS = {
    "python": DEFAULT_PYTHON_CONFIG,
    "javascript": DEFAULT_JAVASCRIPT_CONFIG,
    "java": DEFAULT_JAVA_CONFIG,
}


# Default pipeline stages
DEFAULT_STAGES = {
    "ingest": PipelineStage(
        name="ingest",
        enabled=True,
        timeout_seconds=600.0,
        retry_count=1,
        skip_on_error=False,
        parameters={
            "format": "auto",
            "encoding": "utf-8",
            "follow_symlinks": False,
        },
    ),
    "normalize": PipelineStage(
        name="normalize",
        enabled=True,
        timeout_seconds=300.0,
        retry_count=0,
        skip_on_error=False,
        parameters={
            "normalize_identifiers": True,
            "resolve_types": True,
        },
    ),
    "graph": PipelineStage(
        name="graph",
        enabled=True,
        timeout_seconds=600.0,
        retry_count=0,
        skip_on_error=False,
        parameters={
            "build_call_graph": True,
            "build_type_graph": True,
            "build_data_flow": True,
            "build_control_flow": False,  # Optional, expensive
        },
    ),
    "dynamic": PipelineStage(
        name="dynamic",
        enabled=True,
        timeout_seconds=300.0,
        retry_count=0,
        skip_on_error=True,  # Optional - coverage/traces may not exist
        parameters={
            "coverage_path": None,
            "trace_path": None,
            "normalize_paths": True,
            "hot_path_percentile": 10,
            "coverage_format": "auto",  # "cobertura", "coverage_py", "auto"
            "fallback_on_missing": True,
        },
    ),
    "static": PipelineStage(
        name="static",
        enabled=True,
        timeout_seconds=300.0,
        retry_count=0,
        skip_on_error=False,
        parameters={
            "extract_ast": True,
            "extract_types": True,
            "extract_imports": True,
        },
    ),
    "translate": PipelineStage(
        name="translate",
        enabled=True,
        timeout_seconds=300.0,
        retry_count=0,
        skip_on_error=True,  # Optional stage
        parameters={
            "auto_map_via_heuristics": True,
            "confidence_threshold": 0.5,
            "max_iterations": 10,
            "enable_conflict_resolution": True,
            # Confidence tier thresholds (must match
            # cogant.translate.confidence.ConfidenceModel)
            "static_plus_runtime_threshold": 0.65,
            "static_only_threshold": 0.5,
            "runtime_only_threshold": 0.4,
            "human_reviewed_threshold": 0.9,
        },
    ),
    "statespace": PipelineStage(
        name="statespace",
        enabled=True,
        timeout_seconds=300.0,
        retry_count=0,
        skip_on_error=True,  # Optional stage
        parameters={
            "infer_observations": True,
            "infer_actions": True,
            "infer_transitions": True,
        },
    ),
    "process": PipelineStage(
        name="process",
        enabled=True,
        timeout_seconds=300.0,
        retry_count=0,
        skip_on_error=True,  # Optional stage
        parameters={
            "extract_pipelines": True,
            "extract_event_flows": True,
        },
    ),
    "validate": PipelineStage(
        name="validate",
        enabled=True,
        timeout_seconds=300.0,
        retry_count=0,
        skip_on_error=False,
        parameters={
            "validate_schema": True,
            "validate_references": True,
            "check_coverage": True,
        },
    ),
    "export": PipelineStage(
        name="export",
        enabled=True,
        timeout_seconds=300.0,
        retry_count=0,
        skip_on_error=False,
        parameters={
            "format": "json",
            "compress": True,
            "create_bundle": True,
        },
    ),
}


# Default pipeline configuration
DEFAULT_PIPELINE_CONFIG = PipelineConfig(
    name="default",
    description="Default analysis pipeline with all stages enabled",
    run_stages=[
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
    parallel_stages=[],  # Run stages sequentially by default
    stages=DEFAULT_STAGES,
    languages=[
        DEFAULT_PYTHON_CONFIG,
        DEFAULT_JAVASCRIPT_CONFIG,
        DEFAULT_JAVA_CONFIG,
    ],
    include_patterns=["**/*.py", "**/*.js", "**/*.java"],
    exclude_patterns=[
        "**/test_*.py",
        "**/*_test.py",
        "**/tests/**",
        "**/node_modules/**",
        "**/.git/**",
        "**/__pycache__/**",
    ],
    analyze_tests=True,
    analyze_dependencies=True,
    follow_imports=True,
    max_import_depth=5,
)


# Minimal pipeline (fast, core only)
MINIMAL_PIPELINE_CONFIG = PipelineConfig(
    name="minimal",
    description="Minimal pipeline with only essential stages",
    run_stages=[
        "ingest",
        "static",
        "normalize",
        "graph",
        "validate",
        "export",
    ],
    stages={
        k: v for k, v in DEFAULT_STAGES.items()
        if k in ["ingest", "static", "normalize", "graph", "validate", "export"]
    },
    languages=[DEFAULT_PYTHON_CONFIG],
    analyze_tests=False,
    analyze_dependencies=False,
    follow_imports=False,
    max_import_depth=0,
)


# Comprehensive pipeline (slow, all options)
COMPREHENSIVE_PIPELINE_CONFIG = PipelineConfig(
    name="comprehensive",
    description="Comprehensive pipeline with all optional stages enabled",
    run_stages=[
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
    stages=DEFAULT_STAGES,
    languages=[
        DEFAULT_PYTHON_CONFIG,
        DEFAULT_JAVASCRIPT_CONFIG,
        DEFAULT_JAVA_CONFIG,
    ],
    analyze_tests=True,
    analyze_dependencies=True,
    follow_imports=True,
    max_import_depth=10,  # Deeper exploration
)


# Default export configuration
DEFAULT_EXPORT_CONFIG = ExportConfig(
    primary_format=ExportFormat.JSON,
    additional_formats=[],
    output_dir="./cogant_output",
    create_bundle=True,
    bundle_name="cogant_bundle",
    compression="gzip",
    compression_level=6,
    include_provenance=True,
    include_metadata=True,
    include_statistics=True,
    minify_json=False,
    gnn_format=None,
    gnn_include_features=True,
    gnn_split_train_test=False,
    gnn_train_test_split=0.8,
)


# Minimal export (fast)
MINIMAL_EXPORT_CONFIG = ExportConfig(
    primary_format=ExportFormat.JSON,
    output_dir="./cogant_output",
    create_bundle=False,
    compression="none",
    include_provenance=False,
    include_metadata=True,
    include_statistics=False,
    minify_json=True,
)


# GNN-focused export
GNN_EXPORT_CONFIG = ExportConfig(
    primary_format=ExportFormat.JSON,
    additional_formats=[ExportFormat.PARQUET],
    output_dir="./gnn_output",
    create_bundle=True,
    compression="zstd",
    include_provenance=True,
    include_metadata=True,
    gnn_format="pytorch_geometric",
    gnn_include_features=True,
    gnn_split_train_test=True,
    gnn_train_test_split=0.8,
)


# Default validation configuration
DEFAULT_VALIDATION_CONFIG = ValidationConfig(
    level=ValidationLevel.MODERATE,
    validate_schema=True,
    validate_references=True,
    validate_graph_structure=True,
    min_provenance_coverage=0.8,
    min_mean_confidence=0.7,
    check_missing_mappings=True,
    check_unobservable_state=True,
    check_unreachable_code=False,
    warn_on_large_graph=True,
    large_graph_threshold=50000,
    generate_report=True,
    fail_on_error=False,
    auto_fix_warnings=False,
)


# Strict validation
STRICT_VALIDATION_CONFIG = ValidationConfig(
    level=ValidationLevel.STRICT,
    validate_schema=True,
    validate_references=True,
    validate_graph_structure=True,
    min_provenance_coverage=0.95,
    min_mean_confidence=0.85,
    check_missing_mappings=True,
    check_unobservable_state=True,
    check_unreachable_code=True,
    warn_on_large_graph=True,
    large_graph_threshold=30000,
    generate_report=True,
    fail_on_error=True,
    auto_fix_warnings=False,
)


# Lenient validation
LENIENT_VALIDATION_CONFIG = ValidationConfig(
    level=ValidationLevel.LENIENT,
    validate_schema=True,
    validate_references=False,
    validate_graph_structure=False,
    min_provenance_coverage=0.5,
    min_mean_confidence=0.5,
    check_missing_mappings=False,
    check_unobservable_state=False,
    check_unreachable_code=False,
    warn_on_large_graph=False,
    generate_report=True,
    fail_on_error=False,
    auto_fix_warnings=True,
)


# Preset configurations (legacy, kept for backward compatibility)
# Note: New presets should be defined in presets.py
PRESETS = {
    "default": {
        "cogant": DEFAULT_COGANT_CONFIG,
        "pipeline": DEFAULT_PIPELINE_CONFIG,
        "export": DEFAULT_EXPORT_CONFIG,
        "validation": DEFAULT_VALIDATION_CONFIG,
    },
    "minimal": {
        "cogant": DEFAULT_COGANT_CONFIG,
        "pipeline": MINIMAL_PIPELINE_CONFIG,
        "export": MINIMAL_EXPORT_CONFIG,
        "validation": LENIENT_VALIDATION_CONFIG,
    },
    "comprehensive": {
        "cogant": DEFAULT_COGANT_CONFIG,
        "pipeline": COMPREHENSIVE_PIPELINE_CONFIG,
        "export": DEFAULT_EXPORT_CONFIG,
        "validation": STRICT_VALIDATION_CONFIG,
    },
    "gnn": {
        "cogant": DEFAULT_COGANT_CONFIG,
        "pipeline": DEFAULT_PIPELINE_CONFIG,
        "export": GNN_EXPORT_CONFIG,
        "validation": DEFAULT_VALIDATION_CONFIG,
    },
}


def get_preset(name: str) -> Dict[str, Any]:
    """
    Get a preset configuration by name.

    Args:
        name: Preset name ('default', 'minimal', 'comprehensive', 'gnn')

    Returns:
        Dictionary of configuration objects

    Raises:
        ValueError: If preset name is unknown
    """
    if name not in PRESETS:
        available = ", ".join(PRESETS.keys())
        raise ValueError(
            f"Unknown preset '{name}'. Available presets: {available}"
        )
    return PRESETS[name]
