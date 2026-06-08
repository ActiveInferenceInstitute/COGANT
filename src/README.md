# COGANT Template Shell

The parent template discovers active projects by looking for top-level `src/`
and `tests/` directories. COGANT keeps its installable package nested under
`cogant/`, so this shell provides a tiny, tested compatibility surface for
explicit template rendering from `projects/working/cogant/`.

The implementation lives at `../cogant/py/cogant/`; package development commands
should still be run from the inner `../cogant/` package root.
