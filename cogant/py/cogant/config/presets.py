"""The single validated project-configuration preset registry."""

from __future__ import annotations

from .pipeline import PipelineConfig
from .schema import (
    BatchConfig,
    CogantConfig,
    ExportConfig,
    ExportFormat,
    ProjectConfig,
    ServerConfig,
    ValidationConfig,
    ValidationLevel,
)


def _standard() -> ProjectConfig:
    return ProjectConfig()


def _minimal() -> ProjectConfig:
    return ProjectConfig(
        cogant=CogantConfig(
            log_level="warning",
            max_workers=2,
            max_memory_mb=2048,
            max_graph_nodes=50_000,
            timeout_seconds=120.0,
            enable_gnn_export=False,
            enable_provenance_tracking=True,
        ),
        pipeline=PipelineConfig(
            stages=["ingest", "static", "normalize", "graph", "export", "validate"],
            skip_dynamic=True,
            render_visualizations=False,
        ),
        export=ExportConfig(
            primary_format=ExportFormat.JSON,
            output_dir="output",
            create_bundle=False,
            compression="none",
            include_provenance=True,
            include_metadata=True,
            include_statistics=False,
        ),
        validation=ValidationConfig(
            level=ValidationLevel.MODERATE,
            validate_schema=True,
            validate_references=True,
            min_provenance_coverage=0.5,
            min_mean_confidence=0.5,
            check_missing_mappings=False,
            check_unobservable_state=False,
            generate_report=True,
            fail_on_error=True,
        ),
    )


def _comprehensive() -> ProjectConfig:
    return ProjectConfig(
        pipeline=PipelineConfig(
            stages=[
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
            ],
            render_visualizations=True,
            profiling_enabled=True,
        ),
        validation=ValidationConfig(
            level=ValidationLevel.STRICT,
            validate_schema=True,
            validate_references=True,
            validate_graph_structure=True,
            min_provenance_coverage=0.95,
            min_mean_confidence=0.85,
            check_missing_mappings=True,
            check_unobservable_state=True,
            check_unreachable_code=True,
            generate_report=True,
            fail_on_error=True,
        ),
    )


def _gnn_focused() -> ProjectConfig:
    return ProjectConfig(
        pipeline=PipelineConfig(
            stages=["ingest", "static", "normalize", "graph", "translate", "statespace", "export", "validate"],
            render_visualizations=True,
            gnn={"include_metadata": True, "include_connections": True, "include_matrices": True},
        ),
        export=ExportConfig(
            primary_format=ExportFormat.JSON,
            output_dir="output",
            create_bundle=True,
            compression="gzip",
            include_provenance=True,
            include_metadata=True,
            include_statistics=True,
        ),
        validation=ValidationConfig(
            level=ValidationLevel.STRICT,
            validate_schema=True,
            validate_references=True,
            validate_graph_structure=True,
            min_provenance_coverage=0.95,
            min_mean_confidence=0.8,
            fail_on_error=True,
        ),
    )


def _security() -> ProjectConfig:
    return ProjectConfig(
        cogant=CogantConfig(
            strict_schema_validation=True,
            fail_on_warnings=True,
            enable_provenance_tracking=True,
            enable_validation=True,
        ),
        pipeline=PipelineConfig(
            stages=["ingest", "static", "normalize", "graph", "export", "validate"],
            skip_dynamic=True,
            render_visualizations=False,
        ),
        validation=ValidationConfig(
            level=ValidationLevel.STRICT,
            validate_schema=True,
            validate_references=True,
            validate_graph_structure=True,
            min_provenance_coverage=1.0,
            min_mean_confidence=0.9,
            check_missing_mappings=True,
            check_unobservable_state=True,
            check_unreachable_code=True,
            fail_on_error=True,
        ),
        server=ServerConfig(
            host="127.0.0.1",
            workspace_root=".",
            allow_absolute_paths=False,
            max_request_bytes=1_000_000,
            max_gnn_text_bytes=500_000,
            max_archive_bytes=10_000_000,
            max_archive_files=250,
            rate_limit_requests=5,
            rate_limit_window_seconds=60,
        ),
        batch=BatchConfig(
            max_targets=25,
            max_archive_files=250,
            max_archive_bytes=10_000_000,
        ),
    )


PRESETS: dict[str, ProjectConfig] = {
    "default": _standard(),
    "minimal": _minimal(),
    "standard": _standard(),
    "comprehensive": _comprehensive(),
    "gnn-focused": _gnn_focused(),
    "security": _security(),
}


def get_preset(name: str) -> ProjectConfig:
    """Return a validated preset or raise a typed lookup error."""
    try:
        return PRESETS[name]
    except KeyError as exc:
        available = ", ".join(PRESETS)
        raise ValueError(f"Unknown preset '{name}'. Available: {available}") from exc


def list_presets() -> list[str]:
    """Return the stable preset names in registry order."""
    return list(PRESETS)
