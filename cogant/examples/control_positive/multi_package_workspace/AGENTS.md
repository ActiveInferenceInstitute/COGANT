# Agents - examples/control_positive/multi_package_workspace

## Scope

Multi-Package Workspace Fixture. This fixture exercises workspace package boundaries and cross-package imports for fast local pipeline and
roundtrip evidence.

## Files

- `packages/` - primary fixture source.

## Rules

- Keep the fixture dependency-free unless the parent README explicitly documents the dependency.
- Preserve real executable Python; do not replace behavior with comments just to satisfy a rule.
- If the architecture shape changes, update this file and the fixture README in the same pass.

## Verification

From the inner package root:

```bash
uv run cogant translate examples/control_positive/multi_package_workspace --layout-output --output output/multi_package_workspace
```
