# Agents — py/cogant/plugins

## Owner

Infra Lead

## Responsibilities

Define plugin protocol system via abstract base classes. Specify extension points for language analysis, trace ingestion, normalization, translation rules, state space compilation, process extraction, export formats, validation, and visualization. Ensure plugin API is stable and backward compatible. Support plugin lifecycle management (initialization, shutdown).

## Extending

Create new plugin type by subclassing Plugin and defining abstract methods for the specific extension point. Use supported_languages or supported_formats set attributes for feature declaration. Implement initialize and shutdown for lifecycle. Document method signatures clearly. Register new plugin types in __init__.py __all__ export. New extension points require Architecture Lead approval to ensure stability.

## Coordination

Provides hooks for third-party extensions without modifying core API. Plugin metadata includes name, version, author, description for discovery and conflict resolution. Runtime Lead ensures plugins integrate cleanly with pipeline stages. Plugins should be stateless where possible and thread-safe.

## Files

base.py: PluginMetadata dataclass and Plugin abstract base class. LanguagePlugin for AST parsing, symbol extraction, type extraction, import resolution. TracePlugin for trace parsing and coverage ingestion. NormalizerPlugin for representation canonicalization. TranslationRulePlugin for GNN node/edge translation and feature computation. StateSpacePlugin for state/observation/action extraction and policy learning. ProcessModelPlugin for stage and dependency extraction. ExportPlugin for custom export formats. ValidationPlugin for validation checks and metrics. VisualizationPlugin for custom rendering.

__init__.py: Exports all plugin base classes and PluginMetadata.
