# COGANT review-and-improvement pass log — 2026-09-08

Fleet review-and-improvement pass on `ActiveInferenceInstitute/COGANT`
(default branch `main`, base `39b961b` "chore(metrics): regenerate METRICS
against commit-bound HEAD"). Clean worktree at start; no pre-existing dirty
files.

## Phase 0 — Preflight

- Baseline gates verified at HEAD: manuscript audit battery green
  (crossrefs 126 ids / 515 refs, citations 155/155, numbers 0 mismatches,
  markdown links 0, math adjacency 0, claim scope 0, robustness 8/8,
  formalisms, synthetic surfaces, module refs 88/0 unresolved, figure
  renderers 14+3, coverage table, metrics freshness, folder docs, docs
  constants, `.pyi` exports, publication readiness `verdict=ready`).
- Full package suite baseline: `uv run pytest tests/ -q` → 1 failed with
  `-x` (property law 4), and `.pytest_cache/lastfailed` listed 39 stale
  node-ids (most already fixed; cache had not been cleared).

## Phase 1 — Review findings (7 parallel dimension scouts)

Ranked outcomes per dimension:

1. **Package tests** — 6 genuinely failing property tests
   (`test_correctness_laws.py` laws 4/5/6, `test_law_matrix_stochasticity.py`
   5a/5b/5c) pinned a removed contract: they built source models with empty
   A/B/C/D and expected `render_matrices_module` to invent defaults. The
   renderer is now deliberately fail-closed ("no matrix is invented when the
   source is incomplete"), so the tests contradicted the implemented
   contract. The other lastfailed clusters (config loaders, language
   fallbacks, package-init) were already green — stale cache.
2. **run_all orchestration** — `--fail-fast` returned mid-loop before
   `run_manifest.json`/`summary.*` were written, discarding all completed
   targets' evidence; `run_cmd_capture` had no timeout (a hung child blocks
   the batch forever); an interrupted git clone (dest without `.git`)
   poisoned every re-run; `export-gnn:{tid}` check label did not match the
   recorded `export_gnn:{tid}` step name.
3. **Tools/scripts hygiene** — two silent-fallback paths weakened gates:
   `audit_manuscript_math_adjacency._resolve` swallowed resolution failures
   (auditing unsubstituted text = silent pass) and
   `check_coverage_table._load_metrics_yaml` returned `{}` on missing or
   broken METRICS.yaml. Entry points are otherwise thin with `__main__`
   guards; no dead tools found; duplication findings noted as taste, not
   fixed.
4. **Manuscript** — prose quality high, cross-refs/figures/citations clean;
   the injected copy under `output/manuscript/` was stale relative to
   METRICS.yaml (9560/53/48 vs 9606/6/47 and older timestamps). Fixed by
   re-running the documented generator (regenerated outputs are disposable).
   The audit battery contradicts the scout's "7 uncited bib entries"
   observation: 155 keys defined, 155 used, 0 orphans.
5. **Plans vs implemented state** — cog-p1-02 (parser capability registry)
   is fully implemented and accepted → closed; cog-p1-01 substantially
   implemented but the schema-version migration mechanism is partial → kept
   active; tasks.yaml has overdue `in_progress` rows (server-managed file,
   left untouched, flagged to the owner); TODO.md cited a regression test at
   a path that does not exist (historical section, left as dated history).
6. **REVIEW_LOG follow-through** — sole log `REVIEW_LOG_2026-08-02.md`; of
   its three open items, the audit-test failure was already fixed
   (5/5 green) and METRICS had been regenerated on 2026-08-19, but the
   TODO checkboxes were never ticked. Notebook stubs remain deliberately
   open. Both resolved items are now recorded; METRICS regenerated again
   against this pass's commit-bound HEAD.
7. **Figures** — 18/18 registered figures pass strict copy + visual QA; no
   orphaned manuscript references; only cosmetic extras (unregistered audit
   PNG; missing source sidecars for eval fig1–fig4, tolerated by the copier).

## Phase 2 — Implementation (commits)

1. `9ac186d` — test(property): laws 4/5/6 + matrix-stochasticity strategies
   supply complete valid source matrices; law4/law5 exercise the degenerate
   aggregate broadcast (D `[1.0]` → uniform over declared cardinality,
   single-column A → column-stochastic expansion). Template-contract test
   accepts a sidecar clone named `COGANT`.
2. `68ce23e` — fix(runner): `FailFastExit` aborts after persisting the
   partial manifest + summary; 1800s timeouts on capture steps; incomplete
   git clones repaired; `export-gnn` label aligned.
3. `c14e1d9` — fix(tools): math-adjacency and coverage-table gates fail
   loud when their inputs are unavailable.
4. (this pass) — TODO.md reconciliation (cog-p1-02 closed, dated pass
   section, open items ticked), REVIEW_LOG (this file), README
   `audit_stage_list` invocation corrected to the inner-package env form
   matching CI, METRICS.yaml + manuscript/figure/report artifacts
   regenerated against commit-bound HEAD.

## Phase 3 — Verification

- Full package suite: **9612 passed / 0 failed / 47 skipped**, coverage
  94.61% against the 89% line gate (12m09s).
- Root tools lane (`uv run pytest tests/` at the project root, minus the
  three tests that require the inner package env — those pass 15/15 under
  `uv run --directory cogant`): the template-contract test is fixed; 10
  remaining failures are pre-existing at HEAD (verified by stash) and
  environmental: the root compatibility-shell venv intentionally installs
  only `pyyaml`+`pytest`, while four test files invoke audit tools that
  import `cogant.*` internals (pydantic). CI never runs this lane — every
  audit gate runs via `uv run --directory cogant` (`.github/workflows/ci.yml`),
  which is green.
- `./run_all.sh --dry-run` → exit 0 (24 targets); batch dashboard
  regeneration → exit 0.
- Manuscript generator re-run → publication readiness `verdict=ready`,
  blockers=0; visual QA 18/18.
- Release gate (`tools/release_gate.py`) lane matrix, root venv
  (Python 3.14.6): package-tests **passed**, ruff **passed**, mypy
  **passed**, rust-format **passed**; rust lanes require
  `PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1` (PyO3 0.22.6 caps at 3.13) and
  then rust-check / rust-test / rust-clippy all **pass**; wheel-smoke
  **fails** only because no pydantic_core binary supports 3.14. Under the
  inner 3.12 env the wheel toolchain is supported but the gate's
  package-tests lane exceeds its 1800s cap (inner addopts add coverage +
  verbose output and the gate runs rust lanes concurrently). All failures
  are environmental (interpreter/toolchain), not code regressions: this
  pass touches no Rust, wheel, or dependency code, and the identical
  pre-pass HEAD fails the same lanes under the same root venv.

## Open / deferred

- **Root-lane environmental test failures** (10, pre-existing at HEAD):
  `tests/test_audit_stage_list.py` (4), `tests/test_audit_synthetic_surfaces.py` (2),
  `tests/test_check_metrics_fresh.py` (3), `tests/test_manuscript_figures.py` (1).
  Fix options: skip-if-`cogant.config`-unavailable markers, or run the tools
  under the inner env. Not caused by this pass; out of every configured CI gate.
- **tasks.yaml date slips** (owner/taskboard server): six `in_progress` rows
  with past end dates and `cog-p4-01` carrying a future `start` while active.
- **Notebook stubs** (`cogant/docs/notebooks/*.md`, 12 pages) — unchanged,
  deliberate placeholders.
- **cog-p1-01** schema-version migration mechanism remains partial (field
  exists; no version-to-version migration code).
- **Pre-existing ruff I001/SIM115 in `tools/run_all_runner.py`** — outside
  the configured lint scope (CI lints `py/cogant/ tests/` in the inner
  package only); left untouched.
- **Release gate wheel-smoke under Python 3.14** — needs a PyO3/pydantic
  toolchain that supports 3.14, or running the gate from a ≤3.13
  interpreter with a package-tests timeout budget that accommodates the
  inner env's coverage addopts. Environmental; out of scope for this pass.
