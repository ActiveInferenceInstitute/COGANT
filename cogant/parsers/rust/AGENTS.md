# Agents — parsers/rust

## Owner

Parser Lead

## Responsibilities

- Rust source code parsing and AST extraction
- Symbol table construction (structs, enums, traits, functions)
- Trait and impl block resolution
- Use statement (import) tracking
- LanguagePlugin protocol compliance

## Implementation

- **parser.py** — RustLanguageParser class using regex-based extraction
- No external dependencies (uses Python re module)
- Returns ParseResult dataclass with structured AST information

## Methods

- `parse_file(path)` → ParseResult — Parse Rust file
- `parse(source)` → Dict — Parse source code string to AST dict
- `extract_symbols(ast)` → List[Dict] — Extract symbol list
- `extract_types(ast)` → Dict — Extract type information
- `resolve_imports(ast)` → List[str] — List imported modules

## Supported Constructs

- Struct definitions
- Enum definitions
- Trait definitions
- Impl blocks (implementations)
- Function declarations
- Module declarations
- Use statements (imports)
- Basic generics

## Testing

- Integration tests in tests/unit/test_parsers.py
- Regex-based parser provides good coverage for common patterns
