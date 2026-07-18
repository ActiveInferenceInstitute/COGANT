# JavaScript parser

`JavaScriptLanguageParser` is the grammar-backed JavaScript implementation.
It is selected when its optional tree-sitter grammar is available; callers
must receive an explicit unavailable or degraded result when that dependency
is absent.
