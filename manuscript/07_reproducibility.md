# Reproducibility {#sec:07-reproducibility}

Reproducible computational research requires version-pinned tools, fixed inputs, documented workflows, and archived outputs [@peng2011reproducible; @sandve2013ten]. ACM's artifact-review terminology is useful here because it distinguishes available artifacts, evaluated artifacts, reproduced results, and independently replicated results [@acmArtifactBadging2020]. COGANT contributes the **graph-generation** slice of that story: identical source trees and identical pipeline configuration should yield identical exported bundles modulo declared nondeterminism (for example optional neural embeddings if enabled). That is a repeatability and artifact-audit claim, not a claim that an independent team has reproduced or replicated every manuscript result. The project also borrows the FAIR emphasis on machine-actionable metadata [@wilkinson2016fair]: generated bundles, figure manifests, rule traces, and claim-ledger rows are designed to be inspected by scripts as well as by human reviewers.

## Publication checklist

When citing or redistributing a COGANT run, archive together:

1. **COGANT version and Git SHA** — `cogant doctor`; `__version__` matches `pyproject.toml`.
2. **Python interpreter** — `python --version` and platform (`uname -a` or equivalent).
3. **Dependency lock** — `uv.lock` from the package root with the same `uv sync --extra …` extras as the run.
4. **Input snapshot** — Git commit of each analyzed repository; for fixtures under `examples/`, record the COGANT monorepo SHA.
5. **Pipeline configuration** — `cogant.yaml` or `PipelineConfig` serialization (secrets redacted).
6. **Stages executed** — full ten-stage DAG vs `skip_stages`, `--no-dynamic`, `--skip-validate`, etc.
7. **Downstream seeds** — only if a learned model consumes exports (COGANT’s default pipeline is deterministic).
8. **Output hashes** — SHA-256 of `gnn_package/` and `bundle.json` for verification.

Worked commands, manifest semantics, and a full `flask_app` re-run recipe: [`06_05_reproducible_recording.md`](06_05_reproducible_recording.md).

## Version pinning

Pin:

- The **COGANT** version (`pyproject.toml` / package `__version__`) and Git commit when installing from source.
- The **Python** minor version.
- **Optional** Rust toolchain commit when building native extensions from `../cogant/rust/`.

## Artifact layout

Pipeline output typically includes JSON for intermediate IRs, **Generalized Notation Notation (GNN)** bundles (canonical `model.gnn.md` plus companion JSON and interop artifacts), validation reports, and optional HTML sites. Paths under the chosen `output_dir` should be treated as disposable but **checksumable**: store hashes alongside published datasets derived from COGANT exports when releasing research artifacts.

The artifact layout is intentionally provenance-shaped. Source files, parser activities, rule applications, conflict-resolution events, generated bundles, figures, and rendered manuscript outputs are separate entities connected by explicit generation steps, following the same broad entity/activity/derivation model standardized by PROV-DM [@moreau2013prov]. At the assertion level, COGANT's rule-evidence rows also echo why/where provenance [@buneman2001whyWhere] and provenance-semiring work, which treats derivation annotations as values that flow through relational and Datalog-style fixed points instead of collapsing them into booleans [@green2007provenance]. COGANT's sidecars are not full PROV-O/JSON-LD documents and do not implement semiring algebra, but the design choice is the same: make trust, reuse, and debugging depend on inspectable derivations rather than on prose assurances. If a downstream archive needs web-native provenance exchange, the current sidecars should be treated as a domain schema that can be mapped into PROV/JSON-LD, not as already conforming linked data [@jsonLd11].

The same scoping applies to artifact packaging. Research Objects were proposed because linked data alone is not enough to support scientific reuse, validation, and publication: reproducible work needs aggregations that bind data, methods, provenance, attribution, and context [@bechhofer2013linkedDataNotEnough]. A COGANT run directory is shaped in that direction -- code snapshot, configuration, intermediate IRs, bundle exports, validation reports, figure sidecars, hashes, and manuscript-variable snapshots -- but it is not advertised as a Research Object implementation. It is a checksumable, provenance-bearing package that a downstream archive could wrap in a formal Research Object or PROV/JSON-LD exchange layer.

## Figure evidence manifests

Manuscript figures follow the same traceability rule as tables. `tools/manuscript_figures.py` registers each promoted figure with its `source_artifact`, renderer, method note, reading guide, limitation note, alt text, SHA-256 hash, byte size, dimensions, data digest, and lightweight visual-QA fields such as nonblank status and sampled color diversity. The copied assets land in `output/figures/` beside `manifest.json` and per-figure `.figure.json` sidecars; strict mode fails when any registered figure is missing or lacks required evidence metadata. Renderer-produced sidecars such as `program_graph.figure.json` are still preserved when available, so displayed node/edge counts and renderer-specific layout choices remain inspectable. This is a visual-analytics provenance convention as much as a file-management convention: provenance work distinguishes data, workflow, interaction, and insight records, and COGANT's sidecars intentionally cover the data and workflow portions while leaving human analytic interactions to future review tooling [@ragan2016provenance].

