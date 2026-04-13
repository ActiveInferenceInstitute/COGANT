# Agents — parsers/go

## Owner

Parser Lead

## Responsibilities

- Go source code parsing and AST extraction
- Symbol table construction (structs, interfaces, functions, methods)
- Package and import resolution
- Method receiver parsing
- LanguagePlugin protocol compliance

## Implementation

- **parser.py** — GoLanguageParser class using regex-based extraction
- No external dependencies (uses Python re module)
- Returns ParseResult dataclass with structured AST information

## Methods

- `parse_file(path)` → ParseResult — Parse Go file
- `parse(source)` → Dict — Parse source code string to AST dict
- `extract_symbols(ast)` → List[Dict] — Extract symbol list
- `extract_types(ast)` → Dict — Extract type information
- `resolve_imports(ast)` → List[str] — List imported packages

## Supported Constructs

- Package declarations
- Import statements (block and single-line)
- Struct type definitions
- Interface type definitions
- Function declarations
- Method declarations (with receivers)
- Type declarations
- Module definitions

## Testing

- Integration tests in tests/unit/test_parsers.py
- Regex-based parser provides good coverage for common patterns
