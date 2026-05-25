# Agents - py/

## Scope

Setuptools source root for the installable COGANT package. The only authored
subtree here should be [`cogant/`](cogant/); all pipeline, CLI, server, and API
logic lives below that package.

## Rules

- Do not add runnable scripts or tests directly under `py/`.
- Keep imports package-relative to `cogant` and preserve the `package-dir = {"" = "py"}` contract in `../pyproject.toml`.
- Generated packaging metadata such as `cogant.egg-info/` is disposable.

## Verification

From the inner package root (`..`):

```bash
uv run pytest tests/ -q --no-cov
uv run mypy py/cogant/
uv run ruff check py/cogant/
```
