## Language Parser Plugin

### Interface

```python
from cogant.plugins import LanguagePlugin, PluginMetadata
from typing import Dict, Any, List

class MyLanguagePlugin(LanguagePlugin):
    """Plugin for MyLanguage."""
    
    def __init__(self):
        super().__init__(PluginMetadata(
            name="MyLanguage",
            version="1.0.0",
            author="You"
        ))
        self.supported_languages = {"mylanguage"}
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize with configuration."""
        pass
    
    def shutdown(self) -> None:
        """Shutdown gracefully."""
        pass
    
    def parse(self, source_code: str) -> Dict[str, Any]:
        """Parse source code and return AST dict."""
        # ... parsing logic ...
        return {"ast": [], "errors": [], "warnings": []}
    
    def extract_symbols(self, ast: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract symbols from AST."""
        return []
    
    def extract_types(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """Extract type information."""
        return {}
    
    def resolve_imports(self, ast: Dict[str, Any]) -> List[str]:
        """Resolve import dependencies."""
        return []
```

### Example: Simple Parser Plugin

```python
from cogant.plugins import LanguagePlugin, PluginMetadata

class SimpleParserPlugin(LanguagePlugin):
    def __init__(self):
        super().__init__(PluginMetadata(name="Simple", version="1.0.0"))
        self.supported_languages = {"simple"}

    def initialize(self, config): pass
    def shutdown(self): pass

    def parse(self, source_code: str):
        """Parse source and return AST dict."""
        functions = []
        for line_no, line in enumerate(source_code.split('\n'), 1):
            if line.startswith("def "):
                name = line.split()[1]
                functions.append({"name": name, "line": line_no, "kind": "function"})
        return {"ast": functions, "errors": [], "warnings": []}

    def extract_symbols(self, ast):
        return ast.get("ast", [])

    def extract_types(self, ast):
        return {}

    def resolve_imports(self, ast):
        return []
```

