# Agents — parsers/javascript

## Owner

Parser Lead

## Responsibilities

- JavaScript source code parsing
- Symbol table construction (functions, classes, variables)
- Module (CommonJS and ESM) resolution
- Unified handling with TypeScript parser
- LanguagePlugin protocol compliance

## Implementation

- **__init__.py** — Exports JavaScriptLanguageParser as alias to TypeScriptLanguageParser
- Actual parser implementation in `parsers/typescript/parser.py`
- JavaScript and TypeScript share the same parser since syntax is largely compatible

## Methods

- `parse_file(path)` → ParseResult — Parse JavaScript file
- `parse(source)` → Dict — Parse source code string to AST dict
- `extract_symbols(ast)` → List[Dict] — Extract symbol list
- `extract_types(ast)` → Dict — Extract type information
- `resolve_imports(ast)` → List[str] — List imported modules

## Supported Constructs

- Functions and arrow functions
- Classes and constructors
- Function declarations
- Module imports/exports (CommonJS and ESM)
- Variable declarations
- Basic type annotations (JSDoc style)

## Testing

- Integration tests in tests/unit/test_parsers.py
- Uses TypeScriptLanguageParser implementation
