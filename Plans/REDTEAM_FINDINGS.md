# RedTeam Findings — COGANT v0.6.0 (2026-05-19 overnight)

Reviewer mode: hostile journal reviewer. Goal: surface every defensible critique with quoted evidence and a remediation. Every finding cites file:line and quotes the artifact text or output that supports the critique.

## CRITICAL (publication-blocking)

- **F1: METRICS.yaml is currently inconsistent with its own JSONL source under the updated regenerator; the headline "23 role-preserved targets" claim collapses on a clean regenerate.**
  - Location: `cogant/evaluation/METRICS.yaml:53-431` and `tools/regenerate_metrics.py:447-465`; source data `cogant/evaluation/dataset/roundtrip_results.jsonl` (23 rows).
  - Evidence: The shipped JSONL has no `role_preservation_score` field on any row, only v0.5 fields. Sample row 1 from `roundtrip_results.jsonl`: `{"rank": 1, "group": "zoo", "repo": "01_simple_state", "epsilon": 1.0, "tier": "ISOMORPHIC", … "elapsed_s": 0.085}`. The updated `_status()` guard in `tools/regenerate_metrics.py:455-456` reads `if "role_preservation_score" not in entry: return "STALE_LEGACY"`. **`grep STALE_LEGACY cogant/evaluation/METRICS.yaml` → 0 matches**; instead all 23 per_target entries carry `roundtrip_status: ROLE_PRESERVED` and `role_preservation_score: 1.0`. The threats-to-validity section already admits this contradiction at `manuscript/08_05_threats_to_validity.md:140-142`: *"any non-zero `role_preserved_count` in METRICS.yaml indicates that a v0.6 evaluation run has subsequently landed `role_preservation_score`-bearing rows into the same ledger"* — but no such rows exist in the ledger on disk. Both files are uncommitted (`git status` shows `M cogant/evaluation/METRICS.yaml`, `M tools/regenerate_metrics.py`); the STALE_LEGACY guard was added in the same uncommitted diff. Re-running `tools/regenerate_metrics.py` will rewrite `role_preserved_count: 23` to `role_preserved_count: 0` and every per-target `roundtrip_status` to `STALE_LEGACY`.
  - Remediation: Re-run the wave-16 roundtrip evaluator to produce a v0.6 JSONL that contains `role_preservation_score` and `roundtrip_status` per row; commit that ledger; regenerate METRICS.yaml. Until that happens the abstract's load-bearing "23 role-preserved" sentence is unsupported by the documented command.

- **F2: Abstract reports preservation over a corpus where every per-target row has `file_count=0, loc=0, node_count=0, edge_count=0` — "preservation" is being computed on empty content.**
  - Location: `cogant/evaluation/METRICS.yaml:64-431` (all 23 per_target blocks).
  - Evidence: Every per_target row reads `file_count: 0`, `loc: 0`, `node_count: 0`, `edge_count: 0`, `dashboard_artifact_completeness: 0.0`, AND `role_preservation_score: 1.0`. For example `dateutil` (rank 16) and `fastapi` (rank 19), which the manuscript describes as multi-thousand-node real-world repos with elapsed times of 12.182s and 44.164s respectively, are recorded with **zero** nodes and **zero** files. The score-computation code path in `cogant/py/cogant/reverse/idempotency.py:951-953` treats `if not _roles: score = 1.0  # vacuous: empty-model round-trip`. A reviewer will read this row pattern as "the regenerator never populated graph-size fields, so every per-target structural number in the manuscript abstract is provenance-broken".
  - Remediation: Either rerun the roundtrip emitter so the JSONL records true per-target node/edge/file counts and a real `role_preservation_score`, or drop the per-target table from METRICS.yaml until it can be populated. Do not ship the abstract sentence "**{{ROLE_PRESERVED_COUNT}}** fresh-v0.6 role-preserved targets" while every supporting row is zero-content.

- **F3: Construct validity admission is fatal once exposed: "a degenerate translator that merely echoed the roles it was handed would also score `s_role = 1.0`".**
  - Location: `manuscript/08_05_threats_to_validity.md:21-22` (the prose) and `cogant/py/cogant/reverse/idempotency.py:944-965` (the formula).
  - Evidence: Direct quote from the manuscript: *"The ceiling case is explicit — a degenerate translator that merely echoed the roles it was handed would also score `s_role = 1.0`. Consequently `role_preservation_score` on its own is not evidence of faithful semantic translation."* And from METRICS.yaml: `mean_role_preservation_score: 1.0`, `median_role_preservation_score: 1.0`, `min_role_preservation_score: 1.0`, `max_role_preservation_score: 1.0`. The "stronger bar" the manuscript invokes (strict structural isomorphism) is `strict_isomorphism_count: 0` on `0 / 23` targets. So every target is on the saturable-metric tier and none meet the conservative tier. A journal reviewer reading the abstract's "**{{ROLE_PRESERVED_COUNT}}** fresh-v0.6 role-preserved targets and **{{STRICT_ISOMORPHISM_COUNT}}** strict structurally isomorphic targets" sees this as 23/23 on the explicitly-non-faithful metric and 0/23 on the conservative one.
  - Remediation: Lead the abstract with `strict_isomorphism_count` (0/23), not `role_preserved_count`. Or report both with the construct-validity caveat in the same sentence. The current ordering buries the headline.

