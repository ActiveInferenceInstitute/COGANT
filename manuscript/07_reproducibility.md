# Reproducibility

Reproducible computational research requires version-pinned tools, fixed inputs, and documented outputs [@peng2011reproducible]. COGANT contributes the **graph-generation** slice of that story: identical source trees and identical pipeline configuration should yield identical exported bundles modulo declared nondeterminism (for example optional neural embeddings if enabled).

## Version pinning

Pin:

- The **COGANT** version (`pyproject.toml` / package `__version__`) and Git commit when installing from source.
- The **Python** minor version.
- **Optional** Rust toolchain commit when building native extensions from `../cogant/rust/`.

## Artifact layout

Pipeline output typically includes JSON for intermediate IRs, **Generalized Notation Notation (GNN)** bundles (canonical `model.gnn.md` plus companion JSON and interop artifacts), validation reports, and optional HTML sites. Paths under the chosen `output_dir` should be treated as disposable but **checksumable**: store hashes alongside published datasets derived from COGANT exports when releasing research artifacts.

## Determinism

Parsing and graph construction aim for deterministic ordering on a fixed filesystem snapshot. Features that pull in external models (for example optional name or documentation embeddings consumed by the Generalized Notation Notation exporter) introduce variability unless models and seeds are fixed; the Generalized Notation Notation export document (`../cogant/docs/export/README.md`) calls out embedding dimensions and optional behavior.

## Relation to the template repository

While this project remains outside [`../../../projects/`](../../../projects/), it is **not** executed by the root `./run.sh` discovery layer. After promotion to [`../../../projects/cogant/`](../../../projects/cogant/) with `src/`, `tests/`, and `pyproject.toml` per template rules, the standard manuscript validation and PDF stages apply; until then, validate Markdown from the template repository root, e.g. `uv run python -m infrastructure.validation.cli markdown ./projects_in_progress/cogant/manuscript/`.

## Validation gates

The pipeline enforces quality through three complementary validation checkers, each targeting a different failure mode:

**IntegrityChecker.** Verifies structural soundness of the program graph: all edge endpoints reference existing nodes, no unintended duplicate nodes exist, orphaned nodes (zero in-degree and zero out-degree) are flagged, and self-loops are reported unless explicitly allowed by configuration. The checker also ensures that confidence scores fall within $[0, 1]$ and that provenance records are non-empty for every node and edge. A graph that fails integrity checks receives a FAIL validation status; downstream export is blocked.

**SchemaValidator.** Validates each IR artifact against its schema contracts (versioned alongside the COGANT package). Schema violations -- such as missing required fields, incorrect types, or unknown enum values in `NodeKind` or `SemanticRole` -- are classified by severity in the validation report.

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

Exported graphs can contain identifiers and comments from source code. Redistribution of derived graphs must respect the licenses of input repositories and organizational data policies. For a **checklist** (version pins, lockfiles, input hashes, manifest verification) when publishing or citing a run, see [`06_05_reproducible_recording.md`](06_05_reproducible_recording.md).
