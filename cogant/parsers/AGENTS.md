# Agents — parsers/

## Owner

Parser Lead

## Responsibilities

- Language-specific AST extraction and symbol table construction
- LanguagePlugin protocol compliance across all parsers
- Language detection and parser selection (LanguageDetector)
- Cross-language parser consistency and validation
- Parser performance and fidelity benchmarks
- Supporting polyglot analysis across Python, TypeScript, JavaScript, Rust, and Go

## Architecture

- **Plugin System**: All parsers implement `LanguagePlugin` protocol
- **Language Detector**: Central dispatch via `cogant.ingest.language_detect.LanguageDetector`
- **Lazy Loading**: Parsers loaded on-demand by language name

## Implemented Parsers

- **python/** — Python AST parser (using Python's `ast` module)
- **typescript/** — TypeScript parser (regex-based); also handles JavaScript source
- **javascript/** — Thin re-export module: `JavaScriptLanguageParser` is an alias for `TypeScriptLanguageParser` from `parsers.typescript.parser`. No standalone parser file — add one here if JS ever diverges from TS
- **rust/** — Rust parser (regex-based)
- **go/** — Go parser (regex-based)

## Parser Registration

Each parser must:

1. Implement `LanguagePlugin` from `cogant.plugins.base`
2. Define `supported_languages` set and `supported_extensions` set
3. Register in `LanguageDetector.PARSER_CLASSES` dictionary
4. Implement 4 abstract methods: parse, extract_symbols, extract_types, resolve_imports

## Output Format

All parsers return compatible structures:
- Language-specific `ParseResult` dataclass with common fields
- Consistent Dict format from AST representation
- Error handling with graceful degradation
