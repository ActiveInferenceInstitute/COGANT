# JavaScript Parser

JavaScript source code parser (uses shared TypeScript parser).

## Contents

- `__init__.py` — Exports JavaScriptLanguageParser
- Parser implementation is shared with TypeScript in `parsers/typescript/parser.py`

## Usage

```python
from parsers.javascript import JavaScriptLanguageParser
# or
from parsers.typescript import TypeScriptLanguageParser

# Both parse JavaScript
parser = JavaScriptLanguageParser()
result = parser.parse_file(Path("script.js"))
```

## Supported Languages

- JavaScript (.js, .jsx)
- TypeScript (.ts, .tsx)

Both are handled by the same `TypeScriptLanguageParser` class since the parsers are very similar.

## Supported Features

- Functions and arrow functions
- Classes and constructors
- Function declarations
- Module imports/exports (named, default, namespace)
- Type annotations (JSDoc or TypeScript-style)
- Variable declarations

## Implementation

See `parsers/typescript/README.md` for full documentation.

The JavaScript and TypeScript syntax is largely compatible for static analysis purposes, so a single parser handles both languages efficiently.

## Dependencies

- Python standard library (re module)
- cogant.plugins.base (LanguagePlugin)
