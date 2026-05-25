# COGANT — Overnight Improvements (2026-05-19)

> Session: PAI Algorithm v6.4.0 E5 overnight. ISA at
> `projects_in_progress/cogant/ISA.md`. Pre-state captured in
> `Plans/PRE_STATE_2026-05-19.md`; first-principles claim audit in
> `Plans/FIRST_PRINCIPLES_AUDIT.md`; RedTeam findings in
> `Plans/REDTEAM_FINDINGS.md` (background agent).

## TL;DR

Six TODO open items were closed durably (with enforced gates, not hand
patches); a seventh (TODO #2 graph normalization) was partially closed
with its remaining sub-items honestly carried forward as follow-ups; a
critical "quietest strong claim" was surfaced (METRICS.yaml asserting
23/23 roundtrip role-preserved when the data file is pure v0.5 legacy
with all rows tagged STALE_LEGACY by the current regen guard — the
regen in this session is expected to overwrite the count to honest 0)
and the matching threats-to-validity paragraph was added.

## Closed durably (gate-enforced, not hand-patched)

| # | Item | Durable artifact | Tests | Closed at |
|---|------|------------------|-------|-----------|
| 1 | mypy strict 30 → 0 | `pyproject.toml` adds `plugins = ["pydantic.mypy"]` + `yaml` ignore | Existing mypy CI step in `.github/workflows/ci.yml`; regen records 0 in METRICS.yaml | TODO #1 |
| 2 | Stage-list drift gate | `cogant.pipeline.RUNNER_STAGES` constant + `tools/audit_stage_list.py` + `make audit-stages` + CI step | `tests/test_audit_stage_list.py` (7 tests, incl. forged-canonical negative control) | TODO #4 (was M4) |
| 3 | `--min-confidence` end-to-end | CLI flag (cli/main.py:690 / 952) → `_filter_semantic_mappings` (orchestration.py:218) | `tests/unit/test_min_confidence_filtering.py` (10 tests across threshold band + edge cases) | TODO #3 |
| 4 | Typed-config pinned-with-debt | Dual-registry asymmetry pinned by explicit assertion | `tests/unit/test_typed_config_loaders_e2e.py` (14 tests incl. `test_documented_dual_preset_surface_remains_acknowledged`) | TODO #1 (architectural) |
| 5 | Viz content probes | `tests/unit/_viz_assert.py` helper migrated into all listed files | All migrated tests (73+ pass in two run) | TODO #5 |
| 6 | Dangling figure cross-ref | Call-out paragraph in `manuscript/98_notation_supplement.md` | `tools/audit_manuscript_crossrefs.py` reports 0 dangling | TODO #6 |
| 7 | Dotted-import package-qualified keying | Two-pass refactor in `api/orchestration.py` (module nodes index dotted + bare; resolution tries target+name → target → parent packages → head) | `tests/unit/test_graph_orchestration_dotted_imports.py` (4 tests) | TODO #2 (sub) |
| 8 | Cross-project link hygiene | Verified `../../../infrastructure` resolves both pre- and post-promotion | Manual check | TODO via memory |

## Surfaced but explicitly deferred (follow-up tickets — scoped)

Each follow-up below carries a scope, falsifiable success criterion, and
intended next-session owner. The follow-up framing is per Advisor R2.

- **F1 — METRICS roundtrip-score honesty.**
  - **Scope**: in `tools/regenerate_metrics.py:parse_roundtrip_results`,
    when no row carries `role_preservation_score`, write
    `mean/median/min/max_role_preservation_score = null` and emit a
    new key `role_preservation_score_source` in METRICS.yaml that takes
    one of `{"v0.6_native", "legacy_epsilon_proxy", "mixed", "empty"}`.
  - **Success criterion**: a unit test asserts that the current
    dataset (all v0.5 legacy) produces `"legacy_epsilon_proxy"` and
    null mean-score keys; pinning the abstract injection then resolves
    to literal "null" / "N/A" in prose.
  - **Owner / when**: next regen-tool maintenance session
    (≤1 week from 2026-05-19).

- **F2 — Per-MappingKind ablation + zoo extension.**
  - **Scope**: extend `tools/regenerate_ablation.py` to emit a
    per-`MappingKind` deltas block under each rule-family, and to
    include `zoo/01_simple_state` in the measured-fixtures list (closes
    TODO #4 sub-items, S02 appendix's "currently flagged as
    unverified" disclosure).
  - **Success criterion**: `METRICS.yaml.ablation.by_mapping_kind` is
    populated; `S02_appendix_ablation.md` resolves
    `{{ABLATION_BY_MAPPING_KIND_*}}` placeholders without
    hand-reconstructed numerics; `tests/test_regenerate_ablation.py`
    asserts non-empty per-MappingKind rows AND that
    `zoo/01_simple_state` appears as a measured target with a
    realistic delta.
  - **Owner / when**: ablation-tool session (≤1 week).

- **F3 — Signposting tightening on §2.04 and §8 sub-sections.**
  - **Scope**: §2.04 signpost added this session; remaining
    sub-sections of §8 (sister of `08_05_threats_to_validity`) get
    matching opener paragraphs identifying *where you came from* and
    *where it leads*.
  - **Success criterion**: every `08_0N_*.md` file opens with a
    signpost paragraph and the body section `## Summary` (or final
    paragraph) names the next section explicitly.
  - **Owner / when**: a manuscript-polish session.

- **F4 — Dual Python/Rust capacity vs runtime clarification.**
  - **Scope**: §1 "Dual Python/Rust architecture" paragraph rewritten
    to lead with the runtime default (Python; `COGANT_USE_RUST=0`)
    and then describe the architectural capacity (8 crates,
    benchmarking-on-both-paths).
  - **Success criterion**: a reviewer cannot read the paragraph and
    infer that the production runtime is Rust by default.
  - **Owner / when**: next manuscript pass.

- **F5 — Graph-normalization remainder.**
  - **Scope**: method-receiver→class resolution, async-call edge
    kind, decorator-driven edges, generated-file detection, test-only
    `NodeKind.TEST` classification. Each is a separate increment with
    its own test fixture.
  - **Success criterion**: per increment, a new
    `tests/unit/test_graph_orchestration_*.py` file with a real-repo
    fixture and the post-fix edge-kind / node-kind assertion. Each
    increment must not regress the dotted-import tests landed this
    session.
  - **Owner / when**: per-increment scheduling; estimated 1 week each.

- **F6 — Dual-preset-registry deletion plan.**
  - **Scope** (per Advisor R2): write a dated, scoped deletion plan
    for one of the two preset registries
    (`config/defaults.py:PRESETS` vs `config/presets.py:PRESETS`).
    Decision needed: A) canonicalize a single name map and align both
    registries; B) prune `presets.py` and migrate its richer-content
    presets into `defaults.PRESETS`.
  - **Success criterion**: a documented ADR landed in
    `cogant/docs/architecture/` with a chosen path and a deletion
    schedule; `test_documented_dual_preset_surface_remains_acknowledged`
    updated to track the plan, not just the asymmetry.
  - **Owner / when**: typed-config session (≤2 weeks).

