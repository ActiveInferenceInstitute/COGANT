# Thin Orchestrated Examples

This folder holds **30 minimal, runnable scripts** that exercise COGANT from four angles:

1. **Stage-isolation scripts (01-12)** — each drives *one* pipeline stage and nothing else, so you can see exactly what `ingest`, `static`, `normalize`, `graph`, `translate`, `statespace`, `process`, `export`, `validate`, or `simulate` produces on its own.
2. **Higher-order scripts (13-20)** — each stitches multiple stages together to demonstrate a real workflow: end-to-end round-trips, cross-fixture comparison, confidence stratification, human-review layering, GNN-section walks, visualization dumps, drift analysis, and the high-level `Session` API.
3. **Cross-cutting analysis (21-22)** — Markov blanket extraction, the Active Inference partition that underpins the GNN `markov_blanket` section; GNN self-analysis.
4. **Specialized demonstrations (23-30)** — Wave-21 translation rules, Chrome DevTools trace ingestion, incremental analysis and benchmarking, multi-episode Active Inference runtime with learning, custom TranslationRule subclass, all-format export comparison, programmatic bundle validation, and graph diff via DriftAnalyzer API.

> COGANT translates source code into the Active Inference Institute's **Generalized Notation Notation** (GNN) — a structured notation for state-space and process models, *not* graph neural networks.

## Pipeline order

```
ingest → static → normalize → graph → translate → statespace → process → export → validate → simulate
```

All scripts share `_common.py`, which provides `banner`, `configure_logging`, `parse_args`, and the `build_rich_graph` helper that emits a typed `ProgramGraph` with full edges (CONTAINS / IMPORTS / INHERITS / READS / WRITES). Without those edges the translate and statespace stages degenerate to zero mappings, so `build_rich_graph` is the canonical "how to get a usable graph in three lines" helper.

## Stage-isolation scripts (01-12)

| Script | Stage | What it shows |
|---|---|---|
| `01_ingest_only.py` | ingest | Discover files in a repo, classify by language, populate `bundle.artifacts['repo_snapshot']` |
| `02_static_only.py` | static | Parse Python source with `PythonASTParser`, count functions/classes/imports |
| `03_normalize_only.py` | normalize | Canonicalize language-specific facts via `CanonicalNormalizer` |
| `04_graph_only.py` | graph | Build a typed `ProgramGraph` from normalized facts |
| `05_translate_only.py` | translate | Run the four default `TranslationRule`s and emit `SemanticMapping`s |
| `06_statespace_only.py` | statespace | Compile a `StateSpaceModel` via `StateSpaceCompiler` |
| `07_process_only.py` | process | Extract a `ProcessModel` via `ProcessExtractor` |
| `08_gnn_export_only.py` | export | Build a complete GNN package with `GNNPackageBuilder` |
| `09_validate_only.py` | validate | Score a GNN package against the 18 canonical sections |
| `10_simulate_only.py` | simulate | Run a `GNNModelRunner` for N steps under Active Inference |
| `11_translate_rules_only.py` | translate (deep) | Register a single rule at a time and inspect its matches per fixture |
| `12_provenance_only.py` | cross-cutting | Walk the provenance records attached to every mapping |

## Higher-order scripts (13-20)

| Script | What it composes | Output highlights |
|---|---|---|
| `13_full_roundtrip.py` | ingest → static → normalize → graph → translate → statespace → process → export → validate | Per-stage timing table, full GNN package on disk, one-shot round-trip demo (~40-100 ms total) |
| `14_cross_fixture_compare.py` | Full pipeline across all 3 control-positive fixtures | Side-by-side table: nodes / edges / mappings / states / observations / actions / validator score |
| `15_confidence_stratification.py` | Registers **all 22 translation rules** via `inspect`, runs `ConfidenceModel.score_batch`, groups by `ConfidenceTier` | Per-tier histograms, per-rule-prefix mean-confidence breakdown, overall mean confidence |
| `16_review_workflow.py` | Synthesises a human review policy over auto-mappings with `ReviewManager` | Accept top-3 by confidence, reject <0.70, edit all `hs_*` entries, show status distribution and `HUMAN_REVIEWED` promotions |
| `17_gnn_sections_walk.py` | Builds a GNN package then walks every `GNNValidator.CANONICAL_SECTIONS` entry | One-line summary per canonical section (state_space, observation_modalities, transition_structure, likelihood_structure, ontology, provenance, confidence, rendering_hints, validation_notes, ...) |
| `18_viz_export_only.py` | GraphVisualizer + MermaidGenerator + SemanticVisualizer + GanttRenderer | D3 HTML, SVG, JSON; 5 Mermaid diagrams (class, dependency, state, sequence, active inference); semantic HTML; Gantt HTML |
| `19_drift_between_fixtures.py` | `DriftAnalyzer` over two compiled bundles (calculator vs event_pipeline) | Total / architectural / semantic-churn drift scores plus per-component node/edge/mapping/state-space deltas |
| `20_session_api.py` | High-level `cogant.api.Session` | `extract_static` → `extract_dynamic` → `build_graph` → `translate_to_gnn` → `compile_state_space` → `export_all`, each call returning a summary dict and the final bundle hitting disk |

