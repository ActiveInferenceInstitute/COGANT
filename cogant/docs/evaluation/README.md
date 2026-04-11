# Evaluation and R&D

> Dated reports, calibration notes, benchmarks, and empirical analyses for COGANT. These documents are the historical and ongoing record of how COGANT's claims (isomorphism, roundtrip fidelity, real-world coverage) have been measured. Machine-readable artifacts live in the **`evaluation/`** directory at the repository root (sibling of **`docs/`**, not part of the MkDocs tree).

## Contents

### Release readiness and milestones

| Page | Description | Level |
|------|-------------|-------|
| [V1.0 Readiness](V1.0_READINESS.md) | Gate-by-gate readiness assessment for v1.0 | Reference |
| [Final Report](FINAL_REPORT.md) | Consolidated final report on the v1.0 evaluation effort | Reference |
| [Release Notes v0.2.0](RELEASE_NOTES_v0.2.0.md) | Historical release notes | Reference |
| [Release Notes v0.5.0](RELEASE_NOTES_v0.5.0.md) | Historical release notes | Reference |
| [Scoping Report](SCOPING_REPORT.md) | Roadmap and milestone tracking | Reference |
| [R&D Log](R&D_LOG.md) | Dated gate entries: changes, tests, coverage, decisions | Reference |

### Theory and mapping

| Page | Description | Level |
|------|-------------|-------|
| [Active Inference Mapping](ACTIVE_INFERENCE_MAPPING.md) | Code patterns to Active Inference roles | Intermediate |
| [Isomorphism Theorem](ISOMORPHISM_THEOREM.md) | Roundtrip / isomorphism discussion and proof sketch | Advanced |
| [Calibration](CALIBRATION.md) | Confidence and rule calibration backlog | Advanced |
| [Constraint Fix](CONSTRAINT_FIX.md) | The CONSTRAINT detection fix and its evaluation impact | Advanced |
| [First Inference](FIRST_INFERENCE.md) | First-inference experiment notes | Intermediate |

### Empirical studies

| Page | Description | Level |
|------|-------------|-------|
| [Roundtrip Eval](ROUNDTRIP_EVAL.md) | Forward + reverse roundtrip evaluation | Intermediate |
| [Roundtrip Validation](ROUNDTRIP_VALIDATION.md) | Validation of the roundtrip claim | Intermediate |
| [Roundtrip Improvement](ROUNDTRIP_IMPROVEMENT.md) | Iterative improvements to roundtrip fidelity | Intermediate |
| [Cross-Language Roundtrip](CROSS_LANG_ROUNDTRIP.md) | Roundtrip across language pairs | Advanced |
| [Real-World Eval](REAL_WORLD_EVAL.md) | External repository runs | Advanced |
| [Empirical Claim](EMPIRICAL_CLAIM.md) | Stated empirical claims and their evidence | Reference |
| [Benchmark vs Prior](BENCHMARK_VS_PRIOR.md) | Comparison against prior baselines | Advanced |
| [Incremental Benchmark](INCREMENTAL_BENCHMARK.md) | Incremental rescanning benchmarks | Advanced |
| [Scaling Analysis](SCALING_ANALYSIS.md) | Scaling characteristics on larger inputs | Advanced |
| [GNN Validation Report](GNN_VALIDATION_REPORT.md) | Validation results for generated GNN packages | Intermediate |
| [Mutation Report](MUTATION_REPORT.md) | Mutation-testing results | Advanced |

### Bibliography

| Page | Description | Level |
|------|-------------|-------|
| [Literature](LITERATURE.md) | Bibliography-style references for COGANT | Reference |
| [Related Work](RELATED_WORK.md) | Comparison with adjacent tools and research | Reference |

## Recommended Reading Order

1. [V1.0 Readiness](V1.0_READINESS.md) — current top-level status.
2. [Final Report](FINAL_REPORT.md) — the consolidated narrative.
3. [Active Inference Mapping](ACTIVE_INFERENCE_MAPPING.md) — the conceptual contract being evaluated.
4. [Roundtrip Eval](ROUNDTRIP_EVAL.md) and [Roundtrip Validation](ROUNDTRIP_VALIDATION.md) — the central empirical claim.
5. [Real-World Eval](REAL_WORLD_EVAL.md) and [Cross-Language Roundtrip](CROSS_LANG_ROUNDTRIP.md) — generalization beyond the lab.
6. [Calibration](CALIBRATION.md) and [Constraint Fix](CONSTRAINT_FIX.md) — known caveats and recent fixes.
7. [Literature](LITERATURE.md) and [Related Work](RELATED_WORK.md) — situate COGANT in the wider ecosystem.

See also the [documentation hub](../index.md) for tutorials, theory, and API reference.

Agent notes: [AGENTS.md](AGENTS.md)
