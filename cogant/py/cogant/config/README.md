# Config — Configuration Schemas and Defaults

Comprehensive configuration system for COGANT with Pydantic v2 models, YAML/JSON loaders, sensible defaults, and named presets for common scenarios.

## Classes and Functions

CogantBaseConfig: Base class for all COGANT configs using Pydantic ConfigDict with use_enum_values=False and validate_assignment=True.

CogantConfig: Top-level system configuration controlling logging (log_level, log_format, log_file), resource limits (max_workers, max_memory_mb, max_graph_nodes, timeout_seconds), caching (enable_caching, cache_dir, cache_ttl_hours), feature flags (enable_provenance_tracking, enable_validation, enable_gnn_export, enable_incremental_analysis), and advanced options (strict_schema_validation, fail_on_warnings, preserve_source_formatting).

LogLevel, ExportFormat, ValidationLevel: String enums for logging verbosity, export output format (JSON, Markdown, etc), and validation strictness (STRICT, LENIENT).

LanguageConfig: Configuration for language-specific analyzers, specifying language identifier, enabled flag, analyzer name and version, and analyzer-specific settings.

PipelineStage: Configuration for a single pipeline stage (name, enabled, timeout_seconds, retry_count, skip_on_error, parameters dict).

PipelineConfig: Configuration for analysis pipeline execution with pipeline identity (name, description), stage specification (run_stages list, parallel_stages for concurrent execution), language configurations, and analysis options (analyze_tests, analyze_dependencies, follow_imports, max_import_depth).

ExportConfig: Configuration for output and export behavior (primary_format, output_dir, create_bundle, compression, include_provenance, include_metadata, include_statistics, minify_json, gnn_format).

ValidationConfig: Configuration for validation checks (level, validate_schema, validate_references, min_provenance_coverage, min_mean_confidence, check_missing_mappings, check_unobservable_state, warn_on_large_graph, generate_report, fail_on_error).

ConfigLoader: Static utility class with methods to load configurations from YAML (load_from_yaml), JSON (load_json_from_file), dictionaries (load_from_dict), and merge configs with override semantics (merge_configs supports deep recursive merging).

ConfigLoadError: Exception raised when configuration loading fails.

DEFAULT_COGANT_CONFIG, DEFAULT_PIPELINE_CONFIG, DEFAULT_EXPORT_CONFIG, DEFAULT_VALIDATION_CONFIG: Module-level default instances for each config type.

MINIMAL_PIPELINE_CONFIG, COMPREHENSIVE_PIPELINE_CONFIG, GNN_EXPORT_CONFIG, STRICT_VALIDATION_CONFIG, LENIENT_VALIDATION_CONFIG: Pre-configured instances for common use cases.

DEFAULT_PYTHON_CONFIG, DEFAULT_JAVASCRIPT_CONFIG, DEFAULT_JAVA_CONFIG: Language-specific default analyzer configurations.

get_preset, list_presets: Functions to retrieve and list named preset configurations. Presets include "minimal" (fast scan, core output), "standard" (balanced with common stages), "comprehensive" (all features), "gnn-focused" (optimized for GNN quality), "security" (boundary and security analysis), "research" (for research/publication quality), "review" (human-in-loop curation), and "batch" (high-volume processing).

## Usage Example

```python
from cogant.config import ConfigLoader, get_preset

# Load from YAML with overrides
base = ConfigLoader.load_from_yaml("cogant.yaml")
config = CogantConfig(**base)

# Use a preset
research_config = get_preset("research")

# Merge configs
merged = ConfigLoader.merge_configs(base, {"max_workers": 8})
```

## Dependencies

Pydantic v2 for validation and serialization, PyYAML for YAML parsing (optional), standard library for typing and file I/O.
