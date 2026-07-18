# Language parser maintenance

- Keep each implementation behind the registry in `cogant.parsers.registry`.
- Preserve the `LanguagePlugin` contract and return source spans whenever the
  parser can determine them.
- Add or update a focused fixture when changing symbols, imports, calls,
  decorators, async constructs, generated-file handling, or test classification.
- Keep optional grammar dependencies explicit; a fallback parser must not be
  presented as equivalent to a grammar-backed parser.
- Run the parser unit tests, polyglot tests, and package lint/type checks from
  the inner `cogant/` package root before handoff.
