# Agents — py/cogant/config

## Owner

Infra Lead

## Responsibilities

Provide configuration schemas, loaders, and defaults for the entire COGANT system. Validate configurations against Pydantic models. Support YAML and JSON loading with environment variable overrides. Maintain backward compatibility with existing configuration files. Provide sensible defaults and named presets for common scenarios.

## Extending

Add new configuration fields to CogantConfig, PipelineConfig, ExportConfig, or ValidationConfig in schema.py. Update DEFAULT_*_CONFIG instances in defaults.py with sensible values. Create new preset functions in presets.py and register in get_preset. Add new LanguageConfig entries for new language support. Ensure all new fields are optional or have defaults to maintain backward compatibility.

## Coordination

Configuration feeds all subsystems (api, cli, plugins) via schema exports from __init__.py. Runtime Lead ensures config surface is stable; breaking changes require Architecture Lead approval. Environment variable overrides bypass file parsing for secrets and deployment-specific settings. Must not break existing cogant.yaml or .env configurations.

## Files

schema.py: Pydantic v2 BaseModel definitions for all configuration types (CogantConfig, PipelineConfig, ExportConfig, ValidationConfig, LanguageConfig, PipelineStage) and enums (LogLevel, ExportFormat, ValidationLevel). All fields have Field descriptions and validation constraints (ge, gt, default_factory).

defaults.py: Default instances (DEFAULT_COGANT_CONFIG, etc) and preset configurations (MINIMAL_PIPELINE_CONFIG, COMPREHENSIVE_PIPELINE_CONFIG, etc). PRESETS dict maps preset names to config bundles. get_preset function returns preset by name.

presets.py: Functions create_minimal_preset, create_standard_preset, create_comprehensive_preset, etc returning dicts with cogant, pipeline, export, validation configs. Each preset optimizes for specific use case (speed, quality, batch processing, etc).

loaders.py: ConfigLoader static class with load_from_yaml, load_json_from_file, load_from_dict, and merge_configs methods. ConfigLoadError exception.

__init__.py: Exports all schema classes, loader classes, default instances, preset getters (get_preset, list_presets, get_named_preset).
