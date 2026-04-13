# Rust Parser

Regex-based parser for Rust source code.

## Contents

- `parser.py` — RustLanguageParser implementation
- `__init__.py` — Package exports

## Usage

```python
from parsers.rust.parser import RustLanguageParser
from pathlib import Path

# Create parser
parser = RustLanguageParser()

# Parse a file
result = parser.parse_file(Path("lib.rs"))
print(f"Structs: {len(result.structs)}")
print(f"Traits: {len(result.traits)}")
print(f"Functions: {len(result.functions)}")

# Or parse source code
code = """
pub struct Person {
    name: String,
    age: u32,
}

impl Person {
    pub fn new(name: String) -> Person {
        Person { name, age: 0 }
    }
}
"""
ast_dict = parser.parse(code)
```

## Supported Features

- Struct definitions
- Enum definitions
- Trait definitions
- Impl blocks (implementations)
- Function declarations
- Module declarations
- Use statements (imports)
- Basic generics

## Output

ParseResult dataclass with:

- `file_path: Path` — Source file path
- `structs: List[Dict]` — Struct definitions
- `enums: List[Dict]` — Enum definitions
- `traits: List[Dict]` — Trait definitions
- `impls: List[Dict]` — Impl blocks
- `functions: List[Dict]` — Function declarations
- `modules: List[Dict]` — Module declarations
- `uses: List[Dict]` — Use statements
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
