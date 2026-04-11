# `tests/` (template compatibility)

Executable tests for COGANT are under the **package tree**: [`../cogant/tests/`](../cogant/tests/) (pytest, coverage on `py/cogant/`).

This directory exists so that a future move to `projects/cogant/` satisfies the template’s expectation of a top-level `tests/` entry. Keep [`../cogant/tests/`](../cogant/tests/) as the authoritative suite; optionally symlink or mirror here if CI requires `projects/cogant/tests/`.

Run from [`../cogant/`](../cogant/):

```bash
uv run pytest tests/ -q
```
