# First-Principles + IterativeDepth Claim Audit — COGANT 2026-05-19

> Deconstruct → Challenge → Reconstruct, applied to the manuscript's
> load-bearing claims. Lens passes: A) reader of paper, B) reviewer of
> code, C) reproducer, D) adversarial.

## Method

For each load-bearing claim:
1. **Deconstruct** — what irreducible fact does it assert?
2. **Challenge** — physics (immutable) / engineering constraint (movable)
   / unvalidated assumption?
3. **Re-derive** — run the actual generator THIS SESSION (R8), quote the
   artifact.
4. **Verdict** — Confirmed / Requalified / Retracted.

The five `feedback-*` memories that gate this audit:

- `feedback-audit-quietest-strong-claims` — spend scrutiny on the *quietest
  strongest claim*, not on the loudly-hedged ones.
- `feedback-disclosure-is-not-remediation` — a buried hedge in a prose
  paragraph does not fix a defect that exists in the data file the prose
  refers to. The remediation must change the load-bearing object.
- `feedback-verify-review-recs-before-applying` — re-derive numbers from
  primary artifacts before applying any edit.
- `feedback-remediation-agent-launders-fabrication` — do not hard-code an
  audit's flagged number into prose to silence the audit.
- `feedback-shape-tests-dont-bind-truth` — a test that checks only the
  *shape* of an output (counts present, fields populated) does not bind
  the truth of those values; pin known-bad rows.

## Finding 1 — Roundtrip ledger 23/23 is the quietest strong claim

**The claim.** Abstract (`manuscript/00_abstract.md`):

> `METRICS.yaml` reports **{{ROLE_PRESERVED_COUNT}}** fresh-v0.6
> role-preserved targets and **{{STRICT_ISOMORPHISM_COUNT}}** strict
> structurally isomorphic targets (legacy rows are tagged `STALE_LEGACY`,
> not counted as preserved).

`cogant/evaluation/METRICS.yaml` at audit time:

```yaml
roundtrip:
  total_targets: 23
  role_preserved_count: 23
  strict_isomorphism_count: 0
  drift_count: 0
  failed_count: 0
  mean_role_preservation_score: 1.0
  median_role_preservation_score: 1.0
  min_role_preservation_score: 1.0
  max_role_preservation_score: 1.0
```

So when the abstract is rendered, it reads "23 fresh-v0.6 role-preserved
targets" plus the legacy hedge. Quietest strong claim: *every single
target was role-preserved, with perfect score*. A reader sees 23/23 +
mean=median=min=max=1.0 and concludes the evaluation is flawless.

**Deconstruct.** What is the irreducible fact? The data file
`cogant/evaluation/dataset/roundtrip_results.jsonl` has 23 rows. Each row
asserts a *role-preserved* verdict on a specific repository.

**Challenge.** What does each row actually contain? Re-derived this
session via `python3 cogant/evaluation/dataset/roundtrip_results.jsonl`
inspection:

```
total: 23
with role_preservation_score: 0
with roundtrip_status: 0
with tier ISOMORPHIC: 23
with epsilon == 1.0: 23
fields: elapsed_s, epsilon, group, orig_n_actions, orig_n_hidden,
        orig_n_obs, rank, repo, synth_n_actions, synth_n_hidden,
        synth_n_obs, tier
```

**Every row is a legacy v0.5 ε-bucket entry** — no `role_preservation_score`
field, no `roundtrip_status` field. The v0.5 epsilon=1.0 was the
ε-bucket threshold of role multiset similarity *under the old taxonomy*.
The v0.6 schema separates `role_preservation_score` (multiset min/max
similarity, the post-fix measure that penalises both dropped and
hallucinated roles) from `roundtrip_status` (a categorical verdict).

**Re-derive.** `tools/regenerate_metrics.py:_status()` explicitly handles
the legacy case — quoted from `tools/regenerate_metrics.py:451-454`:

```python
# Legacy v0.5 rows carry only `tier`/`epsilon` and NO v0.6
# `role_preservation_score`. Relabelling tier=ISOMORPHIC as a
# fresh v0.6 "ROLE_PRESERVED" verdict is laundering, not a
# measurement — flag it so it is NOT counted as role-preserved.
if "role_preservation_score" not in entry:
    return "STALE_LEGACY"
```

The function correctly returns `STALE_LEGACY` for every current row. The
counter then sums `STRUCTURALLY_ISOMORPHIC` + `ROLE_PRESERVED` (line
477-479). Neither status is produced for these rows. **A fresh regen
should report `role_preserved_count: 0`, not 23.**

The current METRICS.yaml value of 23 must have been written before the
`STALE_LEGACY` guard was added, OR the dataset was richer at write time
and has since been stripped to the v0.5 fields. Either way, the *current
METRICS.yaml is out of sync with the current code, and the abstract that
injects it overclaims by a factor of ∞* (0 → 23).

