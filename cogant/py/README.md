# Python Source Root

This directory is the setuptools package root configured by `cogant/pyproject.toml`:
`import cogant` resolves to [`cogant/`](cogant/). Keep installable library code under
that package and keep repository orchestration in the package root, `scripts/`, or
staging-root tools.

## Layout

- [`cogant/`](cogant/) - canonical Python package and public API surface.
- `cogant.egg-info/` - generated packaging metadata when present; do not edit.

## Commands

Run commands from the inner package root, one level up from this directory:

```bash
cd ..
uv run pytest tests/ -q
uv run mypy py/cogant/
uv run ruff check py/cogant/
```
