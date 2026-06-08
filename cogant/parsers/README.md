# Parsers — Language-Specific AST Extraction

Polyglot language parsers converting source code to symbols and ASTs.

## Contents

- **python/** — Python parser (AST-based via `ast` module)
- **typescript/** — TypeScript parser (regex-based); also handles JavaScript source through the compatibility path
- **javascript/** — Tree-sitter backed `JavaScriptLanguageParser` delegating to `cogant.parsers.tree_sitter_base.TreeSitterParser`; the compatibility regex alias remains available as `LegacyJavaScriptLanguageParser`
- **rust/** — Rust parser (regex-based)
- **go/** — Go parser (regex-based)

## Parser Architecture

Each parser implements the `LanguagePlugin` protocol from `cogant.plugins.base`:

```python
class LanguagePlugin(Plugin):
    def parse(self, source_code: str) -> Dict[str, Any]:
        """Parse source code and return AST."""

    def extract_symbols(self, ast: Dict) -> List[Dict]:
        """Extract symbols from AST."""

    def extract_types(self, ast: Dict) -> Dict:
        """Extract type information."""

    def resolve_imports(self, ast: Dict) -> List[str]:
        """Resolve import dependencies."""
```

## Parser Output

Each parser returns a `ParseResult` dataclass with:

- `file_path: Path` — Source file path
- Language-specific symbols (classes, functions, structs, etc.)
- `imports: List[Dict]` — Import/use statements
- `errors: List[str]` — Parse errors encountered

## Language Detection

The `LanguageDetector` class in `cogant.ingest.language_detect` provides:

```python
# Detect language from file extension
lang = LanguageDetector.detect_language(Path("file.ts"))

# Count languages in repository
langs = LanguageDetector.detect_repo_languages(Path("/repo"))

# Get parser for language
parser = LanguageDetector.get_parser("python")
```

## Implementation Approach

- **Python**: Full AST parsing via Python's `ast` module (no external deps)
- **JavaScript**: Tree-sitter backed (`tree_sitter_javascript` grammar) with an embedded fallback to the compatibility regex TypeScript parser when the grammar is unavailable
- **TypeScript**: Regex-based extraction through the registered compatibility parser
- **Rust**: Regex-based extraction (no external deps)
- **Go**: Regex-based extraction (no external deps)

All parsers handle syntax errors gracefully with partial results.

## Adding New Languages

To add a new language parser:

1. Create `parsers/[language]/parser.py` with a `[Language]LanguageParser` class
2. Implement `LanguagePlugin` abstract methods
3. Return language-specific `ParseResult` dataclass
4. Update `LanguageDetector.EXTENSION_MAP` and `PARSER_CLASSES`
5. Create `parsers/[language]/__init__.py` with exports
6. Document in `parsers/[language]/README.md`

## Dependencies

- Each parser is independent; no cross-language dependencies
- Only Python standard library (ast, re modules) for core parsers
- Optional: tree-sitter for more advanced parsing
