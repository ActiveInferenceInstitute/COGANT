# Calibration

This page collects the confidence-calibration notes for COGANT. A dedicated `CALIBRATION.md` is tracked in the R&D backlog — until it lands, the canonical source is the confidence discussion in `_rnd/ACTIVE_INFERENCE_MAPPING.md` and the behavior in `py/cogant/translate/confidence.py`.

## What the score means

Confidence scores are **epistemic about the pipeline**, not about whether the analyzed code is "good". A low score almost always means one of:

- the receiver type of a call was inferred by import tracing rather than an explicit annotation;
- the matched rule is in a low-priority band (e.g. name-keyword fallback when no structural evidence is available);
- coverage or trace data was missing for the region where the node lives;
- the mapping survived conflict resolution as a runner-up when a higher-priority rule also fired.

## Confidence tiers

`determine_confidence_tier` partitions the scalar confidence into four tiers. The thresholds live in `py/cogant/translate/confidence.py`:

| Tier | Condition | Semantics |
| --- | --- | --- |
| **HUMAN_REVIEWED** | `c >= 0.9` and human review evidence present | manually curated |
| **STATIC_PLUS_RUNTIME** | `c >= 0.65` and both AST + trace evidence | best structural evidence |
| **STATIC_ONLY** | `c >= 0.5` and AST evidence only | source-structure claim |
| **RUNTIME_ONLY** | `c >= 0.4` and trace evidence only | runtime-only inference |

Anything below `0.4` is kept in the bundle (for traceability) but excluded from the state-space compilation by default.

## Calibration approach

Current version (v0.1.x) computes confidence as a product of a **rule base score**, a **provenance penalty**, and a **conflict discount**:

```text
confidence = base_score * provenance_factor * conflict_factor
```

- **base_score** is set per-rule at class-definition time, reflecting how strong a structural signal the rule relies on (structural rules like `MutatingSubsystemRule` start at 0.95; keyword-only rules start lower).
- **provenance_factor** penalizes heuristic import tracing (-0.08), unresolved types (-0.05 per unresolved argument), and partial parses (-0.10).
- **conflict_factor** halves any mapping that survives conflict resolution as a runner-up.

No learned parameters yet. The roadmap item is to fit `provenance_factor` and `conflict_factor` against a labeled corpus of (node, human-assigned role) pairs and publish a reliability diagram.

## Validation data

Per-fixture breakdown (2026-04-09):

| Fixture | Total mappings | Mean confidence | STATIC_PLUS_RUNTIME | STATIC_ONLY | RUNTIME_ONLY |
| --- | ---: | ---: | ---: | ---: | ---: |
| `calculator` | 6 | 0.91 | 0 | 6 | 0 |
| `event_pipeline` | 20 | 0.86 | 0 | 20 | 0 |
| `flask_mini` | 19 | 0.83 | 0 | 19 | 0 |
| `flask_app` | 51 | 0.82 | 0 | 51 | 0 |

`STATIC_PLUS_RUNTIME` counts are zero across the control-positive fixtures because no trace data is committed alongside the source; runs with `--coverage` and `--trace` can promote individual transitions into the highest tier.

## Open questions

1. Should the provenance penalty be additive or multiplicative? Current code is multiplicative but the review tests expect additive behavior in one edge case.
2. How should we score mappings emitted during a `max_iterations` warning — trust them, discount them, or drop them?
3. Can we publish a per-rule reliability diagram once a labeled corpus is available?
4. Should `HUMAN_REVIEWED` be a separate orthogonal flag rather than a tier, so human-reviewed low-confidence mappings can be distinguished from never-reviewed high-confidence ones?

See also the [Active Inference mapping (R&D)](active_inference_mapping.md) page for the surprising findings that informed the current calibration approach.
