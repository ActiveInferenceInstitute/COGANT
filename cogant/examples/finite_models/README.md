# Explicit finite models

These authored models provide complete state configurations, action labels,
observation outcomes, and probability kernels. They enter the explicit finite
model compiler rather than the source-code inference pipeline.

From the inner package root:

```bash
uv run cogant finite compile examples/finite_models/toggle.json -o output/finite/toggle.json
uv run cogant finite verify examples/finite_models/toggle.json output/finite/toggle.json
uv run cogant finite compile examples/finite_models/counter.json -o output/finite/counter.json
uv run cogant finite verify examples/finite_models/counter.json output/finite/counter.json
```

Output files must be new paths. Reuse an existing compiled artifact with
`finite verify`, or choose another output path for a fresh compilation.

- `toggle.json`: hold/toggle actions and a fully observed binary state.
- `counter.json`: increment/reset actions, saturation at the top state, and
  partial observation: `zero` and `one` both emit `low`.

The Python API, stochastic kernels, matrix orientation, resource contract, and
runtime handoff are documented in [Finite models](../../docs/api/finite_models.md).
