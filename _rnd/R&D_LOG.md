# COGANT R&D Log

Dated entries per tier. Each entry: what changed, test numbers, coverage, what broke, what's next.

---

## 2026-04-09 — P0 Gate

**What changed:**
- Initialized standalone git repo in `projects_in_progress/cogant/` (template repo gitignores this path)
- Replaced all 17 hollow unit test files (tested plain dicts) with real cogant class instantiation
- New test files: test_graph_builder.py, test_confidence.py, test_gnn_export.py, test_state_space.py, test_translation_rules.py, test_validation.py, test_parser.py (all rewritten)
- `static/dataflow.py`: 19% → 84% — full READ/WRITE/DEPENDS_ON edge extraction from AST (assignments, augmented, attribute access, subscript, unpacking, call args, return values, scoped)
- `static/types.py`: 16% → 77% — type annotation propagation (function params, returns, class attrs, variables, self.x in __init__, literal type inference)
- `parsers/python/parser.py::extract_calls()`: wired to `CallGraphBuilder` (was returning `[]`)
- All 8 Rust crates compiled (`cargo build --release`), PyO3 FFI wired via maturin
- `py/cogant/rust_backend.py`: feature-flagged `COGANT_USE_RUST=1` → RustProgramGraphAdapter
- Coverage gate: `--cov-fail-under=70` added to pyproject.toml (bumped to 75% at P1)
- `.pre-commit-config.yaml`: ruff lint+format, pre-commit-hooks

**Test results:** 681 passed, 3 skipped | 73.76% coverage (70% gate met)
**Baseline was:** 176 integration tests, 64% coverage

**What broke:** Nothing. matplotlib not installed → 23 PNG tests failed at gate check; fixed by installing viz extras (`uv pip install matplotlib plotly jinja2`).

**Decisions made:**
- git init in `projects_in_progress/cogant/` (not `cogant/cogant/`) — root of the project subtree
- Coverage gate starts at 70% (73.76% achieved), bumped to 75% for P1

**What's next:** P1 — core correctness, A/B/C/D matrices, real-world fixtures, dynamic pipeline.

---

## 2026-04-09 — P1 Gate

**What changed:**

### Statespace + Process (compiler.py, timeline.py, policies.py)
- `statespace/compiler.py`: 75% → 86% — completed `_extract_actions()`, `_extract_transitions()`, `_extract_likelihoods()`, `_extract_preferences()`
  - Actions from ACTION/POLICY mappings + WRITES edges for outcomes
  - Transitions: action→hidden_state WRITES → Transition(from, action, to, probability)
  - Likelihoods: Bernoulli/Categorical/Gaussian from type_hint metadata
  - Preferences: CONSTRAINT/PREFERENCE mappings → Preference(variable, expression, weight)
- `statespace/temporal.py`: → 80% — async detection, event-driven discrete/continuous classification
- `process/timeline.py`: 16% → 94% — topological ordering, parallel stage detection, fan_out/fan_in
- `process/policies.py`: 40% → 99%
- All 3 control-positive repos produce non-empty StateSpaceModel

