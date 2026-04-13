# Agents — parsers/python

## Owner

Parser Lead

## Responsibilities

- Python source code parsing via ast module
- Symbol table construction (classes, functions, variables)
- Type hint extraction (PEP 484, 585, 604, etc.)
- Import and module resolution
- LanguagePlugin protocol compliance

## Implementation

- **parser.py** — PythonLanguageParser class wrapping cogant.static.parser.PythonASTParser
- Uses Python 3.8+ built-in ast module (no external dependencies)
- Returns ParseResult dataclass with structured AST information

## Methods

- `parse_file(path)` → ParseResult — Parse Python file
- `parse(source)` → Dict — Parse source code string to AST dict
- `extract_symbols(ast)` → List[Dict] — Extract symbol list
- `extract_types(ast)` → Dict — Extract type information
- `resolve_imports(ast)` → List[str] — List imported modules

## Supported Constructs

- Classes and inheritance
- Functions and methods (including async)
- Decorators
- Type annotations
- Import statements
- Module docstrings
- Assignments with type hints

## Testing

- Integration tests in tests/unit/test_parsers.py
- Uses example files in examples/control_positive/