## Critical integrity finding — Roundtrip 23/23 quietest-strong-claim

`cogant/evaluation/dataset/roundtrip_results.jsonl` holds 23 rows in
the v0.5 ε-schema (tier=ISOMORPHIC, epsilon=1.0, no
`role_preservation_score`, no `roundtrip_status`). The current
`tools/regenerate_metrics.py:_status()` legacy guard tags every such
row `STALE_LEGACY` and excludes them from `role_preserved_count`.
**The shipped METRICS.yaml** (last regenerated before the guard
landed, or against a richer dataset since stripped) **asserts
`role_preserved_count: 23`** and the abstract injects that value.

The threats-to-validity section (§8.05) now carries an explicit
disclosure paragraph: the ε-corpus is a *role-recall regression set*,
not a fresh v0.6 result, and a non-zero `role_preserved_count` in
METRICS.yaml indicates either (a) a fresh v0.6 evaluation has landed
v0.6-tagged rows into the same ledger, or (b) the METRICS.yaml is out
of date — the per-target `roundtrip_status` field is the
trustworthy signal.

A fresh regen (running in this session) is expected to overwrite
`role_preserved_count` to 0 and mark all 23 rows STALE_LEGACY in
`per_target`. The abstract injection will then read honestly
"0 fresh-v0.6 role-preserved targets and 0 strict structurally
isomorphic targets". The prose already handles the 0-case gracefully.

## Manuscript signposting improvements

- §1 (Introduction): roadmap paragraph extended to enumerate
  appendices S01–S06 and the notation supplement, with one-clause
  descriptions of what each carries.
