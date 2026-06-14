# GNN v2 Audit Surface

This page records the verifier boundary for COGANT's current upstream
Generalized Notation Notation integration.

COGANT intentionally separates four claims:

1. **Version currentness.** The active environment resolves the pinned
   `generalized-notation-notation` v2.0.0 release bundle, whose engine reports
   GNN v2.0.0.
2. **Bridge usability.** COGANT imports upstream only through
   `cogant.gnn.upstream_bridge`, because raw `src.gnn` import remains sensitive
   to upstream's repository-style layout.
3. **COGANT-owned method health.** Package build, validator, type-check,
   matrix export, reverse, roundtrip, runner, CLI, and pipeline tests can pass
   against the pinned upstream bundle.
4. **Selected upstream all-step execution.** The optional upstream pipeline is
   a stricter compatibility surface. Product code treats selected upstream-step
   failures as advisory; audit mode promotes them to fatal so a report cannot
   quietly convert partial compatibility into a full execution claim.

## Audit Helper

Use the project-root helper after producing an audit directory:

```bash
uv run python tools/gnn_v2_audit_surface.py \
  --audit-dir /tmp/cogant_gnn_v2_audit \
  --output-dir /tmp/cogant_gnn_v2_audit/published_surface
```

The helper writes:

| Output | Purpose |
| --- | --- |
| `gnn_v2_audit_surface.json` | Machine-readable claim classification. |
| `gnn_v2_audit_surface.md` | Human-readable report for reviews and release notes. |
| `gnn_v2_audit_surface.svg` | Compact visualization of version, upstream-step, and supply-chain lanes. |

Run strict mode when an audit should fail on any selected upstream step failure:

```bash
uv run python tools/gnn_v2_audit_surface.py \
  --audit-dir /tmp/cogant_gnn_v2_audit \
  --strict-upstream
```

Strict supply-chain mode is separate:

```bash
uv run python tools/gnn_v2_audit_surface.py \
  --audit-dir /tmp/cogant_gnn_v2_audit \
  --strict-supply-chain
```

## Reading The SVG

The SVG has three lanes: version/bridge, selected upstream all-step gate, and
supply-chain scan. The upstream lane then shows one block per selected upstream
step. Green means success; red means a selected step failed. This is a visual
claim ledger, not a decorative figure: if the all-step lane is red, the docs
must not say that COGANT's package fully executes through every selected
upstream step.

## Current Boundary

The current bridge supports COGANT's validation, type-check, export,
visualization, roundtrip, and runner paths against the pinned v2.0.0 bundle.
The optional upstream executable render/execute path is stricter and remains a
separate compatibility target. Treat a 100/100 COGANT package score as a
structural-validation statement, not as proof that every upstream executable
framework backend can render and run the package.