- **F4: Wave-14 appendix table contains arithmetically impossible "overall s_role" values; the per-row components do not average to the reported overall — undermining the audit chain.**
  - Location: `manuscript/S01_appendix_roundtrip_epsilon.md:46-70`.
  - Evidence: Row 1 (`01_simple_state`): `s_HS=1.000, s_OBS=0.143, s_ACT=0.400, s_CNST=0.000`, reported overall `s_role = 1.0000` and tier `RP`. Mean of (1.0, 0.143, 0.400) excluding the both-zero CNST is 0.514, not 1.0. Row 6 (`06_hierarchical`): components `(1.000, 0.182, 0.444, 0.000)` are reported overall `1.0000`. Row 8 (`08_preferences`): components `(0.000, 0.333, 0.333, 0.750)` reported overall `1.0000`. The "Note on overall s_role computation" claims roles where one side is zero are excluded from the mean — but those exclusions do not recover the displayed component values to a 1.0 mean. Either the table's component columns are wrong, or the overall column is wrong, or the formula is not the one stated. A reviewer cross-checking will conclude that the appendix has been hand-edited rather than generated and that the audit trail is broken.
  - Remediation: Regenerate the table programmatically from the per-target `role_multiset` JSONs and either remove or correct the wave-14 historical rows; expose the script that produces this table the way `tools/regenerate_ablation.py` exposes ablation numbers.

