"""
Named configuration presets for COGANT system.

Provides optimized presets for common analysis scenarios:
- minimal: Fast analysis, core stages only
- standard: Balanced approach with common stages
- comprehensive: All features enabled
- gnn-focused: Optimized for GNN export quality
- security: Boundary and security analysis
"""

from .schema import (
    CogantConfig,
    ExportConfig,
    ExportFormat,
    LanguageConfig,
    LogLevel,
    PipelineConfig,
    PipelineStage,
    ValidationConfig,
    ValidationLevel,
)


def create_minimal_preset() -> dict:
    """
    Minimal preset: Fast scan with core output.

    Enables only essential stages (ingest, normalize, graph, validate, export).
    Excludes tests and dependencies. Good for quick analysis of small codebases.
    """
    cogant = CogantConfig(
        version="1.0.0",
        environment="production",
        log_level=LogLevel.WARNING,
        max_workers=2,
        max_memory_mb=2048,
        max_graph_nodes=50000,
        timeout_seconds=120.0,
        enable_caching=True,
        cache_ttl_hours=6,
        enable_provenance_tracking=False,
        enable_validation=True,
        enable_gnn_export=False,
        strict_schema_validation=False,
    )

    pipeline = PipelineConfig(
        name="minimal",
        description="Minimal pipeline: fast scan with core output",
        run_stages=["ingest", "normalize", "graph", "validate", "export"],
        stages={
            "ingest": PipelineStage(
                name="ingest",
                enabled=True,
                timeout_seconds=300.0,
                parameters={"format": "auto", "encoding": "utf-8"},
            ),
            "normalize": PipelineStage(
                name="normalize",
                enabled=True,
                timeout_seconds=150.0,
                parameters={"normalize_identifiers": True},
            ),
            "graph": PipelineStage(
                name="graph",
                enabled=True,
                timeout_seconds=300.0,
                parameters={
                    "build_call_graph": True,
                    "build_type_graph": False,
                    "build_data_flow": False,
                },
            ),
            "validate": PipelineStage(
                name="validate",
                enabled=True,
                timeout_seconds=120.0,
                skip_on_error=False,
            ),
            "export": PipelineStage(
                name="export",
                enabled=True,
                timeout_seconds=120.0,
                parameters={
                    "format": "json",
                    "compress": True,
                    "create_bundle": False,
                },
            ),
        },
        languages=[
            LanguageConfig(
                language="python",
                enabled=True,
                analyzer_name="ast-analyzer",
                analyzer_config={"follow_imports": False},
            )
        ],
        analyze_tests=False,
        analyze_dependencies=False,
        follow_imports=False,
        max_import_depth=0,
    )

    export = ExportConfig(
        primary_format=ExportFormat.JSON,
        output_dir="./cogant_output",
        create_bundle=False,
        compression="none",
        include_provenance=False,
        include_metadata=False,
        include_statistics=False,
        minify_json=True,
        gnn_format=None,
    )

    validation = ValidationConfig(
        level=ValidationLevel.LENIENT,
        validate_schema=True,
        validate_references=False,
        min_provenance_coverage=0.5,
        min_mean_confidence=0.5,
        check_missing_mappings=False,
        check_unobservable_state=False,
        warn_on_large_graph=False,
        generate_report=False,
        fail_on_error=False,
    )

    return {
        "cogant": cogant,
        "pipeline": pipeline,
        "export": export,
        "validation": validation,
    }


