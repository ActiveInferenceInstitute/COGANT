# Go Parser

Regex-based parser for Go source code.

## Contents

- `parser.py` — GoLanguageParser implementation
- `__init__.py` — Package exports

## Usage

```python
from parsers.go.parser import GoLanguageParser
from pathlib import Path

# Create parser
parser = GoLanguageParser()

# Parse a file
result = parser.parse_file(Path("main.go"))
print(f"Package: {result.package}")
print(f"Structs: {len(result.structs)}")
print(f"Interfaces: {len(result.interfaces)}")
print(f"Functions: {len(result.functions)}")

# Or parse source code
code = """
package main

import "fmt"

type Person struct {
    Name string
    Age  int
}

func (p *Person) String() string {
    return fmt.Sprintf("%s (%d)", p.Name, p.Age)
}

func main() {
    p := &Person{Name: "Alice", Age: 30}
    fmt.Println(p)
}
"""
ast_dict = parser.parse(code)
```

## Supported Features

- Package declarations
- Import statements (block and single-line)
- Struct type definitions
- Interface type definitions
- Function declarations
- Method declarations (receivers)
- Type declarations
- Module definitions

## Output

ParseResult dataclass with:

- `file_path: Path` — Source file path
- `package: str` — Package name
- `imports: List[Dict]` — Import statements
- `structs: List[Dict]` — Struct type definitions
- `interfaces: List[Dict]` — Interface type definitions
- `functions: List[Dict]` — Function declarations
- `methods: List[Dict]` — Method declarations
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