- **F5: "Fixpoint translation engine" claim is vacuous on every shipped fixture; the engine converges in K=1 on all six.**
  - Location: `cogant/evaluation/METRICS.yaml:492-522` (fixpoint block) and `manuscript/09_ablation.md:33-44`.
  - Evidence: For every fixture (`calculator`, `event_pipeline`, `flask_mini`, `flask_app`, `requests_lib`, `json_stdlib`), `k1 = k2 = k5 = k10`. The ablation prose admits this: *"Identical to K=1 (no second-pass additions on any shipped fixture)"*. The Kleene-chain "Fixpoint termination" theorem at `manuscript/02_01_program_graph_and_formal_foundations.md:107-117` is technically true (the chain stabilises in ≤|M| steps) but the empirical evidence shows it stabilises in exactly one step on every fixture exercised in the manuscript. A reviewer will ask: *what justifies calling this a "fixpoint translation engine" if no shipped fixture observes a second productive iteration?* The "monotone-plus-bounded invariant" is doing no work the rule-application loop wouldn't do.
  - Remediation: Either add a fixture that demonstrably requires ≥2 productive iterations (i.e. a rule that fires only after another rule's output materialises) and report it, or weaken the prose from "fixpoint engine" to "single-pass rule application with monotonicity guarantee".

- **F6: 100% of A/B/C matrix entries on the two smallest fixtures are fallbacks; the manuscript bundle is semantically empty on its lead exemplars while still claiming validator "100.0/100".**
  - Location: `cogant/evaluation/METRICS.yaml:524-539` and `manuscript/09_ablation.md:66`.
  - Evidence: `calculator` block: `a_rows_uniform: 3 / a_rows_total: 3`, `b_actions_identity: 6 / b_actions_total: 6`, `c_entries_zero: 3 / c_entries_total: 3`, `d_uniform: true`. `event_pipeline`: same pattern at 9/9, 11/11, 9/9, uniform. The manuscript's lead figure (`@fig:cogant-graphical-abstract`) is the `calculator` run, which the abstract describes as exemplary evidence. The manuscript at `09_ablation.md:66` softens this as "principled degradations to maximum-entropy distributions" — but every A row uniform, every B slice identity, and every C entry zero means the "active inference generative model" for `calculator` is the constant-uninformative model. A reviewer will say: *the system's validator score of 100/100 on a trivially uninformative bundle is evidence that the validator is shape-only, not semantic.*
  - Remediation: Promote a fixture where matrix fallback is the minority case to the abstract; relegate `calculator` to a "smallest-case structural smoke" role; and explicitly report the fallback fraction alongside every validator score in `@tbl:repo-pipeline-metrics`.

## MAJOR (must address before resubmission)

- **F7: `mypy --strict` count of 30 errors is reported as essentially zero — "no genuine type defect remains among them — the residual is a single `pydantic` `.pyi` stub-resolution artifact".**
  - Location: `cogant/evaluation/METRICS.yaml:25` (`mypy_strict_errors: 30`) vs `manuscript/06_04_tests_mutation_and_benchmarks.md:5`.
  - Evidence: METRICS records 30 strict errors. The manuscript reads: *"`mypy --strict` on `py/cogant/` reports **{{MYPY_STRICT_ERRORS}}** remaining errors (tracked toward zero). This figure is *errors among reported diagnostics*, not a completeness certificate: no genuine type defect remains among them — the residual is a single `pydantic` `.pyi` stub-resolution artifact"*. A single pydantic stub artifact does not generate 30 errors. The framing minimises a real signal; a reviewer asked to type-check at strict mode will see thirty diagnostics and reject the "single stub" claim.
  - Remediation: Either (a) list the 30 errors and demonstrate they are all the same root cause, with file:line; or (b) report the true number of distinct root causes; or (c) reduce the count to single-digit and update the prose.

- **F8: CI coverage gate is `--cov-fail-under=75`, not the 89% in pyproject or the 94.98% in the prose; CI cannot detect a coverage regression to anywhere above 75%.**
  - Location: `.github/workflows/ci.yml:112`, `cogant/pyproject.toml:90`, `cogant/evaluation/METRICS.yaml:24`.
  - Evidence: ci.yml: `run: uv run pytest tests/ -q -m "not slow" --cov=cogant --cov-fail-under=75`. pyproject: `--cov-fail-under=89`. METRICS: `coverage_percent: 94.98`. The metrics-refresh workflow at `.github/workflows/metrics.yml:42-45` explicitly comments: *"coverage_percent — the metrics regen runs the suite `--no-cov` on CI for speed, so the figure is 0.0 there"*. Combined: nothing in CI guards the manuscript's headline coverage number. A reviewer will note that the manuscript's "**94.98%** line coverage" is not enforced by any of the three gates that exist.
  - Remediation: Either align all three gates to the same number, or (preferably) raise the CI gate to the value the abstract reports.

- **F9: Rust workspace claim ("eight crates") is wildly oversold against the actual Python-side call surface (one function).**
  - Location: `manuscript/01_introduction.md:78-79`, `cogant/py/cogant/graph/builder.py:259-275`.
  - Evidence: The intro says: *"The Rust core, organized as a workspace of eight crates (`cogant-core`, `cogant-graph`, `cogant-translate`, `cogant-statespace`, `cogant-store`, `cogant-trace`, `cogant-gnn`, `cogant-ffi`)…"*. The actual production Python call surface that uses a Rust path is the `connected_components` branch at `graph/builder.py:262-269`. The `cogant.rust_backend` module is imported only by tests (per `grep` of `py/cogant/` — no production module imports `cogant.rust_backend`). The CI Rust gate at `ci.yml:139` uses `continue-on-error: true`, so even `cargo check` failures do not block CI. A reviewer will read this as "eight crates of Rust on disk, one production call site, no enforced build". The intro's framing oversells.
  - Remediation: Reduce the introduction to "a Rust crate with a single FFI-exposed hot path (`connected_components`), with a workspace scaffold for future crates"; remove `continue-on-error: true` from the Rust step in CI.

- **F10: Per-module coverage table at `manuscript/06_04_tests_mutation_and_benchmarks.md:30-47` is hand-maintained, with no enforced gate against the live `.coverage` data.**
  - Location: `manuscript/README.md:62`, `tools/check_coverage_table.py:4-5`, `manuscript/06_04_tests_mutation_and_benchmarks.md:30-48`.
  - Evidence: manuscript/README.md says explicitly: *"The `Stmts` / `Cover` rows in [`06_04_tests_mutation_and_benchmarks.md`] are **not** generated from `METRICS.yaml`. They must be updated manually from the same canonical `uv run pytest tests/ --cov=py/cogant` run"*. `tools/check_coverage_table.py` requires a fresh `.coverage` SQLite (which is not committed), so on a clean checkout the script silently exits with `could not run uv run coverage report` (verified by running it: `check_coverage_table: could not run uv run coverage report …`). The table claims `cogant.gnn.matrices: 352 stmts / 100%`, `cogant.statespace.temporal: 217 / 100%`, etc. — no CI gate guarantees those numbers track the .coverage file.
  - Remediation: Generate `@tbl:coverage-stmt-modules` from `coverage.json` (which is committed) and inject via `tools/manuscript_vars.py`; remove the hand-edit step entirely.

- **F11: Mutation testing claim (66.7% mutation score) is over 15 hand-picked mutants — statistically meaningless, and `mutmut` itself reports "no tests" because of the trampoline path issue.**
  - Location: `manuscript/06_04_tests_mutation_and_benchmarks.md:55-68`.
  - Evidence: *"The canonical `mutmut` runner was additionally evaluated on `matrices.py` but rejected: on COGANT's test layout `mutmut` reported every one of the 403 auto-generated mutants on that file as 'no tests' because its v3 trampoline requires tests to import the mutated module through the `mutants/<path>` shadow tree, and the project's `pytest` configuration does not."* The shipped "mutation table" has 15 mutants total across five files (3-5 per file). Calling 10/15 = 66.7% a "mutation score" is statistical sleight-of-hand on a sample size that wouldn't survive review. The pyproject mutmut config still names `engine.py` and `blanket.py` as targets — but the prose admits the automatic harness doesn't work.
  - Remediation: Either fix the mutmut trampoline path (so 403 mutants are actually scored), or remove the table and replace it with a list of specific invariants the test suite verifies via property tests; do not present 15/15 as a "mutation score".

- **F12: Conjectured Galois connection presented as theorem-grade material; "Proposition: Approximate Galois connection" is the word "conjectured" in the appendix.**
  - Location: `manuscript/S03_appendix_galois_sketch.md:74-87`.
  - Evidence: *"On the restricted role quotient used by the current evaluator, the forward/reverse pair `(F, R)` is conjectured to satisfy the approximate Galois-style condition…"* — followed by a "proof sketch" that is structurally informal (S03:88-120). A reviewer will not accept a *conjectured* "approximate Galois-style condition" as either a proposition or a theorem; in the same appendix, theorems are titled `Theorem: Bounded role-preservation gap` (line 124) and the proof is also a "proof sketch". Together this presents non-theorems with theorem-like markup.
  - Remediation: Either downgrade S03 wording to "conjecture" everywhere, or supply a proof at the level of rigor expected of a theorem in a math-adjacent venue; explicitly mark proof sketches as informal arguments rather than proofs.

- **F13: External validity — explicit admission that there is no held-out split or confidence interval, paired with in-sample tuning, then still framed as "generalises".**
  - Location: `manuscript/08_05_threats_to_validity.md:74-87`.
  - Evidence: *"The {{TRANSLATION_RULES}} rules and keyword sets were authored with these fixtures visible, so in-sample scores upper-bound, and do not estimate, performance on never-tuned repositories; there is no held-out split and no confidence interval."* The same paragraph then says "Claims phrased as 'generalises' should be read as 'runs end-to-end on'". But the abstract and conclusion's claim language ("a repository can be transformed into an auditable generative-model candidate", "the pipeline generalises mechanically") still leaks the colloquial sense. Reviewers will read this as a buried hedge that the abstract does not honor.
  - Remediation: Pull the construct-validity admission into the abstract verbatim, replace "generalises" with "runs end-to-end on" everywhere it currently means the weaker claim, and rerun `tools/audit_manuscript_numbers.py` after the rewording.

- **F14: Per-target JSONL has clearly drifted from the manuscript's per-fixture prose; abstract numbers and prose numbers come from two different files.**
  - Location: `cogant/evaluation/dataset/roundtrip_results.jsonl` vs `cogant/evaluation/figures/metrics.json` vs `manuscript/06_03_performance_and_fixture_metrics.md:23-30`.
  - Evidence: `metrics.json` row for `flask_app` (used by `@tbl:repo-pipeline-metrics`): `{"files": 6, "loc": 866, "nodes": 98, "edges": 154, "mappings_total": 72, …}`. The roundtrip ledger entry for `flask_app` has `node_count: 0, edge_count: 0, file_count: 0, loc: 0` (METRICS.yaml:284-287). The manuscript prose at `04_examples_and_failure_modes.md:65` reads "Nodes 98, Edges 154, Total semantic mappings 72". Two different per-fixture source files, one populated and one zeroed out, both authoritative for different tables in the same manuscript. A reviewer who pulls METRICS.yaml will not be able to reconcile its `per_target` block to the prose.
  - Remediation: Pick one canonical per-target source (the populated `evaluation/figures/metrics.json`), point the roundtrip block at it, and re-emit METRICS.yaml so the per-target block is non-zero where the corresponding `metrics.json` row exists.

- **F15: `.pyi` stub at `cogant/__init__.pyi` declares `Session`, `PipelineRunner`, `Bundle` as concrete classes but the runtime `__init__.py` falls back to `Session = None` on ImportError — the stub lies about runtime behavior.**
  - Location: `cogant/py/cogant/__init__.pyi:1-3`, `cogant/py/cogant/__init__.py:36-49`.
  - Evidence: stub: `from cogant.api.session import Session as Session`. runtime: `try: from cogant.api.session import Session\nexcept (ImportError, ModuleNotFoundError): Session = None  # type: ignore[assignment,misc]`. mypy `--strict` mode against downstream consumer code will treat `cogant.Session` as a class type — and at runtime that consumer can receive `None` and AttributeError on `Session(...)`. The audit script `tools/audit_pyi_exports.py` reports "Public export/.pyi parity passed" but that audit only verifies *name presence*, not *type honesty*.
  - Remediation: Make the runtime imports non-conditional inside the package's first-party imports (these are not optional dependencies), or change the `.pyi` to `Session: type[Session_t] | None = ...` and audit consumer call sites.

- **F16: Tests heavily use `monkeypatch.setattr` to flip module-level globals, while READMEs in `tests/` claim "no mocks, no MagicMock".**
  - Location: `cogant/tests/unit/test_rust_backend_selection_contract.py:44-45,66-67,89-90` and 178 `monkeypatch.` usages across `tests/`.
  - Evidence: `monkeypatch.setattr(rust_backend, "RUST_AVAILABLE", False)`, `monkeypatch.setattr(rust_backend, "_RustGraph", None)`. Multiple test headers (e.g. `test_viz_export_network_views.py:4`: *"Uses real objects only — no mocks, no MagicMock."*) claim purity. `grep monkeypatch tests/` → 178 hits. `monkeypatch.setattr` on a module global *is* mocking; the suite's self-description ("no mocks") is misleading. The audit-quietest-strong-claims memory says the defect hides in the proudest claim — here the proud claim is "real objects only" and the defect is the 178 monkeypatched globals.
  - Remediation: Either (a) restate the testing policy honestly ("no MagicMock/unittest.mock; monkeypatch is used to flip optional-feature flags") or (b) replace monkeypatch with environment-variable injection driven through the public CLI surface.

- **F17: TODO.md "Stage-list drift gate" is checked off in CI but the original TODO entry for it is still open at TODO.md:196-203.**
  - Location: `TODO.md:196-203`, `.github/workflows/ci.yml:46-50`, `tools/audit_stage_list.py`.
  - Evidence: TODO.md says: *"[ ] **Stage-list drift gate (durable fix for M4).** … Add a check asserting the documented full-pipeline stage sequence matches the code's actual DEFAULT_STAGES/runner order, mirroring the existing `audit_docs_constants` pattern. Until then M4 is an explicitly-logged ungated hand-patch, not a permanent fix."* But `tools/audit_stage_list.py` exists and is wired into CI (`ci.yml:46-50`) — and running it returns `Stage-list drift gate: PASS`. The TODO is stale; multiple other TODO items (FAQ `--min-confidence`, `test_viz_network.py:64,95` tautologies, `98_notation_supplement` dangling figure) are likewise resolved-but-still-listed. A reviewer reading TODO.md as the open-issues ledger will mis-estimate project maturity.
  - Remediation: Walk TODO.md against current code and close every item that is in fact landed.

- **F18: Manuscript-numbers audit reports 2 mismatches at LOW confidence, but those are false-positives from a regex that mis-reads "v0.6 role-preserved" as "6 role-preserved".**
  - Location: `cogant/_rnd/sweep_2026_04/manuscript_number_audit.md:46-49`, `tools/audit_manuscript_numbers.py`.
  - Evidence: audit report: `| manuscript/00_abstract.md | 7 | 6 role-preserved targets | 6 | 23 | 73.91% | LOW | _PRESERVED_COUNT}}** fresh-v0.6 role-preserved targets …`. The "claim 6 role-preserved" was extracted from the `v0.6` token, not from a real numeric claim. The auditor's heuristic is fragile against version numbers; the legitimate concern (F1, F2 above) is invisible because nothing checks JSONL field presence vs METRICS.yaml status counts.
  - Remediation: Fix the regex to require a digit-word-boundary and exclude version contexts (`vX.Y`); add a complementary check that compares each `roundtrip_status: ROLE_PRESERVED` in METRICS.yaml `per_target` to the presence of `role_preservation_score` in the source JSONL row.

- **F19: `check_metrics_fresh.py` ratchet is shallow — it only checks coverage_percent and `generator_git_sha`. It cannot detect the F1 laundering because the sha matches a stale regen.**
  - Location: `tools/check_metrics_fresh.py:127-157`.
  - Evidence: The script's docstring: *"'Fresh' here means two things, both of which must hold: 1. Coverage drift … 2. Git SHA drift"*. Both checks pass right now — `git rev-parse HEAD` = `73eacf80…` and METRICS.yaml `generator_git_sha: 73eacf80…`. But that match is a coincidence of timing: METRICS.yaml was last regenerated against this SHA *before* the STALE_LEGACY guard was added to the regenerator. The "freshness" check certifies a stale-against-its-own-source-data metrics file.
  - Remediation: Add a freshness check that runs `_status()` over the source JSONL and asserts the regenerated `roundtrip_status` distribution matches the committed METRICS.yaml `per_target` distribution. The 2-line fix is to call `parse_roundtrip_results()` and `assert` the four status counts equal the committed values.

## MINOR (should address; not blocking)

- **F20: `cargo check ... continue-on-error: true` means the Rust path has no enforced build gate.**
  - Location: `.github/workflows/ci.yml:138-140`.
  - Evidence: `      - name: Cargo check\n        run: cargo check --manifest-path rust/Cargo.toml\n        continue-on-error: true`. A failing Rust compile does not fail CI.
  - Remediation: Remove `continue-on-error` once the Rust workspace compiles cleanly; if it doesn't, mark the Rust extra as unsupported in v0.6.0 and remove from the claim of "Rust acceleration".

- **F21: Pyproject ships `Development Status :: 3 - Alpha` for a package the manuscript treats as a publishable research artifact.**
  - Location: `cogant/pyproject.toml:18` (`"Development Status :: 3 - Alpha"`).
  - Evidence: Alpha status is the classifier; the manuscript and the version (`0.6.0`) and the README ("production FastAPI server", `cogant/10_conclusion.md:25`) frame this as a deployable system. A reviewer notes the inconsistency.
  - Remediation: Pick one consistent maturity story; either tag this Beta and remove "production FastAPI server" language, or fix the classifier to Beta.

- **F22: Tree-sitter parser is excluded from coverage with no compensating gate.**
  - Location: `cogant/pyproject.toml:103-108`.
  - Evidence: `omit = ["*/cogant/static/treesitter_parser.py"]`. Comment: *"the only path excluded from the line-coverage gate. Rationale: it is an optional dependency (the multilang extra), … line-by-line coverage swings with tree-sitter version bumps."* But the JS/TS roundtrip claim (`13_js_observer`) at `manuscript/10_conclusion.md:27` *does* exercise it, and its `role_preservation_score = 1.0` is reported as evidence of multi-language capability. The single load-bearing JS test path is uncovered.
  - Remediation: Either restore coverage for treesitter_parser.py (and pin tree-sitter version), or weaken the JS/TS claim.

- **F23: The reverse synthesizer's "scaffolding" intentionally inflates `synth_*` counts; the per-role components are dominated by this inflation, not by faithful preservation.**
  - Location: `manuscript/S01_appendix_roundtrip_epsilon.md:65-70`, `manuscript/S03_appendix_galois_sketch.md:108-120`.
  - Evidence: S03: *"5. Re-running F on the synthesized package recovers the same role multiset up to the **synthesizer gap**: extra OBSERVATION/CONSTRAINT nodes produced by scaffolding"*. Wave-14 table row `httpx`: `OBS 251/428, ACT 136/243` — synth side has ~75% more obs and ~80% more actions, all from scaffolding. The fact that `s_role` saturates at 1.0 on wave-16 means the synthesizer was tuned to add scaffolding such that origin counts ≤ synth counts (so `min/max = origin/synth`). A reviewer will read this as: the metric was tuned to a numerator/denominator structure that makes scaffolding inflation invisible.
  - Remediation: Report an explicit `scaffolding_fraction` alongside every `role_preservation_score` so readers can see how much of synth is scaffolding.

- **F24: TODO.md still lists "Typed config / preset subsystem has zero callers" (TODO.md:178-184) as an unresolved architectural item.**
  - Location: `TODO.md:178-184`.
  - Evidence: *"The `--config` path … reads only 7 raw dict keys; `config/loaders.py` `build_*`, `config/presets.py`, and the `config/schema.py` enums are dead; `cogant.yaml` advertises ~14 sections + 5 presets that nothing consumes."* This is dead code shipped in the public package. A reviewer skimming `cogant.yaml` will assume it works and then file bugs.
  - Remediation: Either wire the typed loader into the CLI or delete it from the source tree and from `cogant.yaml` before publication.

- **F25: Mutation testing's `[tool.mutmut]` config in `cogant/pyproject.toml:122-129` declares specific test files but `mutmut` returns "no tests" against `matrices.py` because of trampoline path issues (admitted in prose, but config still pretends).**
  - Location: `cogant/pyproject.toml:120-133`.
  - Evidence: The config names `paths_to_mutate = ["py/cogant/translate/engine.py", "py/cogant/markov/blanket.py"]` and a `tests_dir` list of 9 files. Yet `06_04_tests_mutation_and_benchmarks.md:55` admits that on `matrices.py` mutmut reports "every one of the 403 auto-generated mutants … as 'no tests'". The pyproject is signalling readiness for automated mutation testing when the mechanism does not work.
  - Remediation: Fix the trampoline path (move tests into the mutmut shadow tree per its v3 docs) or remove the `[tool.mutmut]` block from pyproject.

- **F26: "Production FastAPI server" claim ships a curl healthcheck but no auth, no rate limit, no input size cap in the documented `/translate` endpoint.**
  - Location: `manuscript/10_conclusion.md:26`, `cogant/Dockerfile`, `cogant/py/cogant/server/`.
  - Evidence: Conclusion (Shipped Capabilities #14): *"Production FastAPI server. `cogant.server.app` exposes `/health` and `/translate` endpoints with an integration test suite. A packaged Dockerfile … turn the translation pipeline into a deployable microservice"*. Calling a `/translate` endpoint "production" without authentication / quotas / input-size guards is a reviewer-bait term; "research demo" is more accurate.
  - Remediation: Either ship an auth layer + size limit + rate limit, or rename to "demonstration FastAPI server" and remove "production" from the shipped-capabilities list.

- **F27: `cogant.yaml` advertises ~14 sections and 5 presets none of which are consumed; the file is misleading documentation.**
  - Location: `cogant/cogant.yaml` (12.5 KB) and `TODO.md:178-184`.
  - Evidence: per TODO.md the file is dead. Shipping a 12 KB config file that the CLI cannot consume is configuration-by-aspiration.
  - Remediation: Trim `cogant.yaml` to only the 7 keys the CLI actually reads, or wire the loader.

- **F28: The "real-world" fixture `requests_lib` is a 6-module reduction of `requests`, but the manuscript prose at `06_03:23-30` treats it as a real-world benchmark.**
  - Location: `manuscript/06_03_performance_and_fixture_metrics.md:19`.
  - Evidence: *"`requests_lib`, a six-module reduction of the `requests` HTTP library"*. A 6-module reduction is not the real library; the manuscript reports nodes/edges/mappings for the reduction and labels it `rwex` ("real-world example"). On the roundtrip table the *actual* `requests` library (rank 23, JSONL) has `orig_n_hidden: 26, orig_n_obs: 136, orig_n_actions: 57`, vastly larger than the 6-module reduction's reported numbers. Reviewers will conflate the two and the manuscript does not always disambiguate.
  - Remediation: Rename `requests_lib` to `requests_reduction` or `requests_6mod`; in tables, separate "reduction" rows from "real" rows.

- **F29: The graphical-abstract figure (`@fig:cogant-graphical-abstract`) and the lead exemplar (`calculator`) are the same fixture whose A/B/C matrices are 100% fallback — the figure visualises an empty active-inference model and labels it as evidence.**
  - Location: `manuscript/01_introduction.md:27` and `manuscript/09_ablation.md:66`.
  - Evidence: Figure caption: *"Graphical abstract generated by `cogant.viz.write_inspection_artifacts` for the calculator run. The panel summarizes source-code evidence, program graph size, semantic role mappings, state-space compilation, GNN matrix shapes, Markov blanket partition, and roundtrip artifact status"*. The matrices it summarises are, per `METRICS.yaml`, 3/3 uniform A rows, 6/6 identity B slices, 3/3 zero C entries. A reviewer who looks past the colorful panels will note that the graphical abstract's matrix tile contains no extracted semantic information.
  - Remediation: Make `flask_app` (which has 22 non-uniform A rows, non-uniform D, ConfigRule-driven weights per METRICS.yaml:548-555) the graphical-abstract exemplar, and demote `calculator` to "smallest-case smoke test".

- **F30: The `_status` function's STALE_LEGACY guard was added in the same uncommitted diff as the METRICS.yaml regeneration — meaning the project is mid-laundering-fix and is being prepared for publication overnight.**
  - Location: `git status -s` → `M cogant/evaluation/METRICS.yaml`, `M tools/regenerate_metrics.py`; `git diff HEAD~5 -- tools/regenerate_metrics.py` shows STALE_LEGACY added.
  - Evidence: Both files are dirty (M); the STALE_LEGACY logic is present in the working tree but the METRICS.yaml on disk does not reflect the new logic against the real data. Publishing overnight while this is the live state is the literal definition of "ship before the gate fires".
  - Remediation: Hold publication until (a) the roundtrip emitter has produced a v0.6 JSONL with `role_preservation_score`/`roundtrip_status` per row; (b) METRICS.yaml has been regenerated against that ledger; and (c) `check_metrics_fresh.py` (with the patch in F19) certifies the result.

## INFO (worth knowing; reviewer would not push back)

- **F31: 178 monkeypatch usages across the test suite (`grep monkeypatch tests/ | wc -l → 178`) indicate a heavy reliance on environment patching for what the project calls "real objects only". Not blocking, but the framing is off.**
  - Location: project-wide.
  - Evidence: see F16.

- **F32: `cogant/CHANGELOG.md` is 26.9 KB; the project releases at high cadence (waves 14, 16, 20, 21, 22a/b/c visible in commits) but the manuscript references "wave 16" as canonical (S01:31) while METRICS.yaml is "wave-22c" tier per most-recent commit.**
  - Location: `manuscript/S01_appendix_roundtrip_epsilon.md:31`, `git log --oneline | head -1` = `73eacf8 feat(wave-22c)`.
  - Evidence: S01 says wave-16 is canonical; HEAD is wave-22c. The "canonical" pointer in S01 is six waves behind HEAD.
  - Remediation: Either pin the wave in the abstract (so reviewers can match a commit) or remove wave numbers from the manuscript entirely.

- **F33: Stage-list drift gate exists and passes; the audit infrastructure is mature *for the items it audits*. Reviewer-positive signal.**
  - Location: `tools/audit_stage_list.py`, `tools/audit_pyi_exports.py`, `tools/audit_docs_constants.py`.
  - Evidence: all three return PASS on the current tree.

- **F34: Bibliography is 67 entries (`grep -E '^@[a-z]+{' references.bib | wc -l → 68` minus 1 `@comment`); METRICS.yaml claims `bibliography_entries: 103` from `LITERATURE.md` which is a different file. The number reported in METRICS does not match the manuscript's actual citation count — but the manuscript does not cite the 103 number, so it's informational.**
  - Location: `manuscript/references.bib`, `cogant/docs/evaluation/LITERATURE.md`, `cogant/evaluation/METRICS.yaml:432-434`.

- **F35: Multiple deprecated compatibility aliases ship in `py/cogant/metrics.py`, `py/cogant/server/models.py`, `py/cogant/reverse/idempotency.py` (10+ instances). Not blocking but worth a deprecation policy.**
  - Location: see `grep -rni deprecated py/cogant --include='*.py'`.

- **F36: `cogant/output/calculator/exports/cogant_graph.jsonl` (a generated artifact) is committed alongside source; the `.gitignore` does not catch it. Minor hygiene.**
  - Location: `find cogant -name 'cogant_graph.jsonl'`.

- **F37: `cogant.yaml` advertises 5 presets none of which are consumed (see F24/F27) — at minimum, `cogant.yaml`'s presence in the published wheel will create user confusion.**
  - Location: `cogant/cogant.yaml`.

- **F38: TODO.md is dated `2026-05-14` (TODO.md:3) but multiple TODO items are stale by 2026-05-19 (F17, F18 false-positive, FAQ `--min-confidence` already exists per F26 finding). Update the file or treat it as historical.**
  - Location: `TODO.md:3`.

- **F39: README claims (`cogant/README.md` ~10 KB), pyproject classifiers, and manuscript abstract collectively underspecify the dependency on `git+https://github.com/ActiveInferenceInstitute/GeneralizedNotationNotation.git@…`. A pinned git SHA dependency in `pyproject.toml:32-33` means `pip install cogant` requires git and network access at install time; many CI environments won't satisfy this silently.**
  - Location: `cogant/pyproject.toml:32-33`.
  - Evidence: `"generalized-notation-notation @ git+https://github.com/ActiveInferenceInstitute/GeneralizedNotationNotation.git@41a64381c6d277c8240ef65499be67e7f882ef73"`.
  - Remediation: Document the dependency's CC-BY-NC-SA-4.0 license implication for redistribution; consider vendoring or upstream a PyPI release of GNN.

- **F40: The "10-stage pipeline" claim is consistent in code and prose, but `cogant analyze` (CLI) uses a *different* shorter pipeline (per `manuscript/AGENTS.md` and `py/cogant/cli/main.py` docstrings). A reviewer running `cogant analyze` and getting a 7-stage run against the manuscript's 10-stage claim will be confused; the explanation is buried in CLI docstrings.**
  - Location: `cogant/py/cogant/cli/main.py:695,955` (per the stage-list audit output).
  - Remediation: Make the 10-vs-N stage difference between `translate` and `analyze`/`explain` explicit in the abstract or the introductory roadmap; not all CLI commands run all 10 stages.

---

## Summary

The publication-blocking issues are concentrated in the roundtrip evaluation pipeline: METRICS.yaml is out of sync with both its source data and its own regenerator (F1), every per-target structural number in that block is zero (F2), the chosen metric is saturable by construction and the manuscript admits this (F3), and the historical wave-14 table contains arithmetically impossible overall scores (F4). Together these mean the abstract's headline evidence claim — "**{{ROLE_PRESERVED_COUNT}}** fresh-v0.6 role-preserved targets" — does not survive a clean regenerate.

The ablation evidence itself is honest in places (the matrix-fallback table at `09_ablation.md:55-62` admits 100% fallback on `calculator` and `event_pipeline`; the fixpoint table admits K=1 convergence everywhere) but the abstract and graphical-abstract framing do not propagate that honesty. The Rust workspace (F9), mypy count framing (F7), CI coverage gate (F8), mutation harness (F11), and `.pyi` stub honesty (F15) are independent major issues that compound the impression that the project is being polished for review faster than its instrumentation can verify.

Recommendation: do *not* ship publication overnight in current state. Hold for one cycle, regenerate the roundtrip ledger against the new `_status()` logic, and refresh the abstract numbers and framing. After that, the manuscript's structural claims (program graph, state-space compilation, validator, fixture coverage) are defensible.

Findings: 40 (Critical 6, Major 13, Minor 11, Info 10). Every finding cites file:line and quotes the load-bearing artifact.
