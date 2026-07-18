# Configuration

COGANT has one public configuration root: `ProjectConfig`. Every loader and
preset returns that validated Pydantic model. The precedence chain is:

`defaults < preset < file < environment < CLI`

## Classes and Functions

CogantBaseConfig: Base class for all COGANT configs using Pydantic ConfigDict with use_enum_values=False and validate_assignment=True.

CogantConfig: Top-level system configuration controlling logging (log_level, log_format, log_file), resource limits (max_workers, max_memory_mb, max_graph_nodes, timeout_seconds), caching (enable_caching, cache_dir, cache_ttl_hours), feature flags (enable_provenance_tracking, enable_validation, enable_gnn_export, enable_incremental_analysis), and strictness knobs (strict_schema_validation, fail_on_warnings, preserve_source_formatting).

LogLevel, ExportFormat, ValidationLevel: String enums for logging verbosity, export output format (JSON, Markdown, etc), and validation strictness (STRICT, LENIENT).

LanguageConfig: Configuration for language-specific analyzers, specifying language identifier, enabled flag, analyzer name and version, and analyzer-specific settings.

PipelineStage: Configuration for a single pipeline stage (name, enabled, timeout_seconds, retry_count, skip_on_error, parameters dict).

PipelineConfig: The canonical execution model for ordered stages, output
locations, runtime flags, dynamic inputs, and per-stage configuration.

ExportConfig: Configuration for output and export behavior (primary_format, output_dir, create_bundle, compression, include_provenance, include_metadata, include_statistics, minify_json, gnn_format).

ValidationConfig: Configuration for validation checks (level, validate_schema, validate_references, min_provenance_coverage, min_mean_confidence, check_missing_mappings, check_unobservable_state, warn_on_large_graph, generate_report, fail_on_error).

ServerConfig: Local-only host defaults, workspace/path policy, authentication,
request/archive byte and file limits, rate limits, bounded concurrency, and
request timeouts.

BatchConfig: Typed package/output roots, source targets, remote acquisition,
batch steps, archive limits, and optional manuscript stages.

ConfigLoader: Static utility class with `load_project_config`, `load_from_yaml`,
`load_json_from_file`, and `load_from_dict`. All of these validate the complete
`ProjectConfig`; `merge_configs` is only a mapping utility and does not bypass
validation.

ConfigLoadError: Exception raised when configuration loading fails.

DEFAULT_COGANT_CONFIG, DEFAULT_PIPELINE_CONFIG, DEFAULT_EXPORT_CONFIG, DEFAULT_VALIDATION_CONFIG: Module-level default instances for each config type.

MINIMAL_PIPELINE_CONFIG, COMPREHENSIVE_PIPELINE_CONFIG, GNN_EXPORT_CONFIG, STRICT_VALIDATION_CONFIG, LENIENT_VALIDATION_CONFIG: Pre-configured instances for common use cases.

DEFAULT_PYTHON_CONFIG, DEFAULT_JAVASCRIPT_CONFIG, DEFAULT_JAVA_CONFIG: Language-specific default analyzer configurations.

`get_preset`, `get_named_preset`, `list_presets`: Functions backed by the one
registry. The supported names are `default`, `minimal`, `standard`,
`comprehensive`, `gnn-focused`, and `security`.

## Usage Example

```python
from cogant.config import ConfigLoader, ProjectConfig, get_preset

# Load the complete typed root from YAML, then apply higher-precedence values.
config = ConfigLoader.load_project_config(
    "cogant.yaml",
    environment={"COGANT_SERVER__HOST": "127.0.0.1"},
    cli={"pipeline": {"verbose": True}},
)
assert isinstance(config, ProjectConfig)

# Use a preset
security_config = get_preset("security")

# Merge configs
merged = ConfigLoader.merge_configs(
    {"pipeline": {"verbose": False}},
    {"pipeline": {"verbose": True}},
)
```

## Dependencies

Pydantic v2 for validation and serialization, PyYAML for YAML parsing (optional), standard library for typing and file I/O.