- §2.04 (GNN export + error handling): added a one-paragraph signpost
  closing the four-part method core (§2.01–§2.04) and pointing to
  §3 (API/workflows) as the next destination.
- §8.05 (Threats to validity): added "Legacy ε-corpus dataset state"
  paragraph documenting the STALE_LEGACY guard semantics and the
  per-target signal as the trustworthy reader path.
- §98 (Notation supplement): added the dangling-figure
  call-out paragraph linking the confidence-tier table to the
  calibration figure.

## Process artifacts

- **Pre-state snapshot**: `Plans/PRE_STATE_2026-05-19.md` +
  `Plans/_artifacts/{ruff-check,ruff-format,claim-ledger,audit-*}.txt`
  capture the exit codes and outputs of all 12 gates before any edits
  landed.
- **First-principles audit**: `Plans/FIRST_PRINCIPLES_AUDIT.md`
  documents the deconstruct-challenge-rebuild pass on the top 10
  load-bearing claims, with explicit verdicts and follow-up IDs.
- **RedTeam findings**: `Plans/REDTEAM_FINDINGS.md` (background agent)
  surfaced additional findings; triage results documented in this
  report's RedTeam section once available.
- **ISA**: `projects_in_progress/cogant/ISA.md` is the system of
  record for this run; ISCs, decisions, and the changelog are
  populated through VERIFY + LEARN.

## Memory-grounded methodology notes

- Followed `template-repo-convergent-automation`: owned `tools/`,
  tests, `ISA.md`, primitives. Manuscript prose edits were minimal
  and surgical (only signposts + threats-to-validity disclosure that
  the polish loop would not re-author back to the unhedged state).
- Applied `audit-quietest-strong-claims`: spent scrutiny on the
  `role_preserved: 23` strong claim, not on the loudly-hedged
  limitations sections.
- Applied `feedback-disclosure-is-not-remediation`: did not bury the
  STALE_LEGACY finding in a limitation hedge; promoted it to a §8.05
  paragraph AND surfaced the regen-driven structural fix.
- Applied `feedback-recurring-loop-suspect-the-gate`: stage-list
  drift now has an *enforced* gate with a negative-control test, not
  another hand patch.
- Applied `feedback-shape-tests-dont-bind-truth`: the drift-gate
  test fixtures include a forged-canonical mismatch that proves the
  gate isn't shape-blind.

## Post-state ground truth (2026-05-19 22:23)

The regen completed at `2026-05-20T05:03:34.170873Z` (UTC). Fresh
METRICS.yaml values:

```
test_count_total:    9648  (↑ from 9613 — new session tests added)
test_count_passing:  9575  (↑ from 9561)
coverage_percent:    94.98 (held)
mypy_strict_errors:  0     (↓ from 30 — pydantic.mypy plugin + yaml override)
ruff_violations:     0     (held)
roundtrip.role_preserved_count:   0  (↓ from 23 — laundering keystone corrected)
roundtrip.strict_isomorphism_count: 0  (held)
all 23 per_target rows tagged: STALE_LEGACY  (was: ROLE_PRESERVED 23x)
```

Abstract injection at `output/manuscript/00_abstract.md` now reads
honestly: "*METRICS.yaml reports* **0** *fresh-v0.6 role-preserved
targets and* **0** *strict structurally isomorphic targets (legacy rows
are tagged STALE_LEGACY, not counted as preserved)*" and "**9575**
*passing tests*", "**94.98%** *line coverage*", "**0** `mypy --strict`
*findings*". The keystone laundering defect from RedTeam F1 is closed
at the data, METRICS, and prose layers.

## Post-state gate sweep

| Gate | Result |
|------|--------|
| `mypy --strict` (211 source files) | Success: no issues found |
| `ruff check` + `ruff format --check` | All checks passed |
| `tools/audit_stage_list.py` | PASS |
| `tools/audit_pyi_exports.py` | Public export/.pyi parity passed |
| `tools/audit_docs_constants.py` | Docs/constants audit passed |
| `tools/audit_manuscript_crossrefs.py` | OK 32 files / 109 ids / 421 refs |
| `tools/audit_manuscript_numbers.py` | MISMATCH=0, MATCH=4, EXPECTED_MISMATCH=6 |
| `tools/audit_test_names.py` | OK |
| `tools/claim_ledger.py` | 2836 records emitted |
| Session-new tests (35) | 7 (stage-list) + 10 (min-confidence) + 14 (typed-config) + 4 (dotted-import) = 35 passing |

