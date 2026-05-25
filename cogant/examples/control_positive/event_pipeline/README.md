# Event Pipeline Fixture

Event ingestion, transformation, and dispatch flow. It exercises data-flow and orchestration mappings without external services.

## Files

- `pipeline.py` - fixture source.

## Smoke Command

From the inner package root:

```bash
uv run cogant translate examples/control_positive/event_pipeline --layout-output --output output/event_pipeline
```
