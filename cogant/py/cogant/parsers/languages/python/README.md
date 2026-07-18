# Python parser

`PythonLanguageParser` is the primary Python front end. It uses Python's AST
and emits the shared parsed-file and parsed-symbol structures consumed by
static analysis and graph normalization.

Changes to symbol identity, imports, methods, decorators, async functions, or
test detection require corresponding Python fixtures and graph assertions.
