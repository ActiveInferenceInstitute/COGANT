# Agents - examples/control_positive/flask_mini

## Scope

Flask Mini Fixture. This fixture exercises route handlers, request observation, and response actions for fast local pipeline and
roundtrip evidence.

## Files

- `app.py` - primary fixture source.

## Rules

- Keep the fixture dependency-free unless the parent README explicitly documents the dependency.
- Preserve real executable Python; do not replace behavior with comments just to satisfy a rule.
- If the architecture shape changes, update this file and the fixture README in the same pass.

## Verification

From the inner package root:

```bash
uv run cogant translate examples/control_positive/flask_mini --layout-output --output output/flask_mini
```
