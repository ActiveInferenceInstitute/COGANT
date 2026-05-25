# Agents - examples/control_positive/data_pipeline

## Scope

Data Pipeline Fixture. This fixture exercises extract/transform/load functions and data-flow edges for fast local pipeline and
roundtrip evidence.

## Files

- `pipeline.py` - primary fixture source.

## Rules

- Keep the fixture dependency-free unless the parent README explicitly documents the dependency.
- Preserve real executable Python; do not replace behavior with comments just to satisfy a rule.
- If the architecture shape changes, update this file and the fixture README in the same pass.

## Verification

From the inner package root:

```bash
uv run cogant translate examples/control_positive/data_pipeline --layout-output --output output/data_pipeline
```
