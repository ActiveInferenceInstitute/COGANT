# Agents — py/cogant/parsers

## Owner

Ingest Lead

## Responsibilities

Tree-sitter substrate: `TreeSitterParser` parses Python, JavaScript, TypeScript, TSX, Rust, and Go through one interface; grammars load lazily and missing languages degrade gracefully. Top-level `cogant/parsers/<lang>/` plugins remain the canonical `LanguagePlugin` implementations; this package is the shared low-level layer they may delegate to.

## Coordination

Feeds `static/` and language plugins; paired with `tree_sitter_base.py` (`ParsedFile`, `ParsedSymbol`, `get_tree_sitter_parser`).

## Files

- `tree_sitter_base.py` — `TreeSitterParser`, `ParsedFile`, `ParsedSymbol`, `get_tree_sitter_parser`.
- `__init__.py` — public exports.