### GNN A/B/C/D Matrices (AII upstream validator compliance)
- New file: `py/cogant/gnn/matrices.py` (480 lines) — `GNNMatrices` class
  - A matrix (likelihood P(o|s)): from READS/OBSERVES edges, observation→hidden_state. Row-normalized.
  - B tensor (transition P(s'|s,a)): from WRITES/MUTATES edges, action→hidden_state. Column-normalized per (state,action) pair. Identity fallback for actions without writes.
  - C vector (log preferences): from CONSTRAINT/PREFERENCE mapping confidence scores, signed negative for avoid/reject labels
  - D vector (initial prior): from StateVariable domain + CONFIGURATION neighbors, confidence-weighted, uniform fallback
- `py/cogant/gnn/formatter/structural.py`: `_format_state_space()` emits AII bracket notation `A[[rows=N][cols=M]]`
- `py/cogant/gnn/validator.py`: `validate_matrices()` checks shape + probability simplex constraints
- `py/cogant/gnn/json_export.py`: `matrices` key added to JSON output
- Validator returns 0 errors on calculator, event_pipeline, flask_mini fixtures

### Real-World Fixtures + Dynamic Analysis
- `examples/real_world/flask_app/` (6 files, ~850 lines) — Flask-pattern web app
- `examples/real_world/requests_lib/` (7 files, ~750 lines) — HTTP client library pattern
- `examples/real_world/json_stdlib/` — CPython 3.11 `Lib/json/` (verbatim copy, ~1,231 lines)
- `tests/integration/test_real_world_pipeline.py` — 21 tests, all 3 repos produce non-empty GNN
- Dynamic analysis wired: `PipelineConfig.skip_dynamic`, `--no-dynamic` CLI flag on translate/process/benchmark
- Dynamic stage gracefully skips when no .coverage / trace data present

### Principled VFE/EFE + Plugin/Provenance Coverage + Rust Hot Path
- `simulate/free_energy.py`: 15% → covered — principled VFE = KL[Q||P] - E_Q[log P(o|s)], principled EFE = epistemic (entropy) - pragmatic (C·pred_obs) per timestep
- `simulate/runner.py`: ModelRunner accepts A/B/C/D; `vfe_from_beliefs()`, `efe_for_policy()`, `update_beliefs_from_observation()` delegate to principled math; heuristic fallback preserved for back-compat
- `plugins/base.py`: 0% → covered — Plugin/LanguagePlugin/TracePlugin ABC lifecycle tested
- `provenance/tracker.py`: 0% → covered — add/query/merge/serialize all tested
- `translate/review.py`: 17% → covered — accept/reject/edit/split/merge/history all tested
- `rust_backend.py`: `RustProgramGraphAdapter` wrapping PyO3 behind `COGANT_USE_RUST=1`
- `benchmarks/bench_graph_build.py`: raw Rust node-only 1.28× faster; adapter currently 0.63× (Python shadow store overhead — edge ingest in Rust needed for real win)

**Test results:** 869 passed, 4 skipped | 77.42% coverage (75% gate met)

**What broke:**
- PNG tests failed at initial gate: matplotlib not in default deps. Fix: `uv pip install matplotlib plotly jinja2` (viz extras). Added to `[all]` extras in pyproject.toml.
- Rust adapter speedup is negative on small graphs (0.63×). The Python shadow store and double construction eliminate the FFI benefit at this scale. Edge ingest needs to move into Rust FFI to unlock real speedup.

**Decisions made:**
- AII GNN matrices use pure-Python arrays (no numpy dep) — matches existing codebase style
- `simulate/runner.py` keeps heuristic fallback when A/B/C/D not provided — backwards-compatible
- Rust hot path: `COGANT_USE_RUST=1` env var, not hardwired — lets users opt in
- Real-world fixtures are synthetic-but-realistic pattern files (not full Flask clone) for speed and stability

**Open items going into P1.5/P3:**
- Rust edge ingest needs to move into FFI to get real speedup (deferred P1.5 item)
- `statespace/variables.py` at 56% — needs more test coverage
- `scoring/drift.py` at 44%, `scoring/metrics.py` at 29% — low but not blocking
- Tree-sitter integration (P5) still pending

**What's next:** P1.5 Rust edge FFI, P3 qualitative validation, P4 manuscript audit, P5 tree-sitter.

---

## 2026-04-09 — P3 Gate

**What changed:**

### Qualitative AI Role Validation
- New file: `tests/unit/test_ai_role_validation.py` (16 tests) — asserts that Active Inference role assignments produced by the translator match hand-curated expectations on the three control-positive fixtures (calculator, event_pipeline, flask_mini).
  - Each test locks down a specific theory-to-code mapping: observations ↔ function parameters / external inputs, hidden_states ↔ internal variables / class attributes, actions ↔ mutating functions / event handlers, preferences ↔ assertions / validation constraints.
  - Tests assert both presence (roles exist) and absence (roles are not misassigned) to catch silent drift.
- New file: `_rnd/ACTIVE_INFERENCE_MAPPING.md` — formal theory document mapping code patterns to Active Inference roles. Serves as the durable contract between code-pattern detectors and the AI ontology used by the GNN emitter. Cross-references the AII upstream spec.

### Surprising findings surfaced during P3
Four bugs / gaps uncovered while writing the validation tests — documented in-log but not all fixed in P3:
1. `gnn/semantic_mappings.json` exporter drops the `confidence` field for a subset of rule types (shape-only mapping). Needs follow-up.
2. `ActionRule` has a recall gap on top-level functions with side-effect-only bodies (detected side effects but did not promote to action role). Logged for P3.5.
3. `json_stdlib` fixture produces 0 actions and 0 transitions — this is a function-heavy codebase with very few mutating top-level call sites; the current action detector is class-biased. Not a bug per se, but highlights a detector coverage limitation.
4. `calculator` GNN runner raises `empty-beliefs` error on the 0-state-variable fixture path (divide-by-zero in belief normalization). Needs guard in `simulate/runner.py`.

**Test results:** 885 passed, 4 skipped | ~77% coverage (75% gate still met)
**Delta from P1:** +16 tests (869 → 885). No coverage regression.

**What broke:** Nothing blocking. Four findings above logged for downstream fix-up; none caused test suite failures.

**Decisions made:**
- ACTIVE_INFERENCE_MAPPING.md lives in `_rnd/` (not `docs/`) because it is R&D-phase scaffolding; will migrate to `docs/theory/` when the mapping stabilizes.
- Validation tests assert specific roles on specific symbols (brittle but intentional) — the goal is to catch silent drift, so the brittleness is a feature.
- P3.5 / bug-fix sweep deferred out of the P3 gate to keep the phase scope tight.

**Open items going into P4/P5:**
- Four bugs above (semantic_mappings exporter, ActionRule recall, action-detector class bias, empty-beliefs guard)
- Validation fixtures still limited to 3 control-positive repos; need negative fixtures (non-AI code) to lock down false-positive rates.

**What's next:** P4 manuscript audit and experimental numbers; P5 tree-sitter multi-language.

---

## 2026-04-09 — P4 Gate

**What changed:**

### Manuscript Audit + Real Experimental Numbers
- `manuscript/06_experimental_setup.md` — rewritten with Tables 4–7 containing real numbers harvested from actual pipeline runs on the six fixtures (calculator, event_pipeline, flask_mini, flask_app, requests_lib, json_stdlib). Replaces the prior placeholder tables that hand-waved on sizes and timings.
- `manuscript/05_conclusion.md` — expanded from 5 shipped capabilities to 10, reflecting the actual P0/P1 deliverables (A/B/C/D matrices, dynamic pipeline, VFE/EFE, Markov blanket, real-world fixtures, Rust scaffold, provenance, plugins, review workflow, AII validator compliance).
- `manuscript/04_examples_and_failure_modes.md` — Flask walkthrough rewritten against `flask_app` with real counts: 98 nodes, 597 edges. Prior draft used synthetic pedagogical numbers.

### Reproducible Figures
- New file: `_rnd/figures/generate_figures.py` (406 lines) — single-entry figure generator. Reads canonical metrics, produces four PNGs used in the manuscript (fixture scale bar chart, coverage trajectory, VFE/EFE trace on calculator, role-confusion heatmap).
- New file: `_rnd/figures/metrics.json` — canonical machine-readable metrics for all six fixtures (nodes, edges, role counts, A/B/C/D shapes, runtime). Source of truth for both manuscript tables and figures; eliminates the "the number in the text doesn't match the number in the figure" class of manuscript bug.

### Scoping Report Refresh
- `_rnd/SCOPING_REPORT.md` bumped to v3 — reflects P0/P1/P3 gates, updated coverage, remaining-work delta.

**Test results:** 885 passed, 4 skipped | ~77% coverage (75% gate still met)
**Delta from P3:** No new tests. P4 is a documentation/figure phase; all code churn was in manuscript sources and `_rnd/figures/`.

**What broke:** Nothing. Manuscript builds clean; figures regenerate deterministically.

**Decisions made:**
- `_rnd/figures/metrics.json` is the single source of truth for manuscript numbers — both tables and figures read from it. Any new metric in the manuscript must land in metrics.json first.
- Figure generator uses `MPLBACKEND=Agg`, fixed RNG seeds, and writes to `_rnd/figures/out/` (gitignored). This matches the reproducibility posture of the rest of the template.
- Conclusion section inflation from 5→10 items reflects what actually shipped; resisted the temptation to list aspirational P5/P1.5 work.

**Open items going into P5:**
- Literature review stream (LITERATURE.md, RELATED_WORK.md) still pending — tracked as LIT stream, not a gated phase.
- Figures are static PNGs; interactive plotly variants for the HTML/web build of the manuscript still TODO.

**What's next:** P5 tree-sitter multi-language substrate + git-diff incremental mode.

---

## 2026-04-09 — P5 Gate

**What changed:**

### Tree-Sitter Multi-Language Substrate
- New file: `py/cogant/parsers/tree_sitter_base.py` (507 lines) — `TreeSitterParser` universal wrapper around `tree_sitter` bindings. Loads grammars lazily, normalizes the CST into cogant's internal ProgramGraph node/edge schema, and exposes a per-language plugin hook for language-specific refinements. Supports Python, JavaScript, and TypeScript grammars in P5.
- New file: `py/cogant/parsers/javascript/parser.py` — `JavaScriptLanguagePlugin` using tree-sitter. Function/class/module extraction, import graph, basic call graph. Plugs into the existing `LanguagePlugin` ABC so the downstream pipeline (translation rules, state space, GNN export) is language-agnostic.
- New file: `py/cogant/parsers/typescript/tree_sitter_parser.py` — TypeScript parser. Uses both `tree-sitter-typescript::language_typescript` and `::language_tsx` so both `.ts` and `.tsx` inputs route correctly. Type annotations flow into the existing type-inference pass.

### Git-Diff Incremental Mode
- New file: `py/cogant/ingest/incremental.py` (234 lines) — `IncrementalIngester`. Uses `git diff --name-status` between two refs (default: HEAD~1..HEAD) to compute changed files, then re-runs the parser + translation rules only on the affected subgraph. The merger preserves pre-existing nodes/edges from unchanged files.
- New CLI command: `cogant changed` — thin orchestrator over `IncrementalIngester`. Flags for `--since <ref>`, `--until <ref>`, `--json` output. Designed for CI use (analyze only what changed in a PR).

### Tests
- New file: `tests/unit/test_tree_sitter.py` — tree-sitter base parser tests (grammar loading, CST normalization, plugin hook invocation, error handling on malformed sources).
- New file: `tests/unit/test_js_parser.py` — JavaScript plugin end-to-end smoke tests (small JS fixture in → ProgramGraph out with expected roles).
- 22 new tests total.

**Test results:** 907 passed, 4 skipped | ~77–78% coverage (75% gate still met)
**Delta from P4:** +22 tests (885 → 907).

**What broke:**
- Tree-sitter grammar wheels are platform-specific; the `tree-sitter-typescript` 0.21 wheel exposes `language_typescript` and `language_tsx` as separate entry points (not a single `language()` export). Initial import patterned after the Python binding failed; fix was to call both explicitly.
- Git-diff path resolution for renames: `git diff --name-status` emits `R100 old new` which the first cut of the parser treated as three separate files. Fixed with a small parser for the R/C status lines.

**Decisions made:**
- Tree-sitter parsers run alongside — not in place of — the existing AST-based Python parser. The AST parser is still authoritative for Python because it has richer type and dataflow coverage; tree-sitter is the fallback and the only path for non-Python languages. This lets us ship JS/TS without regressing Python fidelity.
- Incremental mode merges into an on-disk ProgramGraph cache keyed by file SHA. On cache miss, it falls back to a full re-parse of the affected file. Cache invalidation is explicit (`cogant changed --no-cache`).
- `cogant changed` emits a JSON diff summary (added/removed/changed nodes and edges) in addition to the merged graph — this is what downstream CI integrations will consume.

**Open items going into post-P5:**
- Rust edge FFI (P1.5) still in progress — blocked on edge ingest moving into Rust to unlock real speedup.
- Tree-sitter C/C++/Rust/Go grammars not yet wired (only Py/JS/TS in P5).
- Incremental cache eviction policy is LRU-by-file-count; no size-based eviction yet.
- EXP streams: property-based tests (hypothesis), `cogant explain` CLI, perf harness — all in progress, not gated.
- LIT stream: `LITERATURE.md`, `RELATED_WORK.md` — in progress, not gated.
- P3 bug sweep: four findings logged in P3 (semantic_mappings exporter, ActionRule recall, action-detector class bias, empty-beliefs guard) still open.

**What's next:** P1.5 Rust edge FFI completion; EXP stream completion (property tests, explain CLI, perf harness); LIT stream completion (LITERATURE.md, RELATED_WORK.md); P3 bug sweep.

---

## Upcoming

| Phase | Status | Target |
|-------|--------|--------|
| P0 | ✅ Complete | 73.76% / 70% gate |
| P1 | ✅ Complete | 77.42% / 75% gate |
| P3 | ✅ Complete | Qualitative validation, ACTIVE_INFERENCE_MAPPING.md, 885 tests |
| P4 | ✅ Complete | Manuscript audit, experimental numbers, figures/metrics.json |
| P5 | ✅ Complete | tree-sitter Py/JS/TS, git-diff incremental, 907 tests |
| P1.5 | 🔄 In progress | Rust edge FFI, benchmark |
| EXP streams | 🔄 In progress | Property tests, `cogant explain` CLI, perf harness |
| LIT stream | 🔄 In progress | LITERATURE.md, RELATED_WORK.md |