## RedTeam findings — disposition

RedTeam ran 40 adversarial findings against the post-edit tree
(`Plans/REDTEAM_FINDINGS.md`). Triage in this session:

| ID | Finding | Disposition |
|----|---------|-------------|
| F1 | METRICS roundtrip 23/23 inconsistency | **RESOLVED** by regen (0/23 now) |
| F2 | Per-target structural numbers zero | **DOCUMENTED** in threats-to-validity ε-corpus paragraph; deferred to F1-follow-up |
| F3 | s_role saturable by construction | **DOCUMENTED** in threats-to-validity (existing prose); promoted to abstract by 0/0 honest count |
| F4 | Arithmetic-impossible wave-14 table | **CLARIFIED** in S01 appendix with explicit "wave-14 components ≠ wave-16 overall" caveat + F1 follow-up tag |
| F5 | Fixpoint K=1 vacuous | **HONEST** in ablation prose; follow-up F7 (new) — add fixture requiring ≥2 productive iterations |
| F6 | A/B/C 100% fallback on lead exemplar | **PARTIALLY RESOLVED** — figure caption in §1 explicitly tags `calculator` as smallest-fixture orientation figure (not informative-posterior evidence) and points to `flask_app` (22 A rows, 41% non-fallback; D non-uniform) as the matrix-fallback diagnostic exemplar. Full exemplar swap (regenerating the graphical-abstract PNG from a flask_app run) deferred to F8 (new) — requires running `run_all.py` against flask_app and re-emitting the inspection-dashboard artifacts |
| F7 | mypy framing oversold | **RESOLVED** — manuscript prose now reflects post-fix zero-error state |
| F8 | CI coverage gate 75% vs 89% vs 94.98% | **RESOLVED** — `.github/workflows/ci.yml` aligned to 89% (pyproject floor) with comment explaining the 94.98% headline / 89% floor relationship |
| F9 | Rust workspace oversold | **RESOLVED** — §1 intro paragraph rewritten to lead with Python-default runtime + Rust-as-scaffold framing |
| F10 | Per-module coverage table hand-edited | **RESOLVED** (2026-05-20) — `tools/check_coverage_table.py` extended with `_parse_coverage_json` fallback that reads the committed `cogant/coverage.json` when the `.coverage` SQLite is absent (the original gate could only run after a fresh `pytest --cov`). Strict mode now runnable on a clean checkout. The gate surfaced 4 real drifts (engine 244→250 stmts, resilience 92→93%, png_export 1385→1771 stmts and 98→90%, flow 99→100%); all 4 corrected against ground truth. Wired into `make audit-coverage-table` + CI lint job. Post-fix all 27 rows match |
| F11 | Mutation testing 15-mutant sample | **PARTIALLY RESOLVED** (2026-05-20) — §6.04 prose now carries explicit "Statistical caveat" paragraph naming the 66.7% as a qualitative diagnostic on a 15-mutant hand-picked sample, NOT a statistically meaningful score. Readers told to treat the per-module rows as kill/total counts on the sample, not as estimates of the package-wide mutation-survival rate. Full mutmut trampoline fix remains future work |
| F12 | Galois proposition is "conjectured" | **RESOLVED** — S03 heading downgraded to `Conjecture` + explicit "Status" callout naming the proof-sketch as informal argument and a formal proof as future work |
| F13 | External validity hedge buried | **RESOLVED** — abstract now carries an explicit "External-validity caveat" paragraph naming "no held-out test split" + "no confidence interval" + the in-sample-upper-bound interpretation; cross-refs to @sec:08-05-threats-to-validity |
| F14 | Two per-fixture data sources | **OPEN** — deferred to F13 (new): canonicalize per-target source |
| F15 | `.pyi` stub honesty for optional imports | **RESOLVED** (2026-05-20) — `cogant/py/cogant/__init__.py` first-party imports made non-conditional (Session, PipelineRunner, Bundle, ProgramGraphBuilder, TranslationEngine, StateSpaceCompiler, GNNMarkdownFormatter). The Rust extension and the legacy `schemas.graph` fallback path are preserved (legitimate optional-implementation states). Test class rotated: `TestOptionalImportFallbacks` → `TestFirstPartyImportFailsLoudly` (10 tests asserting ImportError raise; 1 test pinning the legacy-graph fallback survival; 1 test pinning the Rust silent-fallback). New top-level regression `tests/unit/test_top_level_public_api_is_typed.py` (5 tests) pins that `cogant.Session` etc. are real classes, never None |
| F16 | "No mocks" policy vs 393 monkeypatch | **RESOLVED** — `cogant/tests/README.md` now carries honest test-isolation policy paragraph |
| F17 | TODO.md stale closed items | **RESOLVED** — all closed items now marked `[x]` with cite to their gate/test |
| F18 | audit_manuscript_numbers regex picks up "v0.6" as "6" | **RESOLVED** — regex now uses negative lookbehind `(?<![v\d.])`; post-fix MISMATCH count = 0 |
| F19 | check_metrics_fresh ratchet is shallow | **RESOLVED** (2026-05-20) — `tools/check_metrics_fresh.py` now re-classifies every row of `roundtrip_results.jsonl` via the same `_status()` logic the regenerator uses and asserts the four count fields (`role_preserved_count`, `strict_isomorphism_count`, `drift_count`, `failed_count`) match the committed values. Pinned by `tests/test_check_metrics_fresh.py` (4 tests: positive control, negative control catching a laundered METRICS.yaml against legacy-only data, honest legacy-only passes, and `_classify_row`-matches-regen-logic table). Wired into `make audit-metrics-fresh` + CI lint job |
| F20 | `cargo check ... continue-on-error: true` | **OPEN** — `cargo` not available in current shell; deferred to a future Rust-toolchain-equipped session. Documented as known posture in `manuscript/01_introduction.md` Dual Python/Rust architecture paragraph: "Rust workspace is an opt-in acceleration scaffold rather than the active runtime path" |
| F21 | Dev Status :: 3 - Alpha vs published artifact | **RESOLVED** (2026-05-20) — `cogant/pyproject.toml` classifier promoted to `Development Status :: 4 - Beta`; added `Intended Audience :: Science/Research`, `Topic :: Scientific/Engineering :: Artificial Intelligence`, `Typing :: Typed`; inline comment documents the maturity rationale |
| F22 | Tree-sitter parser uncovered yet load-bearing for JS/TS | **RESOLVED** (2026-05-20) — conclusion §15 now carries explicit "Coverage caveat" tagging the tree-sitter parser as omitted from the line-coverage gate by config + explaining the JS path is integration-exercised but not part of the 94.98% headline; readers are pointed to the structural-roundtrip framing rather than coverage-gated production support |
| F26 | "Production FastAPI server" without auth/quotas | **RESOLVED** (2026-05-20) — conclusion §14 renamed "Demonstration FastAPI server"; explicit non-production warning ("no authentication, no rate limiting, no request-size cap, no request-body sanitiser") + pointer to `cogant/docs/security/README.md` for the documented untrusted-input boundary |
| F28 | `requests_lib` conflated with full library | **RESOLVED** (2026-05-20) — §6.03 prose explicitly tags `requests_lib` as a "six-module reduction" (not the full library) and gives the full-library `rank: 23` row's hidden/obs/action sizes inline for direct comparison |
| F32 | Wave-number drift between S01 and HEAD | **RESOLVED** (2026-05-20) — S01 appendix gains "Wave nomenclature note" naming the three relevant waves (14, 16, 22) and explaining the relationship to current METRICS.yaml; ties the per-wave context together so a reviewer following a git ref can match the right wave |
| F23 | Synthesizer-gap scaffolding inflation | **RESOLVED** (2026-05-20) — `tools/regenerate_metrics.py` now emits `scaffolding_fraction` on every `per_target` row of `METRICS.yaml.evaluation.roundtrip`, computed as `(sum(synth_*) − sum(orig_*)) / sum(synth_*)` over HIDDEN_STATE/OBSERVATION/ACTION role-count fields. Pinned by `tests/test_scaffolding_fraction.py` (4 tests). Documented in `manuscript/S03_appendix_galois_sketch.md` "Scaffolding diagnostic" paragraph: read alongside `role_preservation_score` to see how much of a saturated 1.0 RP score is faithful preservation versus scaffolding inflation that clears the min/max similarity ceiling |
| F24/F27 | cogant.yaml dead surface | **PARTIALLY RESOLVED** (2026-05-20) — `cogant/cogant.yaml` header rewritten with explicit "CONSUMED today" vs "ASPIRATIONAL today" sections naming exactly which 7 keys the CLI reads and which 13 top-level sections are pinned by the typed-config tests but not yet wired through. Honest scoping, not a silent prune; full wire-or-prune decision stays in F6 follow-up |
| F38 | TODO.md "Last updated" stale | **RESOLVED** (2026-05-20) — date refreshed |
| F39 | GNN dep is pinned git SHA (install-time network/git required) | **RESOLVED** (2026-05-20) — `cogant/pyproject.toml` dependency block carries an explicit "Install-time prerequisites" comment naming the git + network-to-github.com requirement and the CC-BY-NC-SA-4.0 license implications. PyPI release tracked as future work |
| F40 | CLI subcommand stage-count differences | **RESOLVED** (2026-05-20) — §3 prose now carries explicit "Per-command stage coverage" paragraph naming which subcommands run all 10 stages (`translate`, default `analyze`) vs which run a minimal subset (`explain`: 5 stages; `statespace`: 4 stages; `validate`: 5 stages); reviewer running a non-default subcommand can match observed stage count to the documented subset |
| F36 | `cogant_graph.jsonl` committed artifact | **NO-OP** (2026-05-20) — investigation found `cogant/.gitignore` line `output/` already ignores the file; `git ls-files` confirms it is not tracked. False positive in the RedTeam report |
| F20, F33–F35, F37 (remaining minor/info) | Misc | **DOCUMENTED** in `Plans/REDTEAM_FINDINGS.md`; rotate-in to next maintenance session |

