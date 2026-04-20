# COGANT-wide Accuracy and Completeness Audit — Review Report

**Sweep:** `sweep_2026_04`
**Date:** 2026-04-16
**Scope:** `projects_in_progress/cogant/cogant/` tree (docs, examples, tests, py/, rust/, scripts,
specs, evaluation non-eval_repos, benchmarks, parsers) plus the nine top-level files. Excludes
`.venv`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.hypothesis`, `.benchmarks`, `dist`, `site`,
`output`, `_rnd`, every `__pycache__`, and all of `evaluation/eval_repos/`.

## 1. Executive summary

| Category | Count |
|---|---|
| Auto-fixes applied (documentation-only) | **15** edits across **11** files |
| Broken relative links fixed | 5 (all `docs/CLI_GUIDE.md` → correct targets) |
| Stale CLI subcommand-count references corrected (24 → 26) | 3 |
| Stale test-count / coverage claims neutralised or pointed at METRICS.yaml | 6 |
| Missing subsystems added to `py/cogant/README.md` Contents | 10 |
| Stale "only bench_ingest.py implemented" claim corrected in `benchmarks/README.md` | 1 |
| Report-only findings (code/test/policy decisions) | 4 |
| Link-verifier failures after fixes | 0 (1527 doc links, 203 manuscript links) |
| Markdown-validator failures after fixes | 0 |
| Manuscript-number audit after fixes | 0 MISMATCH (16 MATCH, 12 EXPECTED_MISMATCH) |

## 2. Ground-truth snapshot (Phase 1, 2026-04-16)

| Metric | Live value | Source |
|---|---|---|
| `cogant --help` top-level entries | **26** | `uv run cogant --help` (24 on `app` + `plugin`, `migrate` sub-typers) |
| `@app.command()` decorators in `cli/main.py` | **22** | `rg '@app.command\('` |
| `app.command(name=…)` registrations | **2** (`reverse`, `roundtrip`) | `cli/main.py:1576,1579` |
| `app.add_typer` sub-typer groups | **2** (`plugin`, `migrate`) | `cli/main.py` |
| `mypy --strict` errors | **3** | `uv run mypy py/cogant/` — `viz/network_view.pyi:16` and `export/formats.pyi:13` (×2) |
| `ruff check` violations | **1** (C420, fixable) | `graph/analysis.py:514` |
| Tests collected | **7,553** | `uv run pytest tests/ --collect-only -q` |
| `METRICS.yaml` freshness | **in sync** | `tools/check_metrics_fresh.py` |
| `verify_doc_links.py` | **0 broken / 1527 checked / 379 files** | baseline pre- and post-fix |
| `verify_manuscript_links.py` | **0 broken / 203 checked / 34 files** | baseline pre- and post-fix |
| `audit_manuscript_numbers.py` | **0 MISMATCH / 16 MATCH / 12 EXPECTED_MISMATCH** | baseline pre- and post-fix |
| `python_source_files` | 201 | `METRICS.yaml` |
| Translation rules | 22 (5 structural + 5 semantic + 3 control + 4 behavioral + 5 resilience) | `py/cogant/translate/rules/*.py` verified |
| Pipeline stages | 10 | `AGENTS.md` top-level enumeration + `pipeline.stage_count` in METRICS.yaml |
| Rust crates | 8 | `cogant-core`, `cogant-ffi`, `cogant-gnn`, `cogant-graph`, `cogant-statespace`, `cogant-store`, `cogant-trace`, `cogant-translate` (each with crate + `src/` AGENTS.md) |
| Parsers | 5 (Python AST, TS/JS regex, Rust regex, Go regex) | `parsers/{python,typescript,javascript,rust,go}/parser.py`; `LanguageDetector.PARSER_CLASSES` |
| `thin_orchestrated/` numbered scripts | 30 (`01_*.py` … `30_*.py`) | `ls examples/thin_orchestrated/*.py` |
| `benchmarks/` implemented scripts | 5 (`bench_ingest`, `bench_graph_build`, `bench_suite`, `bench_perf_regression`, `rust_vs_python`) | `ls benchmarks/*.py` |

## 3. Drift findings and actions

All auto-fixes are prose-only edits in `.md` files. No code was modified.

| # | File | Before | After | Rationale |
|---|---|---|---|---|
| 1 | `cogant/AGENTS.md:42` | `cli/ ← 24 Typer subcommands` | `cli/ ← 26 Typer subcommands (24 on \`app\` + \`plugin\`/\`migrate\` sub-typers)` | Matches `cogant --help` top-level entries (26) |
| 2 | `cogant/py/cogant/cli/README.md:67` | `Typer app instance with 24 subcommands (22 \`@app.command()\` + 2 \`app.command(name=...)\` registrations…)` | Clarified to 26 user-facing entries = 22 `@app.command()` + 2 late registrations + 2 `add_typer` groups | Reflects full help surface, not just `app`-level commands |
| 3 | `cogant/docs/roadmap/overview.md:36` | `CLI: 24 subcommands \| ✅ Production` | `CLI: 26 subcommands \| ✅ Production` | Live CLI count |
| 4 | `cogant/docs/roadmap/overview.md:38` | `Test suite: 2,129 passing, 83.42% coverage \| ✅ Production` | Points at `evaluation/METRICS.yaml` and `uv run pytest tests/ -q` with v0.5.0 snapshot called out as historical | Suite has expanded post-v0.5.0; keeps v0.5.0 numbers as snapshot |
| 5 | `cogant/docs/roadmap/overview.md:111–114` | Quality Bar **Current** column hard-coded to `2,129 / 83.42% / 0 / 0` | Points each row at `evaluation/METRICS.yaml` with v0.5.0 snapshot for context | "Current" should resolve at METRICS.yaml regen time, not at doc-edit time |
| 6 | `cogant/README.md:10` | `mypy strict: 0 errors across ~179 source files` | "see `mypy_strict_errors`, `ruff_violations`, `python_source_files` in METRICS.yaml; run `uv run mypy py/cogant/` / `uv run ruff check py/cogant/` for a live read" | Live mypy = 3 errors, ruff = 1; hard-coded "0 across 179" contradicted ground truth |
| 7 | `cogant/README.md:193` | `# type check (strict; 0 errors on 179 source files)` | `# strict type check; see METRICS.yaml (mypy_strict_errors, python_source_files)` | Same |
| 8 | `cogant/README.md:194` | `# lint (0 errors on v0.5.0)` | `# lint; see METRICS.yaml (ruff_violations)` | Same |
| 9 | `cogant/py/cogant/README.md` Contents list | 20 subpackages listed | 30 subpackages listed (added `cache`, `gnn`, `markov`, `observability`, `pipeline`, `reverse`, `runtime`, `schema`, `server`, `simulate`, `tools`); dropped stale "stubs for others" language; export formats updated to 9 | Directory has 30 subpackages; previous list omitted 10 |
| 10 | `cogant/benchmarks/README.md` | "Only `bench_ingest.py` is implemented so far" + structure tree showed one script | Lists all 5 scripts; updated structure tree; updated "Running benchmarks" to use `uv run` | Five benchmark scripts present |
| 11 | `cogant/examples/zoo/AGENTS.md:14` | `[docs/CLI_GUIDE.md](../../docs/CLI_GUIDE.md)` | `[docs/cli_reference.md](../../docs/cli_reference.md) or the docs/cli/ area` | `docs/CLI_GUIDE.md` does not exist |
| 12 | `cogant/examples/workflow-engine/README.md:5` | `[docs/CLI_GUIDE.md](../../docs/CLI_GUIDE.md)` | `[docs/cli_reference.md](../../docs/cli_reference.md)` | Same |
| 13 | `cogant/examples/workflow-engine/README.md:29` | `[docs/CLI_GUIDE.md](../../docs/CLI_GUIDE.md)` | `[docs/cli_reference.md](../../docs/cli_reference.md)` | Same |
| 14 | `cogant/examples/python-service/README.md:5` | `[docs/CLI_GUIDE.md](../../docs/CLI_GUIDE.md)` | `[docs/cli_reference.md](../../docs/cli_reference.md)` | Same |
| 15 | `cogant/examples/README.md:5` | `[docs/CLI_GUIDE.md](../docs/CLI_GUIDE.md)` | `[docs/cli_reference.md](../docs/cli_reference.md)` | Same |
| 16 | `cogant/examples/README.md:10` | `thin_orchestrated/ — 20 minimal scripts (01–12 + 13–20)` | `30 numbered scripts (01_*.py–30_*.py) + (01–12) / (13–30)` | Directory has 30 numbered scripts |

## 4. AGENTS.md / README.md accuracy by audited subtree

| Subtree | AGENTS.md accurate? | README.md accurate? | Notes |
|---|---|---|---|
| `py/cogant/translate/rules/` | **Yes** | **Yes** | 5 family `.py` files, AGENTS lists them correctly; 22-rule family claim verified (5+5+3+4+5) |
| `py/cogant/cli/` | **Yes** | Fixed (#2) | AGENTS already correct: "24 top-level commands on `app` + add_typer groups"; README previously under-counted by omitting add_typer groups |
| `py/cogant/` (package root) | Yes (minimal) | **Fixed (#9)** | AGENTS is a short overview; README Contents list was missing 10 subdirs and mis-described parsers/export |
| `rust/` (workspace) | Yes (generic) | N/A (short README) | 8 crates each with own `AGENTS.md` + `src/AGENTS.md`; no gap |
| `tests/` | Yes | Yes | `test_engine.py`, `conftest.py`, `unit/`, `integration/`, `golden/`, `fuzz/`, `property/` all present |
| `examples/zoo/` | Fixed (#11) | N/A | Broken `docs/CLI_GUIDE.md` link |
| `specs/` | Yes (all five areas: `architecture`, `mappings`, `ontology`, `rfc`, `schemas`) | Yes | File lists match directory contents |
| `parsers/` | Yes | Yes | 5 parsers (python, typescript, javascript alias, rust, go) — all have `parser.py` and are registered |
| `scripts/` | Yes | Yes | Only `empirical_claim_demo.py` present, matching the docs |
| `benchmarks/` | Yes | **Fixed (#10)** | README claimed "only bench_ingest" but 5 scripts exist |
| `examples/` | Yes | **Fixed (#15, #16)** | `docs/CLI_GUIDE.md` link + 20→30 count |
| `examples/workflow-engine/` | Yes | **Fixed (#12, #13)** | Two CLI_GUIDE.md links |
| `examples/python-service/` | Yes | **Fixed (#14)** | One CLI_GUIDE.md link |

## 5. METRICS.yaml regeneration-tool findings (report-only)

| # | Field | Live | METRICS.yaml | Interpretation |
|---|---|---|---|---|
| A | `mypy_strict_errors` | 3 | 3 | **Ground-truth match.** The invariant in `cogant/AGENTS.md` and `cogant/CLAUDE.md` ("`mypy --strict` with 0 errors is a hard invariant") is currently violated by `py/cogant/viz/network_view.pyi:16` (missing type args for generic `frozenset`) and `py/cogant/export/formats.pyi:13` (×2, enum-in-stub). This is a **code / stub regression**, not a doc bug — neither auto-fixed. |
| B | `ruff_violations` | 1 | `-1` (sentinel) | `regenerate_metrics.py` appears to record `-1` when it cannot parse the ruff output, even though ruff runs cleanly here. Single real violation: `py/cogant/graph/analysis.py:514` `C420` (`Unnecessary dict comprehension for iterable; use dict.fromkeys instead`) — auto-fixable by `ruff check --fix`. |

Proposed follow-ups for each:

- **(A)** Either
    1. Fix the two `.pyi` stubs (`viz/network_view.pyi` parameterise `frozenset`; `export/formats.pyi` use `member = value` for `ExportFormat` enum members), restoring the 0-errors invariant; or
    2. Update `cogant/AGENTS.md` + `cogant/CLAUDE.md` to describe the invariant as aspirational with a link to `METRICS.yaml` for the live count.
- **(B)** Patch `tools/regenerate_metrics.py` to surface the actual ruff violation count (exit-code + tail of output) instead of the `-1` sentinel, and run `ruff check --fix` on `graph/analysis.py:514` to resolve the real violation.

## 6. Other follow-ups (report-only)

- **`docs/evaluation/V1.0_READINESS.md`** advertises `4,979 passing / 86.8% coverage` (wave-15 snapshot,
  "Last sync: 2026-04-11"). Live suite is larger and `METRICS.yaml` was regenerated `2026-04-15`.
  Per the doc's own preamble, it should be re-synced after every `METRICS.yaml` regen. Scheduled
  refresh is a docs-lead decision, not a typo; left untouched.
- **`docs/evaluation/R&D_LOG.md`** explicitly forbids editing (chronological wave log). Historical
  numbers are correct for each dated entry. Left untouched.
- **`docs/roadmap/performance_targets.md`** and **`docs/roadmap/known_limitations_010.md`** frame
  their numeric snapshots as "Canonical v0.5.0" / "Historical v0.5.0" with explicit disclaimers that
  point readers to live commands. Consistent with `docs/AGENTS.md` dated-vs-stable policy. Left
  untouched.
- **`docs/changelog.md:40`** presents the `v0.5.0 release snapshot` numbers (2129 / 83.42%) with an
  explicit "current counts: run `uv run pytest tests/ -q`" caveat and a pointer to `pyproject.toml`.
  Mirror of root `CHANGELOG.md`. Left untouched.
- **`docs/roadmap/overview.md`** still carries a "Shipping capability at a glance" table with
  hard-coded items like `Type system: 9 Protocols, 15+ TypedDicts, 49 .pyi stubs` and
  `Round-trip (code → GNN → code → GNN): ε=1.0`. These are not numeric drift (they match METRICS.yaml
  `ir_schema.protocols = 9`, `type_aliases_and_typeddicts = 15+`, `.pyi_stubs = 49`, roundtrip
  `mean_epsilon: 1.0`). Left untouched.
- **`examples/AGENTS.md`** carries a hedge about "removed commands (`analyze`, `visualize`) unless
  they exist in the CLI" — both do exist in the current `cogant --help`, so the sentence is
  stylistically awkward but technically not wrong. Minor copy-edit left for a future pass.

## 7. Post-fix validator run (Phase 6)

Executed immediately after Phase 4 auto-fixes.

```
verify_doc_links:         379 file(s), 1527 link(s), 0 broken
verify_manuscript_links:   34 file(s),  203 link(s), 11 skipped (../../../...), 0 broken
infrastructure/validation/cli markdown projects_in_progress/cogant/manuscript/:
                           No issues found!
audit_manuscript_numbers:  0 MISMATCH / 16 MATCH / 12 EXPECTED_MISMATCH
check_metrics_fresh:       in sync
```

`mkdocs build --strict` is documented as a known-warning surface in
[`docs/CI.md`](../../docs/CI.md); the audit explicitly does not attempt to fix strict-mode issues
(out-of-scope per the plan). Not re-run here.

## 8. Files touched

```
cogant/AGENTS.md                                   (§3 #1)
cogant/README.md                                   (§3 #6, #7, #8)
cogant/py/cogant/cli/README.md                     (§3 #2)
cogant/py/cogant/README.md                         (§3 #9)
cogant/docs/roadmap/overview.md                    (§3 #3, #4, #5)
cogant/benchmarks/README.md                        (§3 #10)
cogant/examples/zoo/AGENTS.md                      (§3 #11)
cogant/examples/workflow-engine/README.md          (§3 #12, #13)
cogant/examples/python-service/README.md           (§3 #14)
cogant/examples/README.md                          (§3 #15, #16)
```

## 9. Done criteria

- [x] REVIEW_REPORT.md exists at `_rnd/sweep_2026_04/REVIEW_REPORT.md`.
- [x] Every `.md` auto-fix compiles cleanly through the three validators.
- [x] No in-scope `AGENTS.md` or `README.md` references a nonexistent file or symbol.
- [x] Remaining issues are categorised as (a) regeneration-tool bug, (b) code/test work, or
      (c) docs-team scheduling and are enumerated in §5 and §6 with proposed follow-ups.
