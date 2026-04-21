## Plugin API

Extend COGANT with custom plugins.

### Language Plugin

```python
from cogant.plugins import LanguagePlugin, PluginMetadata

class MyLanguagePlugin(LanguagePlugin):
    def __init__(self):
        super().__init__(PluginMetadata(
            name="MyLanguage",
            version="1.0.0",
            author="You"
        ))
        self.supported_languages = {"mylang"}

    def initialize(self, config):
        pass

    def shutdown(self):
        pass

    def parse(self, source_code):
        # Parse source code
        return {"ast": [...]}

    def extract_symbols(self, ast):
        # Extract symbols
        return [...]

    def extract_types(self, ast):
        # Extract types
        return {...}

    def resolve_imports(self, ast):
        # Resolve imports
        return [...]
```

### Custom Export Plugin

```python
from cogant.plugins import ExportPlugin, PluginMetadata

class CustomExportPlugin(ExportPlugin):
    def __init__(self):
        super().__init__(PluginMetadata(
            name="CustomExport",
            version="1.0.0"
        ))
        self.supported_formats = {"custom"}

    def initialize(self, config):
        pass

    def shutdown(self):
        pass

    def export(self, bundle, output_path, format):
        # Export bundle in custom format
        pass

    def get_format_info(self, format):
        # Return format info
        return {}
```
