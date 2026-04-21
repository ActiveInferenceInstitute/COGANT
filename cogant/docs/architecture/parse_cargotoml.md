## Parse Cargo.toml
metadata, deps = parser.parse_cargo_toml(Path("Cargo.toml"))
```

##### Dependency Structure:

```python
@dataclass
class Dependency:
    name: str              # Package name
    version: Optional[str] # Version specifier
    is_dev: bool          # Development dependency?
    is_local: bool        # Local/relative dependency?
```

### Static Analysis Stage

#### PythonASTParser

**Location:** `cogant.static.parser.PythonASTParser`

Parses Python source code using the standard `ast` module.

##### Features:
- Extract function definitions (name, parameters, decorators, docstring, return type)
- Extract class definitions (name, bases, methods, attributes)
- Extract imports (module names, relative/absolute)
- Extract assignments (target names, type annotations, values)

##### Usage:

```python
from cogant.static import PythonASTParser
from pathlib import Path

parser = PythonASTParser()