## Advisor commitment-boundary call

Advisor was called with the work-in-progress summary at task `bw51zvw2d`.
Highest-value advisor feedback (per `Plans/_artifacts/advisor.output`):

- "Plausible-but-unverified numeric prose" — every number cited in
  IMPROVEMENTS traced to a session-derived file ✓
- "Mid-flight artifact capture" — IMPROVEMENTS report now reflects
  post-regen state, not pre-regen expectations ✓
- "F2 deferral framing" — every F-follow-up now has scope +
  falsifiable success criterion + intended owner/date ✓
- "Sweep for sibling stale numbers" — number-provenance sweep run
  against README + PROMOTION + IMPROVEMENTS; only known
  contextually-valid numbers (12 submodules, 22 rules, 23 ledger rows
  vs 13 zoo dirs) remain ✓
- "Cross-ref parser self-test" — verified by inserting deliberately
  dangling refs into a temp file; auditor caught them ✓
- "Negative control for every gate cited" — stage-list ✓ (forged
  canonical fixture). For typed-config: dual-registry pin enumerates
  specific names. For min-confidence: 10 tests cover boundary cases
  including out-of-range tolerance. For dotted-imports: tests assert
  the pre-refactor failure mode (target ID not in IMPORTS edges) is
  resolved.

## Cato cross-vendor audit

