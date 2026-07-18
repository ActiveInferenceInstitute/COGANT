# Language parser implementations

This package contains the installable language-specific parser plugins used by
the COGANT parser registry. The registry is the public selection boundary;
callers should not import a language implementation by filesystem path.

Python uses the standard-library AST parser. JavaScript and TypeScript expose
the current structural compatibility parser and optional tree-sitter paths.
Rust and Go are available as experimental structural parsers until their
fixture and graph-normalization coverage is expanded.

Static capability metadata is available from
`cogant.parsers.parser_capabilities()`. Runtime mode, optional grammar
availability, and explicit degraded reasons are available from
`cogant.parsers.parser_capability_report()`; unavailable selections raise the
registry's typed exception rather than silently returning an empty parser.