This means that visualizations in @sec:01-introduction, @sec:02-04-gnn-export-and-error-handling, and @sec:04-examples-and-failure-modes are part of the reproducible evidence chain rather than illustrative redraws. A reader can verify that the forward graph, state-space factor view, matrix panels, GNN Markdown render, Markov-blanket partition, batch timeline, roundtrip diff, rule trace, evidence-coverage panel, and inference trace were copied from package outputs under `../cogant/output/`, not reconstructed by hand for the manuscript. The manifest does not show that a visual encoding is the only possible one; it records the narrower and more important claim that the shown pixels correspond to declared package artifacts with recorded provenance.

| Figure group | Source artifact | Renderer family | Evidence boundary |
|---|---|---|---|
| End-to-end calculator chain | `../cogant/output/calculator/` JSON, GNN, matrix, and roundtrip artifacts | `cogant.viz.png_export` and `cogant.viz.inspection_dashboard` | Demonstrates inspectable conversion surfaces for one real run; does not prove semantic recall. |
| Fixture evaluation figures | `../cogant/evaluation/figures/metrics.json` | `../cogant/evaluation/figures/generate_figures.py` | Summarizes public API fixture metrics; timing bars are single-run provenance, not benchmark distributions. |
| Ablation figure | `../cogant/evaluation/METRICS.yaml` | `cogant.viz.ablation_view.render_ablation_png` | Shows measured rule-family and fixpoint deltas; does not decompose every mapping kind in the main panel. |
| Batch timeline | `../cogant/output/run_manifest.json` | `tools.manuscript_figures.render_publication_batch_timeline` | Shows recorded stage ordering and verification gates; wall-clock durations are audit metadata. |
| Batch evidence summary | `../cogant/output/dashboard/metrics_per_target.json` | `tools.manuscript_figures.render_publication_batch_evidence_summary` | Summarizes emitted graph, mapping, role, validation, roundtrip, and visual evidence; does not prove semantic correctness. |