## Cross-cutting analysis (21-22)

| Script | What it exercises | Output highlights |
|---|---|---|
| `21_markov_blanket_only.py` | `MarkovBlanketExtractor` across every seed strategy (`auto`, `kind`, `module`, `explicit`) | (μ, s, a, η) counts and boundary ratio per strategy; auto-tier rationale; writes `markov_blanket.json`, `markov_blanket_network.json`, plus collapsed and detailed Mermaid diagrams (role-colored: μ blue, s yellow, a green, η red) |
| `22_gnn_self_analysis.py` | Full end-to-end pipeline on the GNN codebase itself (reflexive analysis); all 17 translation rules; GNN validator; simulation | Per-stage timing table; GNN package on disk; validation score (100/100 on canonical fixtures); free-energy trajectory under Active Inference; PNG rasterization |

## Specialized demonstrations (23-26)

| Script | What it demonstrates | Output highlights |
|---|---|---|
| `23_wave21_rules.py` | Three "wave-21" translation rules: `ParameterRule`, `StateMachineRule`, `RateLimiterRule` on synthetic graph | Synthetic ProgramGraph with parameter/state/rate-limit patterns; per-rule mapping counts; per-node summary table; confidence scores |
| `24_trace_ingester.py` | Chrome DevTools trace ingestion and dynamic enrichment | Synthetic Chrome trace with function entry/exit events; extracted call sequences and call graph; before/after edge counts; runtime evidence tagging |
| `25_changed_and_benchmark.py` | Incremental analysis (`cogant changed`) and benchmark-style performance measurement | CLI help output; full vs incremental pipeline config; timing comparison on calculator fixture; wall-time overhead analysis |
| `26_multi_episode_runtime.py` | `AgentRuntime.run_multi_episode` with VFE tracking and Bayesian learning | 5 episodes × 4 steps; per-episode VFE (mean and final); D prior trajectory (running average); A likelihood updates (frequency-based); ASCII-style VFE plot; learning delta |
| `27_custom_translation_rule.py` | Complete `TranslationRule` subclass (`FactoryMethodRule`) — `matches()`, `apply()`, `explain()` | Custom rule detecting factory methods (`create_*`, `from_*`, `build_*`); registered alongside standard rules; per-match explanations; JSON results |
| `28_export_formats.py` | All supported export formats: GNN Markdown, GNN JSON, GraphML, Parquet | Format × (size, time) comparison table; round-trip validation; `export_comparison.json` |
| `29_bundle_validation_api.py` | `GNNValidator` Python API — per-section scores, errors, warnings, CI gate | Programmatic validation without CLI; threshold-based pass/warn/block decision; degraded-bundle demo |
| `30_graph_diff_api.py` | `DriftAnalyzer` API — architectural + semantic drift between two graph versions | Baseline vs. modified graph; structural drift (Jaccard); architectural drift score; semantic churn; Markdown drift report; CI gate |

## Running

All scripts accept the same two CLI flags from `_common.parse_args`:

* `--target <path>` — repository to analyze (default: `examples/control_positive/calculator`)
* `--output-dir <path>` — where to write artifacts (default: `output/thin/<stage>/`)

Scripts 14, 15, 16, 17, and 19 operate on a hard-coded set of fixtures (they either walk all three control-positive examples or compare two of them), so they ignore `--target`.

From the repo root:

```bash
# Stage-isolation
PYTHONPATH=py python examples/thin_orchestrated/04_graph_only.py \
    --target examples/control_positive/flask_mini \
    --output-dir output/thin/flask_graph

# Higher-order
PYTHONPATH=py python examples/thin_orchestrated/13_full_roundtrip.py \
    --target examples/control_positive/event_pipeline

PYTHONPATH=py python examples/thin_orchestrated/14_cross_fixture_compare.py
PYTHONPATH=py python examples/thin_orchestrated/19_drift_between_fixtures.py
```

Each script is self-contained — running them in order is **not** required. They rebuild whatever upstream context they need.

## Full-coverage sweep

Running every parameterized script against every control-positive fixture plus the five fixture-independent higher-order scripts gives **53 passing combinations**:

```bash
for script in examples/thin_orchestrated/{01,02,03,04,05,06,07,08,09,10,11,12,13,18,20,21}_*.py; do
  for fix in calculator flask_mini event_pipeline; do
    PYTHONPATH=py python "$script" \
      --target "examples/control_positive/$fix" \
      --output-dir "output/thin/verify/$(basename "$script" .py)_$fix"
  done
done
for script in examples/thin_orchestrated/{14,15,16,17,19}_*.py; do
  PYTHONPATH=py python "$script"
done
```

## Why this matters

The full `RoundtripOrchestrator` does a lot of work in one call. When you're learning COGANT, debugging a stage, or wiring a new plugin, a 30-line script that touches a single module is much easier to understand than a 1000-line orchestrator. The 01-12 scripts are the canonical "how do I use stage X" reference. The 13-20 scripts are the canonical "how do I combine stages into a real workflow" reference and double as a high-level smoke test for the whole toolchain.
