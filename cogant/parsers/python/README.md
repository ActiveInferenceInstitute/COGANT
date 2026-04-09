# Python Parser

Python source code parser using the standard AST module.

## Contents

- `parser.py` — PythonLanguageParser implementation
- `__init__.py` — Package exports

## Usage

```python
from parsers.python.parser import PythonLanguageParser
from pathlib import Path

# Create parser
parser = PythonLanguageParser()

# Parse a file
result = parser.parse_file(Path("example.py"))
print(f"Classes: {len(result.classes)}")
print(f"Functions: {len(result.functions)}")
print(f"Imports: {len(result.imports)}")

# Or parse source code
code = """
def my_function(x):
    return x * 2
"""
ast_dict = parser.parse(code)
```

## Supported Features

- Classes and inheritance
- Functions and methods (including async)
- Decorators
- Type annotations
- Import statements (from, import, relative)
- Module docstrings
- Assignments with type hints

## Output

ParseResult dataclass with:

- `file_path: Path` — Source file path
- `classes: List[Dict]` — Class definitions with methods
- `functions: List[Dict]` — Module-level functions
- `imports: List[Dict]` — Import statements
- `assignments: List[Dict]` — Variable assignments
- `docstring: str` — Module docstring
- `errors: List[str]` — Parse errors encountered

## Plugin Interface

Implements `LanguagePlugin` protocol:

- `parse(source_code: str) -> Dict` — Parse source to AST
- `extract_symbols(ast: Dict) -> List[Dict]` — Extract symbol list
- `extract_types(ast: Dict) -> Dict` — Extract type information
- `resolve_imports(ast: Dict) -> List[str]` — List imported modules

## Dependencies

- Python standard library (ast module)
- cogant.plugins.base (LanguagePlugin)
- cogant.static.parser (PythonASTParser)
