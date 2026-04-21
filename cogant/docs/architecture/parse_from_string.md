## Parse from string
source = """
def hello(name: str) -> str:
    '''Say hello.'''
    return f"Hello, {name}!"

class Greeter:
    def greet(self, name: str) -> str:
        return f"Hi, {name}!"
"""
module = parser.parse_string(source, Path("example.py"))

print(f"Functions: {len(module.functions)}")
print(f"Classes: {len(module.classes)}")
print(f"Imports: {len(module.imports)}")

for func in module.functions:
    print(f"  Function: {func.name}")
    print(f"    Args: {func.args}")
    print(f"    Return type: {func.return_annotation}")
    print(f"    Decorators: {func.decorators}")
    print(f"    Async: {func.is_async}")
```

##### PythonModule Structure:

```python
@dataclass
class PythonModule:
    file_path: Path
    docstring: Optional[str]
    functions: List[FunctionDef]
    classes: List[ClassDef]
    imports: List[ImportDef]
    assignments: List[AssignmentDef]
    errors: List[str]
```

#### SymbolExtractor

**Location:** `cogant.static.symbols.SymbolExtractor`

Builds symbol table from parsed Python code with qualified names and scopes.

##### Features:
- Extract module, class, function, method, and variable symbols
- Generate stable, deterministic symbol IDs (SHA256 hash)
- Build qualified names (e.g., `module.ClassName.method_name`)
- Capture docstrings and decorators
- Track parent-child relationships

##### Usage:

```python
from cogant.static import SymbolExtractor
from pathlib import Path

extractor = SymbolExtractor(repo_root=Path("."))
