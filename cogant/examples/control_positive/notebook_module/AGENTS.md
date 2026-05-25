# Agents - examples/control_positive/notebook_module

## Scope

Notebook Module Fixture. This fixture exercises notebook-converted analysis functions and derived metrics for fast local pipeline and
roundtrip evidence.

## Files

- `analysis.py` - primary fixture source.

## Rules

- Keep the fixture dependency-free unless the parent README explicitly documents the dependency.
- Preserve real executable Python; do not replace behavior with comments just to satisfy a rule.
- If the architecture shape changes, update this file and the fixture README in the same pass.

## Verification

From the inner package root:

```bash
uv run cogant translate examples/control_positive/notebook_module --layout-output --output output/notebook_module
```
