# Agents - examples/control_positive/async_service

## Scope

Async Service Fixture. This fixture exercises asyncio queue observation, dispatch action, and graceful shutdown state for fast local pipeline and
roundtrip evidence.

## Files

- `service.py` - primary fixture source.

## Rules

- Keep the fixture dependency-free unless the parent README explicitly documents the dependency.
- Preserve real executable Python; do not replace behavior with comments just to satisfy a rule.
- If the architecture shape changes, update this file and the fixture README in the same pass.

## Verification

From the inner package root:

```bash
uv run cogant translate examples/control_positive/async_service --layout-output --output output/async_service
```
