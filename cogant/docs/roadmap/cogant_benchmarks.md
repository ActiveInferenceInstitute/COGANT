## COGANT Benchmarks

COGANT translates software repositories into **Generalized Notation
Notation** (GNN), the Active Inference Institute's structured state-space and
process-model notation. This page defines the benchmark contract and where
current numbers come from; it is not itself the source of authoritative
measurements.

### Evidence sources

Current benchmark-style claims must be derived from generated artifacts:

- `cogant/evaluation/METRICS.yaml` for manuscript-bound numeric claims.
- `cogant/output/run_manifest.json` for batch targets, commands, step status,
  and run timing metadata.
- `cogant/output/dashboard/metrics_per_target.json` for cross-target graph,
  mapping, validation, roundtrip, and visual-artifact summaries.
- `output/figures/manifest.json` plus per-figure `.figure.json` sidecars for
  publication visual evidence.

When those files disagree with prose, update or regenerate the artifacts first.
Do not hand-edit roadmap prose into a stronger claim than the artifacts support.

### Scope

COGANT benchmark reviews cover five dimensions:

1. **Pipeline latency**: recorded wall-clock time for each configured runner
   command and stage, including the dynamic-analysis stage when enabled.
2. **Throughput**: files, nodes, edges, mappings, and emitted artifacts per
   target.
3. **Validation**: GNN syntax/section compliance, matrix provenance, stochastic
   checks, state-space alignment, and advisory upstream compatibility results.
4. **Roundtrip quality**: role preservation, matrix score, structural score,
   shape parity, generated-code status, and explicit warnings.
5. **Visual evidence completeness**: inspection dashboard, native graphical
   abstract, Figure 10 timeline, detail panels, sidecars, and strict
   publication QA status.

Memory consumption and output-size regressions remain tracked as secondary
targets, but publication claims should stay attached to generated artifacts.

### Reference targets

The fast local reference set begins with the `examples/control_positive/`
fixtures and the pinned targets configured by `run_all.py`. The active target
set is intentionally not duplicated here because it changes as fixtures and
remote examples are promoted. Inspect `run_manifest.json`, `tasks.yaml`, and
`METRICS.yaml` for the exact current set.

For publication figures, the calculator target is used as the readable
single-target timeline and graphical-abstract source. Batch-wide context is
stored in sidecar metadata rather than compressed into an unreadable image.

### Stage-level policy

Stage tables should be generated from run manifests or benchmark tooling. Static
roadmap tables may list measurement categories and thresholds, but should not
publish drifted observed values.

| Category | Target policy | Evidence artifact |
|---|---|---|
| Ingest/static/normalize/graph/dynamic | Cheap local development feedback | `run_manifest.json` command timings |
| Translate/state-space/process/export | Deterministic artifact generation | GNN package JSON, sidecars, and validation report |
| Validate/roundtrip | Explicit pass/fail and advisory failure reporting | validation JSON and `roundtrip/metrics.json` |
| Visualization/inspection | Publication-grade nonblank outputs with sidecars | figure manifest and visual QA audit |

Large-repo targets remain planning goals until backed by reproducible benchmark
runs:

| Repo size | Target intent | Notes |
|---|---|---|
| Medium repositories | Complete local run without manual intervention | Use pinned refs and cached dependencies |
| Large repositories | Streaming export and bounded-memory processing | Requires exporter and graph-builder hardening |
| Polyglot monorepos | Per-language workers with explicit degraded-output status | Requires language-front-end maturity |

### Running benchmark checks

Fast package benchmark and regression checks are run from the inner package
root:

```bash
uv run pytest benchmarks/ -q
```

Full benchmark-style publication evidence is refreshed through the project
pipeline:

```bash
uv run python run_all.py --fail-fast
uv run python scripts/z_generate_manuscript_variables.py
uv run python tools/manuscript_figures.py --strict
```

Roundtrip and robustness claims must also pass the corresponding manuscript
audits before they are cited in prose.

### Measurement methodology

- Use wall-clock time and preserve the run manifest.
- Record config, git refs, generated artifact paths, and sidecar digests.
- Separate timing metadata from benchmark claims; a single recorded run is not a
  statistical benchmark.
- Treat optional upstream or local-service failures as explicit advisory rows
  unless a strict audit promotes them to fatal.
- Keep generated numeric claims in `METRICS.yaml` and manuscript variables.

### Regression policy

A change needs review when it:

- Removes or degrades a required publication figure, sidecar, or visual-QA
  field.
- Converts a strict validation failure into a silent success.
- Drops matrix provenance, state-space alignment, or roundtrip diagnostics.
- Reintroduces hard-coded benchmark counts into roadmap or manuscript prose.
- Expands feature scope without a reproducible artifact path and verifier.

### Optimization priorities

1. Profile before changing performance-sensitive code.
2. Keep evidence-critical renderers and validators small enough to review.
3. Stream large exports before adding large-repo claims.
4. Prefer generated manifests over prose snapshots for current numbers.
5. Add negative controls whenever a new benchmark claim becomes publication
   visible.

### Related documents

- [benchmarks/README.md](https://github.com/ActiveInferenceInstitute/COGANT/blob/main/cogant/benchmarks/README.md)
  - low-level benchmark layout and running guide
- [Architecture](../architecture/README.md) - layered architecture and stage
  boundaries
- [Evaluation](../evaluation/README.md) - generated evidence and readiness
  reports
- [Changelog](changelog.md#changelog) - release notes
- [AGENTS.md](./AGENTS.md) - roadmap maintenance rules
