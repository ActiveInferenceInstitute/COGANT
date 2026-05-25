# Agents - examples/control_positive/event_pipeline

## Scope

Event Pipeline Fixture. This fixture exercises event ingestion, transformation, and publishing flow for fast local pipeline and
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
uv run cogant translate examples/control_positive/event_pipeline --layout-output --output output/event_pipeline
```