: Manuscript figure provenance groups and evidence boundaries. {#tbl:figure-provenance-groups}

## Determinism

Parsing and graph construction aim for deterministic ordering on a fixed filesystem snapshot. Features that pull in external models (for example optional name or documentation embeddings consumed by the Generalized Notation Notation exporter) introduce variability unless models and seeds are fixed; the Generalized Notation Notation export document (`../cogant/docs/export/README.md`) calls out embedding dimensions and optional behavior.

## Canonical metrics regeneration

Every numeric token in this manuscript (`{{COVERAGE_PCT}}`, `{{TEST_COUNT}}`, role-preservation counts, suite runtime, ...) resolves from one source of record, `cogant/evaluation/METRICS.yaml`, via the chain `regenerate_metrics.py` → `inject_manuscript_vars.py` → render. The contract is intentionally one-directional: prose never hard-codes a metric, and `tools/check_metrics_fresh.py` is the drift detector that fails CI when `METRICS.yaml` disagrees with the committed `coverage.json`. For release provenance, run it with `--fail-on-dirty`; the default mode compares committed `HEAD` and warns if uncommitted code, docs, or generated artifacts mean `generator_git_sha` is not a sufficient description of the tree. Three failure modes were observed and hardened so the contract degrades safely rather than silently:

- **Stale-artifact drift.** A checked-in `coverage.json` whose statement denominator predates code growth makes every derived figure stale even though `check_metrics_fresh` reports "in sync" (it compares against that same stale artifact). The mitigation is procedural and stated here for auditors: regenerate from a *fresh* full `uv run pytest tests/ --cov=py/cogant` run, not from the committed artifact, before trusting the headline coverage number.
- **Environment-fragile regeneration.** `regenerate_metrics.py` re-runs the suite in a fast no-coverage mode to recover pass/fail counts; in some environments that sub-invocation mis-parses and returns zero passing. A guard treats `passing == 0` on a multi-thousand-test suite as a parse failure and **preserves the prior canonical counts with a loud warning** rather than overwriting `METRICS.yaml` with corrupted zeros, so a single bad regeneration cannot silently destroy the record.
- **Dirty-worktree provenance.** A clean `generator_git_sha` comparison only shows that `METRICS.yaml` was generated from the committed `HEAD`; it does not show that the current manuscript/package tree has no uncommitted edits. The freshness gate now reports dirty paths by default and can fail via `uv run python tools/check_metrics_fresh.py --fail-on-dirty` for release builds.

These checks are why the round-trip and coverage numbers in this paper are reproducible by re-execution rather than by trust (cf. @sec:08-05-threats-to-validity, which scopes what those reproducible numbers do and do not establish).

## Relation to the template repository

In this standalone checkout, COGANT is checked with the local project commands (`tools/audit_manuscript_crossrefs.py`, `tools/audit_manuscript_numbers.py`, `cogant/docs/verify_manuscript_links.py`, and the package test suite). When the same tree is vendored into the parent template under [`../../../projects/cogant/`](../../../projects/), the root `./run.sh` discovery layer can execute it with `src/`, `tests/`, and `pyproject.toml` per template rules, and Markdown can also be checked from the template repository root with `uv run python -m infrastructure.validation.cli markdown ./projects/cogant/manuscript/`.

## Validation gates

The pipeline enforces quality through three complementary validation checkers, each targeting a different failure mode:

**IntegrityChecker.** Checks structural soundness of the program graph: all edge endpoints reference existing nodes, no unintended duplicate nodes exist, orphaned nodes (zero in-degree and zero out-degree) are flagged, and self-loops are reported unless explicitly allowed by configuration. The checker also checks that confidence scores fall within $[0, 1]$ and that provenance records are non-empty for every node and edge. A graph that fails integrity checks receives a FAIL validation status; downstream export is blocked.

**SchemaValidator.** Validates each IR artifact against its schema contracts (versioned alongside the COGANT package). Schema violations -- such as missing required fields, incorrect types, or unknown enum values in `NodeKind` or `SemanticRole` -- are classified by severity in the validation report. The current validators are package-native checks over COGANT dataclasses and JSON sidecars. They are compatible in spirit with JSON Schema and graph-shape validation, but this manuscript does not claim that every exported artifact ships with a normative JSON Schema or SHACL document [@jsonSchema2020; @w3cShacl2017].

**ProvenanceChecker.** Audits the provenance chain: every assertion in the semantic mapping must trace back to at least one evidence source (SourceCode, TypeSystem, ControlFlow, Heuristic, or External). The checker flags mappings whose provenance is empty or whose confidence score is inconsistent with the declared evidence tier -- for example, a STATIC_PLUS_RUNTIME tier with no runtime trace evidence. These flags appear as warnings rather than errors, since partial provenance is expected for heuristic rules.

Together, these gates ensure that exported bundles meet a minimum quality bar before reaching downstream models. Thresholds and policy defaults are configurable and documented in `../cogant/docs/validation/README.md`.

The concrete shape of a validation report is the `ValidationReport` dataclass defined in `../cogant/py/cogant/validate/report.py`, which bundles the timestamp, the model identifier, a boolean `is_valid` flag, numerical `coverage_score` and `confidence_score` fields in $[0, 1]$, a free-form human-readable `summary` string, and a list of `ValidationIssue` records. Each `ValidationIssue` (defined in `../cogant/py/cogant/validate/schema_check.py`) carries a stable `id`, a `severity` of `error`, `warning`, or `info`, a `category` of `schema`, `integrity`, `provenance`, or `coverage`, the set of `affected_ids`, and an optional `recommendation` string. On a clean calculator run, for example, the report has the following shape:

```json
{
  "id": "report_calculator_20260410T081234Z",
  "schema_name": "calculator",
  "validated_at": "2026-04-10T08:12:34Z",
  "model_id": "model_calculator",
  "is_valid": true,
  "coverage_score": 1.0,
  "confidence_score": 0.94,
  "summary": "Validation PASS — 0 errors, 0 warnings, 12/12 nodes covered",
  "issues": [],
  "details": {"gnn_validator_score": 100.0, "elapsed_ms": 73}
}
```

When one of the gates fires, the same `issues` list accumulates structured records of the form:

```json
{
  "id": "prov_001",
  "severity": "warning",
  "category": "provenance",
  "message": "Mapping 'map_42' declared STATIC_PLUS_RUNTIME but has no dynamic_trace evidence source",
  "affected_ids": ["map_42"],
  "recommendation": "Re-run with --coverage/--trace inputs, or downgrade the declared tier in the rule"
}
```

Errors block export (`is_valid` flips to `false` and the pipeline refuses to write the `gnn_package/` directory); warnings are recorded in the bundle but do not block. Downstream consumers therefore only need to inspect the top-level `is_valid` flag plus any `severity == "error"` entries to decide whether a bundle is safe to ingest.

## Current runner behavior vs template checkpointing

The current `cogant.api.pipeline.PipelineRunner` executes stages in order and records stage outputs in a `Bundle`, but it does **not** currently expose built-in checkpoint/resume flags or a dedicated `manifest.json` writer in that module. Reproducibility is therefore captured today by persisting `bundle.json` (`Bundle.save_json`), pinning config and versions, and retaining exported artifacts.

If COGANT is promoted into the template project workflow under `projects/`, repository-level checkpoint utilities from `infrastructure/core/runtime/checkpoint.py` can be used by the outer orchestration layer. That template capability should be treated as infrastructure-level behavior, distinct from the current COGANT package runner.

## Data ethics and licensing

Exported graphs can contain identifiers and comments from source code. Redistribution of derived graphs must respect the licenses of input repositories and organizational data policies. The **Publication checklist** above is the short form; [`06_05_reproducible_recording.md`](06_05_reproducible_recording.md) expands each item with paths, regeneration scripts, and a worked `flask_app` example.
