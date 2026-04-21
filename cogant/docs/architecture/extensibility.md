## Extensibility

### Custom Rules

Users can define custom translation rules:

```python
from cogant.translate.engine import TranslationRule
from cogant.schemas.semantic import SemanticMapping

class MyCustomRule(TranslationRule):
    def matches(self, graph, query):
        # Return list of match dicts
        return [...]

    def apply(self, match, graph, query):
        return SemanticMapping(...)
```

### Custom Language Plugins

Support for new languages via the plugin system:

```python
from cogant.plugins import LanguagePlugin, PluginMetadata

class MyLanguagePlugin(LanguagePlugin):
    def __init__(self):
        super().__init__(PluginMetadata(name="MyLang", version="1.0.0"))
        self.supported_languages = {"mylang"}

    def initialize(self, config): ...
    def shutdown(self): ...
    def parse(self, source_code): ...
    def extract_symbols(self, ast): ...
    def extract_types(self, ast): ...
    def resolve_imports(self, ast): ...
```

### Custom Export Formats

Add new export formats via the plugin system:

```python
from cogant.plugins import ExportPlugin, PluginMetadata

class MyFormat(ExportPlugin):
    def __init__(self):
        super().__init__(PluginMetadata(name="MyFormat", version="1.0.0"))
        self.supported_formats = {"myformat"}

    def initialize(self, config): ...
    def shutdown(self): ...
    def export(self, bundle, output_path, fmt): ...
    def get_format_info(self, fmt): ...
```
