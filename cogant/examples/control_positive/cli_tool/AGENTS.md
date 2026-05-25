# Agents - examples/control_positive/cli_tool

## Scope

CLI Tool Fixture. This fixture exercises argparse commands, parsed parameters, and command-side effects for fast local pipeline and
roundtrip evidence.

## Files

- `cli_tool.py` - primary fixture source.

## Rules

- Keep the fixture dependency-free unless the parent README explicitly documents the dependency.
- Preserve real executable Python; do not replace behavior with comments just to satisfy a rule.
- If the architecture shape changes, update this file and the fixture README in the same pass.

## Verification

From the inner package root:

```bash
uv run cogant translate examples/control_positive/cli_tool --layout-output --output output/cli_tool
```
