# Agents - examples/control_positive/plugin_architecture

## Scope

Plugin Architecture Fixture. This fixture exercises plugin registration, lookup, and dispatch behavior for fast local pipeline and
roundtrip evidence.

## Files

- `core.py` - primary fixture source.

## Rules

- Keep the fixture dependency-free unless the parent README explicitly documents the dependency.
- Preserve real executable Python; do not replace behavior with comments just to satisfy a rule.
- If the architecture shape changes, update this file and the fixture README in the same pass.

## Verification

From the inner package root:

```bash
uv run cogant translate examples/control_positive/plugin_architecture --layout-output --output output/plugin_architecture
```
