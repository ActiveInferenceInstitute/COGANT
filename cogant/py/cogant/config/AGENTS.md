# Agents — py/cogant/config

## Owner

Infra Lead

## Responsibilities

Provide configuration schemas, loaders, and defaults for the entire COGANT system. Validate canonical sectioned YAML, JSON, and mapping inputs against ProjectConfig with schema version 1.0. Environment configuration uses COGANT_SECTION__FIELD; subsystem runtime toggles remain separate.

## Extending

Add fields to the owning typed model and its stub. Keep presets in the single presets.py registry. Test valid input, rejected input, and defaults < preset < file < environment < CLI precedence whenever changing loader behavior.

## Coordination

Configuration feeds subsystems via typed exports from __init__.py. Access sections as attributes; use model_dump for serialization. Every external layer must pass model validation before execution.

## Files

schema.py: Pydantic v2 BaseModel definitions for all configuration types (CogantConfig, PipelineConfig, ExportConfig, ValidationConfig, LanguageConfig, PipelineStage) and enums (LogLevel, ExportFormat, ValidationLevel). All fields have Field descriptions and validation constraints (ge, gt, default_factory).

defaults.py: Default instances (DEFAULT_COGANT_CONFIG, etc) and preset configurations (MINIMAL_PIPELINE_CONFIG, COMPREHENSIVE_PIPELINE_CONFIG, etc). PRESETS dict maps preset names to config bundles. get_preset function returns preset by name.

presets.py: Functions create_minimal_preset, create_standard_preset, create_comprehensive_preset, etc returning dicts with cogant, pipeline, export, validation configs. Each preset optimizes for specific use case (speed, quality, batch processing, etc).

loaders.py: ConfigLoader static class with load_from_yaml, load_json_from_file, load_from_dict, and merge_configs methods. ConfigLoadError exception.

__init__.py: Exports all schema classes, loader classes, default instances, preset getters (get_preset, list_presets, get_named_preset).
