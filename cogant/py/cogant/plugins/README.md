# Plugins — Extension Protocol System

Abstract base classes and plugin metadata for extending COGANT with custom language analyzers, trace ingestion, normalization rules, translation rules, state space compilation, process extraction, export formats, validation checks, and visualizations.

## Classes and Functions

PluginMetadata: Dataclass with name, version, author, and description for plugin identification.

Plugin: Abstract base class for all plugins. Constructor takes metadata. Abstract methods initialize (setup with config dict) and shutdown (graceful cleanup). Logging on load with metadata.

LanguagePlugin: Plugin for language-specific analysis with supported_languages set. Abstract methods: parse (source_code to AST dict), extract_symbols (AST to symbol list), extract_types (AST to type info dict), resolve_imports (AST to import paths).

TracePlugin: Plugin for dynamic trace ingestion. Abstract methods: parse_trace (trace_file to trace data dict), parse_coverage (coverage file path to coverage dict), extract_call_graph (trace data to call graph dict).

NormalizerPlugin: Plugin for normalizing different representations. Abstract methods: normalize (arbitrary data dict to canonical form), validate_schema (data dict to boolean).

TranslationRulePlugin: Plugin for custom GNN translation rules. Abstract methods: translate_nodes (graph node list to GNN node list), translate_edges (graph edge list to GNN edge list), compute_features (node dict to float feature vector).

StateSpacePlugin: Plugin for state space model compilation. Abstract methods: extract_states (GNN model dict to state dicts), extract_observations (GNN model dict to observation dicts), extract_actions (GNN model dict to action dicts), learn_policies (states/observations/actions dicts to policy dicts).

ProcessModelPlugin: Plugin for process/execution model extraction. Abstract methods: extract_stages (bundle dict to stage dicts), extract_dependencies (stage list to dependency dicts), compute_ordering (stages and dependencies to execution order list).

ExportPlugin: Plugin for custom export formats with supported_formats set. Abstract methods: export (bundle dict, output path, format to file write), get_format_info (format string to format info dict).

ValidationPlugin: Plugin for custom validation checks. Abstract methods: validate (bundle dict to validation results dict), compute_quality_metrics (bundle dict to float metrics dict).

VisualizationPlugin: Plugin for custom visualizations with supported_visualizations set. Abstract methods: render (bundle dict, output path, viz_type to file write), get_viz_info (viz_type to viz info dict).

## Usage Example

```python
from cogant.plugins import LanguagePlugin, PluginMetadata

class RustPlugin(LanguagePlugin):
    def __init__(self):
        super().__init__(PluginMetadata(
            name="rust-analyzer",
            version="0.1.0",
            author="COGANT Team"
        ))
        self.supported_languages = {"rust"}

    def initialize(self, config):
        pass

    def shutdown(self):
        pass

    def parse(self, source_code):
        # Parse Rust code to AST
        return {"ast": "..."}

    # ... implement other abstract methods
```

## Plugin Discovery

Plugins are abstract protocols; concrete implementations are loaded by runtime. Discovery mechanisms can be added in orchestration layer to find plugins by entry points, local directories, or dynamic imports.

## Dependencies

Standard library dataclasses, abc module for abstract base classes, typing for type hints. No external dependencies.
