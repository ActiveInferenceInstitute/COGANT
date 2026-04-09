# Agents — parsers/typescript

## Owner

Parser Lead

## Responsibilities

- TypeScript and JavaScript source code parsing
- Symbol table construction (classes, interfaces, functions)
- Type annotation extraction
- Module resolution with imports/exports
- LanguagePlugin protocol compliance

## Implementation

- **parser.py** — TypeScriptLanguageParser class using regex-based extraction
- Supports both TypeScript (.ts, .tsx) and JavaScript (.js, .jsx)
- No external dependencies (uses Python re module)
- Returns ParseResult dataclass with structured AST information

## Methods

- `parse_file(path)` → ParseResult — Parse TypeScript/JavaScript file
- `parse(source)` → Dict — Parse source code string to AST dict
- `extract_symbols(ast)` → List[Dict] — Extract symbol list
- `extract_types(ast)` → Dict — Extract type information
- `resolve_imports(ast)` → List[str] — List imported modules

## Supported Constructs

- Class declarations with extends/implements
- Interface declarations
- Function declarations
- Method declarations
- Import statements (named, default, namespace)
- Export statements
- Type annotations (basic)
- Return type annotations

## Testing

- Integration tests in tests/unit/test_parsers.py
- Regex-based parser provides good coverage for common patterns