**Verdict.** This is a CRITICAL integrity defect of the loudest results
claim, hiding inside the loudest hedge ("legacy rows are tagged
STALE_LEGACY, not counted as preserved"). The hedge is *true in code*
and *false in the file the code is supposed to produce*. Per
[[feedback-disclosure-is-not-remediation]], the remediation must be
structural: regenerate METRICS.yaml from the current dataset (which is
running in this session), then verify the injected abstract reflects the
honest value (likely `0`).

**Remediation in flight.** `tools/regenerate_metrics.py` running in
background (task `bkax22b7l`). When it completes, the new METRICS.yaml
should show `role_preserved_count: 0`, `total_targets: 23` (with all
23 tagged STALE_LEGACY in per_target), and the abstract injection will
honestly disclose the dataset state.

**Manuscript prose adjustment.** When the regen completes, the abstract
paragraph should be re-read to ensure the prose does not undercut the
new numbers. The "fresh-v0.6 role-preserved targets" phrasing is fine
when the value is 0; if a future regen produces a non-zero value (because
a v0.6 dataset has been added), the value carries the same prose intact.

## Finding 2 — Mean role-preservation score 1.0

**The claim.** METRICS.yaml: `mean_role_preservation_score: 1.0`.

**Re-derive.** `tools/regenerate_metrics.py:_role_score()` (line 466-472)
falls back to `epsilon` when `role_preservation_score` is missing.
Current dataset: 23 rows, all `epsilon == 1.0`. So mean = 1.0 mathematically.

But mean of *what*? Mean of epsilon, not of role_preservation_score —
those are different measures. Reporting a mean of 1.0 with a label
`mean_role_preservation_score` carries the *label* over from the v0.6
schema while the underlying values are v0.5 ε.

**Verdict.** REQUALIFY. The mean score key should either be renamed at
regen time to reflect the source measure (e.g.
`mean_role_preservation_proxy_score`) when the rows are legacy, OR the
mean should be undefined when zero v0.6 rows exist. The cleanest fix is
the second: when no row has `role_preservation_score`, the
`mean_role_preservation_score` field should be `null` and an explicit
`role_preservation_score_source: "legacy_epsilon_proxy"` marker should
appear alongside.

**Effort to fix.** ~30 lines in `tools/regenerate_metrics.py`. Deferred
because regen is mid-run and the abstract injection uses the existing
METRICS.yaml key set; renaming requires a paired manuscript variable
change. Logged as Follow-up F1 in the IMPROVEMENTS report.

## Finding 3 — Coverage 94.98 % is honest

METRICS.yaml: `coverage_percent: 94.98`. Coverage report file
`cogant/coverage.json` exists, audited at totals:
`{'covered_lines': 28016, 'num_statements': 29498, 'percent_covered': 94.98}`.

Re-derive: a clean re-run of `uv run pytest tests/ --cov=py/cogant` in
this session is in flight via the regen pipeline. The static
`coverage.json` value matches the METRICS.yaml. Verdict: CONFIRMED at
the static-snapshot level.

Caveat: per [[gotcha-pipeline-vs-standalone-coverage]], the
template-repo pipeline gate may compute coverage differently than the
in-package standalone `pytest --cov`. This audit confirms the in-package
value; the template pipeline coverage is a separate measurement.

## Finding 4 — Test count 9561 passing / 0 failing

METRICS.yaml: `test_count_passing: 9561`, `test_count_failing: 0`. Static
value from a prior regen.

Re-derive: in this session I ran focused suites (test_audit_stage_list:
7p, test_min_confidence_filtering: 10p, test_typed_config_loaders_e2e:
14p, test_viz_export_network_views + test_viz_static_analysis: 73p,
test_graph_orchestration_dotted_imports: 4p, plus
`-k graph or orchestration or import`: 1846p). The regen running in
background will produce the authoritative current full-suite number.

**Caveat per [[audit-verify-collection-not-just-exit]]**: `0 failing` is
trustworthy only if collection happened. The numbers above suggest the
suite collects > 9000 items, well above any obvious collection-only-N
threshold.

Verdict: pending regen completion; pre-state expectation is *new
tests added in this session would push the passing count past 9561*.

## Finding 5 — mypy strict errors 30 → 0

METRICS.yaml claimed `mypy_strict_errors: 30`. Re-derived at session
start by `uv run mypy --strict py/cogant`:

```
Found 30 errors in 11 files (checked 211 source files)
```

(All from .pyi stubs importing pydantic.) After fix (pydantic.mypy
plugin + yaml override):

```
Success: no issues found in 211 source files
```

Verdict: CONFIRMED both at pre-state (30) and post-state (0). The regen
will write `mypy_strict_errors: 0` into METRICS.yaml.

## Finding 6 — Translation-rule count 22 is structural invariant

`pipeline.translation_rules: 22` in METRICS.yaml. The `regenerate_metrics.py`
counts AST-defined `TranslationRule` subclasses under
`py/cogant/translate/rules/`. Re-derive: walked the directory; pinned
in `MEMORY/WORK/cogant-overnight/` (not strictly necessary — the
manuscript uses this value via `{{TRANSLATION_RULES}}` placeholder,
which the regen refreshes).

Verdict: CONFIRMED (structural invariant; rule add/remove triggers regen
automatically).

## Finding 7 — Dual-language Python/Rust claim

Intro section claims an 8-crate Rust workspace integrated via PyO3 with
a default-off `COGANT_USE_RUST=0` flag.

Re-derived via `ls cogant/rust/` — 8 crate dirs present:
`cogant-core/`, `cogant-graph/`, `cogant-translate/`, `cogant-statespace/`,
`cogant-trace/`, `cogant-ffi/`, `cogant-gnn/`, `cogant-store/`. Verdict:
CONFIRMED.

The "default-off" framing is honest about the production runtime path
(Python). A hostile reviewer might ask: *if Rust is default-off, why
claim the dual-language architecture as a feature?* The answer is that
the architecture is a *capacity*, not a *runtime claim* — the manuscript
should make that explicit. Soft refinement, not a critical fix.

## Finding 8 — Stage list invariance now enforced

Pre-fix: stage list drifted in 3 docs + 1 docstring on iter-4. Post-fix:
`tools/audit_stage_list.py` blocks drift in CI. Audit verified — the
gate fires on a forged canonical mismatch and passes on the current
tree (`test_audit_stage_list_fails_on_corrupted_canonical` is the
negative control).

Verdict: structural invariant promoted from "documented hand-patch" to
"enforced gate." This is exactly the [[feedback-recurring-loop-suspect-
the-gate]] resolution shape — the durable fix is the enforcement, not
another correction.

## Finding 9 — `--min-confidence` claim end-to-end

FAQ documents `--min-confidence` and the wire exists. New tests pin the
filter semantics across 10 cases. Verdict: claim now backed by tests.

## Finding 10 — Per-MappingKind ablation decomposition deferred

The manuscript appendix S02 mentions per-rule-family deltas but does
not break down per `MappingKind`. The ablation harness
`tools/regenerate_ablation.py` measures family-net totals only. This is
an honest open limitation; deferring it does not invalidate any
existing claim, only narrows what S02 can decompose. Logged as Follow-up
F2.

## Lens passes — what each lens surfaced

**Lens A (reader of paper).** Roadmap now spans Section 2 → 10 + S01–S06
+ notation supplement. Each major section already opens with a one-line
"this section" anchor; depth of signposting is uneven and the lens
recommends a tightening pass on §2.04 and §8 sub-sections. Logged as
Follow-up F3.

**Lens B (reviewer of code).** mypy strict (0 errors), ruff (0
violations), drift gate (enforced), viz content probes (migrated). The
remaining hygiene gap: ablation per-MappingKind + zoo extension (F2).

**Lens C (reproducer).** `PROMOTION.md` is current; `README.md` lists
the canonical regenerate commands; submodule init step documented. A
reproducer following the README should land on the same numbers after
the regen completes.

**Lens D (adversarial).** The principal finding is Finding 1
(roundtrip 23/23 stale-legacy laundering risk). All other defenses are
honest. The regen in flight closes Finding 1.

## Verdicts summary

| # | Claim | Verdict | Action |
|---|-------|---------|--------|
| 1 | Roundtrip 23/23 | CRITICAL — stale-laundering risk | Regen in flight; abstract honest after |
| 2 | Mean RPS 1.0 | REQUALIFY | F1 (rename / null-out) |
| 3 | Coverage 94.98 % | CONFIRMED | — |
| 4 | Tests 9561 p / 0 f | Pending regen | — |
| 5 | mypy 0 errors | CONFIRMED post-fix | — |
| 6 | 22 rules | CONFIRMED | — |
| 7 | Dual-language arch | CONFIRMED (with soft refinement) | F4 (clarify capacity vs runtime) |
| 8 | Stage-list enforced | CONFIRMED | — |
| 9 | `--min-confidence` end-to-end | CONFIRMED | — |
| 10 | Per-MappingKind ablation | OPEN limitation | F2 |

## Follow-ups to log

- **F1**: in `regenerate_metrics.py`, mark `mean_role_preservation_score`
  null when no row has `role_preservation_score`, add
  `role_preservation_score_source` field, update manuscript variable
  injection accordingly.
- **F2**: extend `regenerate_ablation.py` to emit per-`MappingKind`
  breakdown and to measure `zoo/01_simple_state` directly.
- **F3**: tighten signpost paragraphs in §2.04 and §8 sub-sections.
- **F4**: in §1 (Dual Python/Rust architecture), distinguish
  *architectural capacity* from *production runtime path*.
- **F5**: complete graph-normalization remainder (method-receiver→class
  resolution, async-call edge kind, decorator-driven edges, generated-
  file detection, test-only `NodeKind.TEST`).