def create_standard_preset() -> dict:
    """
    Standard preset: Balanced analysis with common stages.

    Enables core and optional stages (ingest, normalize, graph, semantic_mapping,
    validate, export). Good for typical codebase analysis.
    """
    cogant = CogantConfig(
        version="1.0.0",
        environment="production",
        log_level=LogLevel.INFO,
        max_workers=4,
        max_memory_mb=4096,
        max_graph_nodes=100000,
        timeout_seconds=300.0,
        enable_caching=True,
        cache_ttl_hours=24,
        enable_provenance_tracking=True,
        enable_validation=True,
        enable_gnn_export=False,
        strict_schema_validation=True,
    )

    pipeline = PipelineConfig(
        name="standard",
        description="Standard pipeline: balanced analysis with common stages",
        run_stages=[
            "ingest",
            "normalize",
            "graph",
            "semantic_mapping",
            "validate",
            "export",
        ],
        languages=[
            LanguageConfig(
                language="python",
                enabled=True,
                analyzer_name="ast-analyzer",
                analyzer_config={
                    "follow_imports": True,
                    "analyze_type_hints": True,
                },
            ),
        ],
        analyze_tests=True,
        analyze_dependencies=True,
        follow_imports=True,
        max_import_depth=3,
    )

    export = ExportConfig(
        primary_format=ExportFormat.JSON,
        output_dir="./cogant_output",
        create_bundle=True,
        compression="gzip",
        include_provenance=True,
        include_metadata=True,
        include_statistics=True,
        minify_json=False,
        gnn_format=None,
    )

    validation = ValidationConfig(
        level=ValidationLevel.MODERATE,
        validate_schema=True,
        validate_references=True,
        validate_graph_structure=True,
        min_provenance_coverage=0.8,
        min_mean_confidence=0.7,
        check_missing_mappings=True,
        check_unobservable_state=True,
        warn_on_large_graph=True,
        generate_report=True,
        fail_on_error=False,
    )

    return {
        "cogant": cogant,
        "pipeline": pipeline,
        "export": export,
        "validation": validation,
    }


def create_comprehensive_preset() -> dict:
    """
    Comprehensive preset: All features enabled for deep analysis.

    Enables all pipeline stages including state_space and process_model.
    Includes tests and dependencies with deep import analysis.
    """
    cogant = CogantConfig(
        version="1.0.0",
        environment="production",
        log_level=LogLevel.DEBUG,
        max_workers=8,
        max_memory_mb=8192,
        max_graph_nodes=200000,
        timeout_seconds=600.0,
        enable_caching=True,
        cache_ttl_hours=48,
        enable_provenance_tracking=True,
        enable_validation=True,
        enable_gnn_export=True,
        strict_schema_validation=True,
    )

    pipeline = PipelineConfig(
        name="comprehensive",
        description="Comprehensive pipeline: all features enabled",
        run_stages=[
            "ingest",
            "normalize",
            "graph",
            "semantic_mapping",
            "state_space",
            "process_model",
            "validate",
            "export",
        ],
        languages=[
            LanguageConfig(
                language="python",
                enabled=True,
                analyzer_name="ast-analyzer",
                analyzer_config={
                    "follow_imports": True,
                    "analyze_type_hints": True,
                    "extract_docstrings": True,
                },
            ),
        ],
        analyze_tests=True,
        analyze_dependencies=True,
        follow_imports=True,
        max_import_depth=10,
    )

    export = ExportConfig(
        primary_format=ExportFormat.JSON,
        additional_formats=[ExportFormat.PARQUET],
        output_dir="./cogant_output",
        create_bundle=True,
        compression="zstd",
        compression_level=9,
        include_provenance=True,
        include_metadata=True,
        include_statistics=True,
        minify_json=False,
        gnn_format="pytorch_geometric",
        gnn_include_features=True,
        gnn_split_train_test=False,
    )

    validation = ValidationConfig(
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
    )

    return {
        "cogant": cogant,
        "pipeline": pipeline,
        "export": export,
        "validation": validation,
    }


