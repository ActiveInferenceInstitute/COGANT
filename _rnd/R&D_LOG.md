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

## Upcoming

| Phase | Status | Target |
|-------|--------|--------|
| P0 | ✅ Complete | 73.76% / 70% gate |
| P1 | ✅ Complete | 77.42% / 75% gate |
| P1.5 | 🔄 In progress | Rust edge FFI, benchmark |
| P3 | Pending | Qualitative validation, ACTIVE_INFERENCE_MAPPING.md |
| P4 | Pending | Manuscript audit, experimental numbers |
| P5 | Pending | tree-sitter, JS/TS, git-diff mode |
