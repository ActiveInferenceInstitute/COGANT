# TypeScript/JavaScript Parser

Regex-based parser for TypeScript and JavaScript source code.

## Contents

- `parser.py` — TypeScriptLanguageParser implementation
- `__init__.py` — Package exports

## Usage

```python
from parsers.typescript.parser import TypeScriptLanguageParser
from pathlib import Path

# Create parser
parser = TypeScriptLanguageParser()

# Parse a file
result = parser.parse_file(Path("example.ts"))
print(f"Classes: {len(result.classes)}")
print(f"Interfaces: {len(result.interfaces)}")
print(f"Functions: {len(result.functions)}")

# Or parse source code
code = """
export class User {
    name: string;
    age: number;
}

export function getUser(id: number): User {
    return { name: 'John', age: 30 };
}
"""
ast_dict = parser.parse(code)
```

## Supported Languages

- TypeScript (.ts, .tsx)
- JavaScript (.js, .jsx)

## Supported Features

- Class declarations with extends/implements
- Interface declarations
- Function declarations
- Method declarations
- Import statements (named, default, namespace)
- Export statements
- Type annotations (basic)
- Return type annotations

## Output

ParseResult dataclass with:

- `file_path: Path` — Source file path
- `classes: List[Dict]` — Class definitions
- `interfaces: List[Dict]` — Interface definitions
- `functions: List[Dict]` — Function declarations
- `imports: List[Dict]` — Import statements
- `exports: List[Dict]` — Export statements
- `errors: List[str]` — Parse errors encountered

## Plugin Interface

Implements `LanguagePlugin` protocol:

- `parse(source_code: str) -> Dict` — Parse source to AST
- `extract_symbols(ast: Dict) -> List[Dict]` — Extract symbol list
- `extract_types(ast: Dict) -> Dict` — Extract type information
- `resolve_imports(ast: Dict) -> List[str]` — List imported modules

## Implementation Notes

This parser uses regular expressions rather than a full AST parser. It provides good coverage for common patterns but may miss edge cases or complex constructs.

## Dependencies

- Python standard library (re module)
- cogant.plugins.base (LanguagePlugin)