def create_gnn_focused_preset() -> dict:
    """
    GNN-focused preset: Optimized for graph neural network export quality.

    Includes all stages with emphasis on feature extraction and graph quality.
    Exports to PyTorch Geometric and Parquet formats with full feature sets.
    """
    cogant = CogantConfig(
        version="1.0.0",
        environment="production",
        log_level=LogLevel.INFO,
        max_workers=6,
        max_memory_mb=8192,
        max_graph_nodes=150000,
        timeout_seconds=600.0,
        enable_caching=True,
        cache_ttl_hours=48,
        enable_provenance_tracking=True,
        enable_validation=True,
        enable_gnn_export=True,
        strict_schema_validation=True,
    )

    pipeline = PipelineConfig(
        name="gnn-focused",
        description="GNN-focused: optimized for graph neural network export",
        run_stages=[
            "ingest",
            "normalize",
            "graph",
            "semantic_mapping",
            "state_space",
            "validate",
            "export",
        ],
        languages=[
            LanguageConfig(
                language="python",
                enabled=True,
                analyzer_name="ast-analyzer",
                analyzer_config={
                    "follow_imports": True,
                    "analyze_type_hints": True,
                    "extract_docstrings": True,
                },
            ),
        ],
        analyze_tests=True,
        analyze_dependencies=True,
        follow_imports=True,
        max_import_depth=5,
    )

    export = ExportConfig(
        primary_format=ExportFormat.JSON,
        additional_formats=[ExportFormat.PARQUET],
        output_dir="./gnn_output",
        create_bundle=True,
        compression="zstd",
        compression_level=6,
        include_provenance=True,
        include_metadata=True,
        include_statistics=True,
        minify_json=False,
        gnn_format="pytorch_geometric",
        gnn_include_features=True,
        gnn_split_train_test=True,
        gnn_train_test_split=0.8,
    )

    validation = ValidationConfig(
        level=ValidationLevel.STRICT,
        validate_schema=True,
        validate_references=True,
        validate_graph_structure=True,
        min_provenance_coverage=0.9,
        min_mean_confidence=0.8,
        check_missing_mappings=True,
        check_unobservable_state=True,
        check_unreachable_code=False,
        warn_on_large_graph=True,
        large_graph_threshold=150000,
        generate_report=True,
        fail_on_error=False,
    )

    return {
        "cogant": cogant,
        "pipeline": pipeline,
        "export": export,
        "validation": validation,
    }


def create_security_preset() -> dict:
    """
    Security preset: Focus on boundary and security analysis.

    Emphasizes call graph, type information, and boundary detection.
    Skips test files. Strict validation with focus on control flow.
    """
    cogant = CogantConfig(
        version="1.0.0",
        environment="production",
        log_level=LogLevel.INFO,
        max_workers=4,
        max_memory_mb=4096,
        max_graph_nodes=100000,
        timeout_seconds=600.0,
        enable_caching=True,
        cache_ttl_hours=24,
        enable_provenance_tracking=True,
        enable_validation=True,
        enable_gnn_export=False,
        strict_schema_validation=True,
    )

    pipeline = PipelineConfig(
        name="security",
        description="Security-focused: boundary and control flow analysis",
        run_stages=[
            "ingest",
            "normalize",
            "graph",
            "semantic_mapping",
            "validate",
            "export",
        ],
        languages=[
            LanguageConfig(
                language="python",
                enabled=True,
                analyzer_name="ast-analyzer",
                analyzer_config={
                    "follow_imports": True,
                    "analyze_type_hints": True,
                },
            ),
        ],
        analyze_tests=False,
        analyze_dependencies=True,
        follow_imports=True,
        max_import_depth=5,
    )

    export = ExportConfig(
        primary_format=ExportFormat.JSON,
        output_dir="./security_analysis",
        create_bundle=True,
        compression="gzip",
        include_provenance=True,
        include_metadata=True,
        include_statistics=True,
        minify_json=False,
        gnn_format=None,
    )

    validation = ValidationConfig(
        level=ValidationLevel.STRICT,
        validate_schema=True,
        validate_references=True,
        validate_graph_structure=True,
        min_provenance_coverage=0.9,
        min_mean_confidence=0.8,
        check_missing_mappings=True,
        check_unobservable_state=True,
        check_unreachable_code=True,
        warn_on_large_graph=True,
        generate_report=True,
        fail_on_error=True,
        auto_fix_warnings=False,
    )

    return {
        "cogant": cogant,
        "pipeline": pipeline,
        "export": export,
        "validation": validation,
    }


PRESETS = {
    "minimal": create_minimal_preset(),
    "standard": create_standard_preset(),
    "comprehensive": create_comprehensive_preset(),
    "gnn-focused": create_gnn_focused_preset(),
    "security": create_security_preset(),
}


def get_preset(name: str) -> dict:
    """
    Get a preset configuration by name.

    Args:
        name: Preset name ('minimal', 'standard', 'comprehensive', 'gnn-focused', 'security')

    Returns:
        Dictionary with 'cogant', 'pipeline', 'export', 'validation' config objects.

    Raises:
        ValueError: If preset name is unknown.
    """
    if name not in PRESETS:
        available = ", ".join(PRESETS.keys())
        raise ValueError(
            f"Unknown preset '{name}'. Available presets: {available}"
        )
    return PRESETS[name]


def list_presets() -> list:
    """Get list of available preset names."""
    return list(PRESETS.keys())
