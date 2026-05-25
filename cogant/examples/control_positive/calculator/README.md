# Calculator Fixture

Arithmetic functions with config values, action-like operations, and assertion-style constraints. It is the default small end-to-end target for translate, visualization, and roundtrip smoke tests.

## Files

- `calculator.py` - fixture source.

## Smoke Command

From the inner package root:

```bash
uv run cogant translate examples/control_positive/calculator --layout-output --output output/calculator
```
