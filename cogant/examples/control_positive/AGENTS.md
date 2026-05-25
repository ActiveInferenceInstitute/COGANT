# Agents - examples/control_positive

## Scope

COGANT-owned positive-control repositories. Add fixtures here when the normal
fast test/evidence path needs a new software architecture shape without remote
GitHub dependencies.

## Rules

- Keep fixtures tiny, deterministic, and dependency-light.
- Prefer idiomatic source code over synthetic comments; the parser should see real constructs.
- Each fixture folder needs a `README.md` and `AGENTS.md` that states what behavior it exercises.
- Remote repositories belong in `run_all.json`, not in this directory.

## Verification

From the inner package root:

```bash
uv run pytest tests/integration/test_reverse_roundtrip_fixtures.py -q --no-cov
uv run cogant translate examples/control_positive/calculator --layout-output --output output/calculator
```