Cato was invoked twice (initial + retry). First invocation surfaced a
directory-context issue (the inner `cogant/cogant/` nesting). Retry
invocation ran 25s and returned partial-trace ("I'll run the four gate
commands in parallel, then inspect the four files") without final JSON
verdict. Per Algorithm doctrine Rule 2a, the Cato verdict is **not
recorded as `pass`**; the work is recorded as having received Cato
review but with incomplete return. The advisor's parallel hostile-pass
served as the structurally equivalent commitment-boundary check.
Recommendation: re-run Cato in a future maintenance session against a
quiescent tree where pytest is not concurrently busy, to obtain a
deterministic verdict.

## Outstanding work — honest characterization

Per [[feedback-disclosure-is-not-remediation]] and the RedTeam
explicit recommendation: this session **improved** the package and
manuscript materially but did NOT close every blocking concern a
hostile reviewer could raise. The remaining open items (F5, F6, F10,
F11, F12, F13, F14, F15, F19 above) are scoped follow-ups, not silent
deferrals. The user should be aware:

- The headline structural honesty (mypy 0, drift-gate enforced,
  roundtrip count corrected to 0 with prose to match) is LANDED.
- The deeper construct-validity concerns (s_role saturable on the
  retained legacy corpus; fixpoint converges in K=1 on every fixture;
  calculator graphical-abstract lead exemplar has 100% matrix
  fallback) are HONESTLY DISCLOSED but not REMEDIATED — they require a
  fresh wave of evaluation data (a v0.6-tagged ledger), which is
  multi-day work.
- Recommendation: this session's improvements ship as a *v0.6.1
  maintenance release*. A *v0.7 publishable wave* needs a v0.6-tagged
  roundtrip ledger and a graphical-abstract exemplar with
  non-fallback A/B/C matrices.
