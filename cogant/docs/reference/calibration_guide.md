# Calibration Guide — Translation Confidence System

> Operational guide for empirically validating COGANT's confidence
> thresholds against a labelled corpus. Companion to the
> repository-wide [`docs/evaluation/CALIBRATION.md`](../evaluation/CALIBRATION.md)
> parameter registry: that file enumerates *what* needs calibrating;
> this file documents *how* to actually do it. Audience: researchers
> and reviewers who plan to resolve `TODO(calibration)` markers in
> `py/cogant/translate/` and `py/cogant/statespace/`.

---

## 1. What "calibration" means in COGANT

In COGANT, **calibration is threshold tuning, not model training.**

The confidence model is a deterministic, closed-form linear blend of
evidence terms:

```
confidence = clip₀¹( (avg_evidence + diversity_bonus) · parser_certainty
                     − conflict_penalty )
```

(see [`py/cogant/translate/confidence.py`](https://github.com/cogant-contributors/cogant/blob/main/py/cogant/translate/confidence.py),
`compute_confidence_score`). The blend itself is held fixed; only the
*scalar constants* — the multipliers, sweep gates, and tier
thresholds documented in §3 — are subject to empirical revision.

This deliberate scope choice has three consequences:

1. **No optimiser, no gradient, no held-out validation set in the
   ML sense.** Calibration is a grid sweep over a small finite set of
   candidate values per parameter, scored against a hand-labelled
   gold standard.
2. **Every calibration result is auditable.** A reviewer can look at
   the sweep curve, the elbow argument, and the resulting choice
   without retraining anything.
3. **The model remains transparent for downstream consumers.** The
   state-space compiler ([`py/cogant/statespace/compiler.py`](https://github.com/cogant-contributors/cogant/blob/main/py/cogant/statespace/compiler.py))
   and the GNN matrix synthesiser ([`py/cogant/gnn/matrices.py`](https://github.com/cogant-contributors/cogant/blob/main/py/cogant/gnn/matrices.py))
   can read confidence values without knowing how they were tuned.

A constant is a **calibration target** if and only if it is annotated
with a `TODO(calibration)` marker in source. Stability constants
(IEEE-754 epsilons, row-sum tolerances) and placeholder priors
(max-entropy Bernoulli, symmetric Dirichlet) are *not* calibration
targets; see [`CALIBRATION.md`](../evaluation/CALIBRATION.md) §4 and §5
respectively.

---

## 2. Threshold registry by file

The current count of `TODO(calibration)` markers in scope is:

| File | Markers |
| --- | ---: |
| `py/cogant/translate/confidence.py` | 8 |
| `py/cogant/translate/engine.py` | 1 |
| `py/cogant/translate/rules/structural.py` | 9 |
| `py/cogant/translate/rules/semantic.py` | 4 |
| `py/cogant/translate/rules/control.py` | 2 |
| `py/cogant/translate/rules/behavioral.py` | 5 |
| `py/cogant/translate/rules/resilience.py` | 4 |
| `py/cogant/statespace/temporal.py` | 2 |
| `py/cogant/statespace/variables.py` | 1 |
| **Total** | **36** |

Counts are obtained by `grep -rho "TODO(calibration)" py/cogant/translate/
py/cogant/statespace/ | wc -l` from the `cogant/` directory. Numbers
shift as markers are resolved or new ones added; the canonical figure
at any point in time is the grep output, not this table.

### 2.1 `py/cogant/translate/confidence.py`

| Constant | Default | Sweep range | Measure (primary) |
| --- | ---: | --- | --- |
| `STATIC_ONLY_THRESHOLD` | 0.50 | `{0.40, 0.50, 0.55, 0.60}` | F1 of `STATIC_ONLY` tier vs. gold |
| `STATIC_PLUS_RUNTIME_THRESHOLD` | 0.65 | `{0.55, 0.60, 0.65, 0.70}` | precision of `STATIC_PLUS_RUNTIME` |
| `RUNTIME_ONLY_THRESHOLD` | 0.40 | `{0.30, 0.35, 0.40, 0.45}` | recall of dynamic-only mappings |
| `HUMAN_REVIEWED_THRESHOLD` | 0.90 | `{0.85, 0.90, 0.95}` | rarely changes; sanity sweep |
| `diversity_bonus` multiplier | 0.10 | `{0.05, 0.10, 0.15, 0.20}` | tier-confusion delta on synthetic mixed-evidence cases |
| `conflict_penalty` multiplier | 0.05 | `{0.02, 0.05, 0.08, 0.10}` | precision of `STATIC_ONLY`-after-conflict cases |
| Spread divergence threshold (`detect_conflicts`) | 0.30 | `{0.20, 0.30, 0.40}` | observed `max−min` distribution on corpus |
| Spread divergence penalty | 0.10 | `{0.05, 0.10, 0.15}` | tier-confusion under conflict |
| Static-vs-dynamic spread | 0.25 | `{0.15, 0.20, 0.25, 0.30}` | observed cross-source delta distribution |
| Static-vs-dynamic penalty | 0.15 | `{0.10, 0.15, 0.20}` | tier-confusion under disagreement |
| `get_high_confidence_mappings` default | 0.70 | `{0.65, 0.70, 0.75, 0.80}` | precision @ "trust without review" cohort |
| `get_low_confidence_mappings` default | 0.60 | `{0.50, 0.55, 0.60, 0.65}` | recall of mappings the reviewer agrees need review |

### 2.2 `py/cogant/translate/engine.py`

| Constant | Default | Sweep range | Measure |
| --- | ---: | --- | --- |
| Conflict-loss broaden trigger | qualitative | empirical conflict-loss rate per rule | per-rule loss-rate threshold (target: ≤ 5 %) |

The marker on `engine.py:125` is not a sweep — it is a *trigger*: if
the empirical conflict-loss rate observed during the rule-band
calibration (§2.3) exceeds ≈5 % for any rule, the priority tiers in
`_resolve_conflicts` should be broadened from the current flat-`0`
priority. Resolution requires editing the priority field on the
losing rule, not changing the engine.

### 2.3 `py/cogant/translate/rules/structural.py` (9 markers)

| Constant | Default | Sweep range | Measure |
| --- | ---: | --- | --- |
| `ReadOnlyInputRule`→`ObservationRule` loss rate trigger | qualitative (≈20 %) | per-rule loss rate | conflict-loss rate on corpus |
| `ReadOnlyInputRule` parser certainty | 0.80 | `{0.70, 0.75, 0.80, 0.85}` | per-module precision |
| `MutatingSubsystemRule` mutation count | 1 | `{1, 2, 3}` | precision/recall F1 |
| `MutatingSubsystemRule` mutation count (inline check) | 1 | `{1, 2, 3}` | redundant — sweep both together |
| `InheritanceRule` tier-disagreement trigger | qualitative | tier-disagreement rate | demote to "explanation only" if routinely overruled |
| `InheritanceRule` agreement trigger | qualitative (50 %) | conflict-win rate | demote if win rate < 50 % |
| `ContainmentRule` method-count + tie-break | 5 / `max(actions, observations)` | `{3, 5, 8}` × tie-break variant | majority-vote accuracy |
| `ContainmentRule` method count (inline check) | 5 | `{3, 5, 8}` | redundant — sweep both together |
| `DataPipelineRule` parser certainty promotion trigger | < 0.80 | false-positive rate | promote to 0.80 if FP < 5 % |

### 2.4 `py/cogant/translate/rules/semantic.py` (4 markers)

| Constant | Default | Sweep range | Measure |
| --- | ---: | --- | --- |
| `ObservationRule` keyword/edge-only split | 0.85 / 0.70 | `{0.80/0.65, 0.85/0.70, 0.90/0.75}` | per-branch precision |
| `ActionRule` writes-threshold (docstring) | ≥ 2 | `{1, 2, 3}` | F1 on functional-style codebases |
| `ActionRule` writes-threshold (inline) | ≥ 1 | `{1, 2, 3}` | redundant — sweep both together |
| `PolicyRule` policy↔action collision rate | qualitative | observed collision rate on `handle`/`dispatch` | tie-break refinement |

### 2.5 `py/cogant/translate/rules/control.py` (2 markers)

| Constant | Default | Sweep range | Measure |
| --- | ---: | --- | --- |
| `ConfigRule` `NodeKind.CONFIGURATION` extraction false-positive rate | qualitative (< 5 %) | observed FP rate | reject confidence band 0.90 if FP ≥ 5 % |
| `FeatureFlagRule` parameter-detection coverage on ML frameworks | qualitative | per-framework recall | extend keyword set if recall < 70 % |

### 2.6 `py/cogant/translate/rules/behavioral.py` (5 markers)

| Constant | Default | Sweep range | Measure |
| --- | ---: | --- | --- |
| `OrchestratorRule` call-fanout (docstring) | ≥ 3 | `{2, 3, 5, 8}` | F1 on orchestrator gold |
| `OrchestratorRule` call-fanout (inline) | ≥ 3 | `{2, 3, 5, 8}` | redundant — sweep both |
| `EventBusRule` EVENT-node coverage | qualitative | per-corpus EVENT-node rate | confidence-tier hint validity |
| `StateMachineRule` STATE-node coverage | qualitative (< 40 %) | corpus coverage rate | demote to 0.75 if coverage < 40 % |
| `TestAssertionRule` keyword expansion trigger | qualitative | recall on assertion gold | expand keyword set if recall < 80 % |

### 2.7 `py/cogant/translate/rules/resilience.py` (4 markers)

| Constant | Default | Sweep range | Measure |
| --- | ---: | --- | --- |
| `RetryPatternRule` parser certainty | 0.70 | `{0.70, 0.75, 0.80}` | promote to 0.80 if `GUARDS` edge coverage improves |
| `SingletonAccessRule` module-diversity floor | ≥ 3 | `{2, 3, 5}` + whitelist filter variant | FP rate (target ≤ 30 %) |
| `SingletonAccessRule` read-count + module-count joint sweep | 3 / 3 | `{3, 5, 8}` × `{2, 3, 4}` | F1 on singleton gold |
| `RateLimiterRule` corpus coverage | qualitative (< 30 %) | per-corpus coverage | promote to 0.80 if coverage > 30 % |

### 2.8 `py/cogant/statespace/temporal.py` (2 markers)

| Constant | Default | Sweep range | Measure |
| --- | ---: | --- | --- |
| Sequential / parallel edge confidence | 0.95 / 0.70 | `{0.90, 0.95}` × `{0.65, 0.70, 0.75}` | trace-validation accuracy |
| `async_fraction` regime threshold | 0.30 | `{0.20, 0.25, 0.30, 0.35, 0.40}` | regime-classification accuracy |

### 2.9 `py/cogant/statespace/variables.py` (1 marker)

| Constant | Default | Sweep range | Measure |
| --- | ---: | --- | --- |
| `ConfidenceLevel` band mapping (`DEFINITE/HIGH/MEDIUM/LOW`) | 0.95 / 0.80 / 0.60 / 0.40 | one-knob-at-a-time around defaults | LOW/MEDIUM split agreement with human labels |

---

## 3. How to calibrate — methodology

### 3.1 Corpus

All calibration sweeps run against the **20-repo fixture corpus**:

* **Location:** `cogant/tests/fixtures/repos/`.
* **Composition:** 20 repositories balanced across Python and JS/TS,
  with three size buckets (≤ 1 kLOC, 1–10 kLOC, 10–100 kLOC) and
  domain coverage spanning CLI tools, web services, ML pipelines, and
  data-processing utilities.
* **Provenance:** Each repository ships with a SHA pin and a manifest
  describing which language version, which test fixtures, and which
  COGANT pipeline stages are exercised.

The corpus is intentionally *not* the same as the dev fixtures used
by the unit-test suite. Calibration must use the corpus; CI must use
the dev fixtures. Mixing them creates an information leak from the
calibration set into the test set.

Gold standards live under `evaluation/gold_standards/` (TBD per
[`CALIBRATION.md`](../evaluation/CALIBRATION.md) §4). Each gold-standard
file is a CSV with columns `(repo, mapping_id, label, reviewer_a,
reviewer_b)` where `label ∈ {correct, incorrect, partial}` and the
two reviewer columns capture inter-annotator agreement (Cohen κ
target ≥ 0.70).

### 3.2 Metrics

Pick the metric class by parameter shape:

| Parameter shape | Metric |
| --- | --- |
| **Tier threshold** (`STATIC_ONLY_THRESHOLD`, etc.) | per-tier precision, recall, F1 against gold; tier-confusion matrix |
| **Continuous multiplier** (`diversity_bonus`, `conflict_penalty`) | L2 error of computed-score distribution against L1-normalised gold-score distribution |
| **Count threshold** (`mutation_count >= N`, `methods >= 5`) | F1 on the mappings produced by the rule that owns the count |
| **Qualitative trigger** (loss-rate, coverage-rate annotations) | the trigger metric named in the marker (e.g. "loss rate ≥ 20 %"); no sweep — observe and act |

For threshold-style parameters, also report the **elbow location** —
i.e. the value at which dF1/dθ first drops below an analyst-chosen
slack (typically 0.05 per sweep step). The elbow is the recommended
pick when no operational constraint forces a different choice.

### 3.3 Recording results

Every resolved marker should produce three artefacts:

1. **Sweep CSV** at `evaluation/calibration_runs/<file>__<param>__<date>.csv`
   with columns `(value, precision, recall, f1, n_mappings, notes)`.
2. **Sweep plot** at `evaluation/calibration_runs/<file>__<param>__<date>.png`
   — F1 (y) vs. parameter value (x), elbow annotated.
3. **Inline annotation update** in the source file: replace
   `TODO(calibration): sweep {…}` with
   `empirically validated 2026-MM-DD against 20-repo corpus —
   see CALIBRATION.md §X` (and the section number in `CALIBRATION.md`
   that describes the sweep).

Reproducibility note: every sweep run must pin

* the corpus SHA-of-SHAs (a single hash over the manifest of pinned
  repo SHAs);
* the COGANT git SHA at the time of the sweep;
* the gold-standard SHA;
* the random seed used for any non-deterministic step (currently
  none, but enforce the discipline pre-emptively).

These four hashes go into the `notes` column of the sweep CSV's
header row.

### 3.4 Pick rules

After producing the sweep curve, pick the operating point under the
following tie-breaks:

* **Default:** elbow of F1 curve.
* **`RUNTIME_ONLY_THRESHOLD`:** tie-break in favour of *recall*.
  Noisy traces should surface for human review rather than be
  silently dropped.
* **`STATIC_PLUS_RUNTIME_THRESHOLD`:** tie-break in favour of
  *precision*. Corroborated mappings are the trustworthy core; a
  noisy `STATIC_PLUS_RUNTIME` cohort poisons every downstream
  consumer that filters on tier alone.
* **`HUMAN_REVIEWED_THRESHOLD`:** do not move below 0.90 without an
  explicit out-of-band justification. The 0.90 figure is the
  classical strong-consensus band and changing it requires an
  argument about what "human-reviewed" means, not just a sweep
  result.
* **Count thresholds (mutation/method/call-fanout):** tie-break in
  favour of the *higher* threshold. Cogant rules are eager by design;
  raising the floor reduces false positives more than it costs true
  positives in the size regimes the corpus covers.

---

## 4. The `TODO(calibration)` pattern

Every calibration target in source carries a marker in one of three
shapes. The shape encodes how to resolve it.

### 4.1 Sweep markers

> `TODO(calibration): sweep {0.4, 0.5, 0.55, 0.6, 0.65, 0.7} over a
> 20+ repo fixture set and pick the precision/recall sweet spot.`

These name an explicit candidate set. **Resolution recipe:**

1. Run the calibration harness with the parameter pinned to each
   candidate value.
2. Score against the gold standard with the metric named in §3.2.
3. Pick the elbow per §3.4.
4. Record the sweep CSV, sweep plot, and update the inline
   annotation per §3.3.

### 4.2 Trigger markers

> `TODO(calibration): if the false-positive rate on the 20-repo
> corpus exceeds 30 %, raise the module-diversity threshold to 5.`

These specify a conditional remediation. **Resolution recipe:**

1. Measure the trigger metric on the corpus (no sweep).
2. If the trigger fires, apply the named remediation; otherwise leave
   the parameter unchanged.
3. In *both* cases, replace the marker with `empirically validated
   2026-MM-DD: trigger metric was X% (vs. Y% threshold); action: Z`.
   Documenting non-firing triggers is as important as documenting
   firing ones — it prevents the marker from being re-opened later
   under the same evidence.

### 4.3 Coverage markers

> `TODO(calibration): measure rate-limiter coverage on the 20-repo
> corpus; if < 30 %, promote to 0.80 as the pattern is becoming more
> common in microservices.`

A trigger marker whose remediation specifically adjusts a confidence
band rather than a count threshold. Resolution proceeds as in §4.2;
the only difference is that the parameter being adjusted is a
confidence value, so the inline rule docstring's confidence-band
discussion may also need updating.

### 4.4 Resolution checklist (all marker shapes)

For every marker resolved, verify:

* [ ] Sweep CSV exists at the canonical path.
* [ ] Sweep plot exists at the canonical path.
* [ ] Source annotation no longer contains `TODO(calibration)`.
* [ ] Source annotation cites the date and the relevant
  `CALIBRATION.md` section.
* [ ] If the parameter value changed: the test suite still passes.
  Confidence-band changes can ripple into tier assignments and
  therefore into rule-output assertions; treat any test failure as a
  signal that downstream consumers need updating.
* [ ] If the parameter value changed: the GNN matrix snapshots
  regenerate without semantic change (run
  `pytest tests/gnn/test_matrices_snapshots.py` if present, or a
  golden-output comparison otherwise). The mutation report
  ([`MUTATION_REPORT.md`](../evaluation/MUTATION_REPORT.md) item M9)
  flagged the boundary semantics of `_map_confidence` as
  mutation-survivable; threshold edits live in exactly that region of
  the codebase, so a snapshot pass is non-optional.
* [ ] An entry is appended to the audit log
  ([`CALIBRATION.md`](../evaluation/CALIBRATION.md) §6) recording
  date, parameter, old value, new value, and reviewer.

### 4.5 Wontfix and deferral

A marker may be deferred ("won't fix this milestone") only if at
least one of the following holds:

* The corpus does not yet cover the regime the marker speaks to
  (e.g. the marker references a JS/TS-specific construct and the
  corpus has insufficient JS/TS code to measure it). Document the
  coverage gap in the marker's annotation.
* The marker is a *trigger* whose trigger metric cannot be measured
  without first resolving an earlier marker. Document the dependency.
* The marker's remediation is blocked on an upstream parser change
  (e.g. tree-sitter coverage). Cite the parser-side issue.

Deferred markers stay in source with their text unchanged but gain a
`# DEFERRED <reason>` line immediately above. They count as open in
the registry until resolved.

---

## 5. Worked example — calibrating `STATIC_PLUS_RUNTIME_THRESHOLD`

To make the methodology concrete, here is the recipe end-to-end for
the threshold whose marker lives at
`py/cogant/translate/confidence.py:40`.

1. **Pin the harness inputs.** Corpus SHA-of-SHAs `c0fa…`, COGANT
   SHA `8f39e593`, gold-standard SHA `g01d…`, seed `0` (unused).
2. **Run the sweep.** For each
   `θ ∈ {0.55, 0.60, 0.65, 0.70}`, monkey-patch
   `ConfidenceModel.STATIC_PLUS_RUNTIME_THRESHOLD = θ`, run COGANT
   end-to-end across the corpus, and collect the resulting
   `SemanticMapping` set.
3. **Score.** Compute per-tier precision and recall against the gold
   labels. The metric of record for this parameter is *precision of
   the `STATIC_PLUS_RUNTIME` tier* (per §3.4).
4. **Plot.** Draw precision (y) vs. θ (x). Annotate the elbow.
5. **Pick.** Suppose the elbow is at θ = 0.65 with precision = 0.86
   and the next-step value θ = 0.70 yields precision = 0.87 (a
   negligible 0.01 gain at the cost of recall). Pick **0.65**.
6. **Update source.** In `confidence.py`, replace the sweep marker
   on line ~40 with:

   ```python
   # empirically validated 2026-06-30 against 20-repo corpus
   # (precision 0.86 at θ=0.65; elbow); see CALIBRATION.md §3.3.
   STATIC_PLUS_RUNTIME_THRESHOLD = 0.65
   ```

7. **Update registries.** Append an audit-log row to
   `CALIBRATION.md` §6 and refresh the table in §2.3 of that file
   with the new annotation status. If the value moved, update the
   table in §2.1 above accordingly.
8. **Verify downstream.** Re-run the test suite, the GNN snapshot
   tests, and the mutation-survivor checks (M9 boundary semantics).
   No failures expected because the chosen value matched the prior
   default; a failure here would indicate the prior default was
   incorrect *and* untested for boundary semantics, which is itself
   a finding.

The same recipe applies to every sweep-shape marker in §2.

---

## 6. Cross-references

* **Module documentation:** [`py/cogant/translate/confidence.py`](https://github.com/cogant-contributors/cogant/blob/main/py/cogant/translate/confidence.py)
  — module-level docstring contains the threshold table and an
  end-to-end walk-through of `compute_confidence_score`.
* **Parameter registry:** [`docs/evaluation/CALIBRATION.md`](../evaluation/CALIBRATION.md)
  — repository-wide registry of every numeric constant; §2.3 is the
  authoritative table for the confidence combiner.
* **Mutation audit:** [`docs/evaluation/MUTATION_REPORT.md`](../evaluation/MUTATION_REPORT.md)
  — item **M9** documents the `>=` / `>` boundary semantics of
  `_map_confidence` in `statespace/compiler.py`. Threshold sweeps
  must not change boundary direction without re-running M9 and
  documenting the implications.
* **Translation rules reference:** [`translation_rules.md`](translation_rules.md)
  — confidence bands of the 22 active rules; calibration affects the
  band assignments on every rule listed there.
* **Semantic roles:** [`semantic_roles.md`](semantic_roles.md) — the
  catalogue of roles that `MappingKind` values resolve to.
* **State-space variables:** [`py/cogant/statespace/variables.py`](https://github.com/cogant-contributors/cogant/blob/main/py/cogant/statespace/variables.py)
  — `ConfidenceLevel` collapses the four-tier model into a coarser
  categorical view; the marker at `variables.py:67` calibrates the
  collapse points.
* **Configuration reference:** [`configuration.md`](configuration.md)
  — none of the calibration constants are user-configurable today;
  surfacing them as configurable would be a separate design change,
  not a calibration step.

---

## 7. Glossary

* **Calibration constant.** A numeric parameter whose value is
  intended to be re-fit against an external corpus. Identified in
  source by a `TODO(calibration)` marker.
* **Principled default.** A starting value motivated by convention,
  literature, or algebraic rationale. Every calibration constant
  starts as a principled default; calibration moves it from
  "principled" to "empirically validated".
* **Stability constant.** A numeric value dictated by IEEE 754 or
  library semantics (e.g. `1e-9` epsilon, `1e-6` row-sum tolerance).
  *Not* a calibration target.
* **Placeholder prior.** A maximum-entropy or uniform value inserted
  so a schema validates, intended to be replaced by learned values
  downstream (e.g. Dirichlet `α=1.0`, Bernoulli `p=0.5`). *Not* a
  calibration target.
* **Trigger marker.** A `TODO(calibration)` whose resolution is
  conditional on a measured rate exceeding a stated threshold. No
  sweep — measure once, act if triggered, document either way.
* **Sweep marker.** A `TODO(calibration)` that names an explicit
  candidate set. Resolved by sweeping over the set and picking the
  elbow.
* **Coverage marker.** A trigger marker whose remediation adjusts a
  confidence band specifically (rather than a count threshold).
* **Elbow.** The value of a parameter at which the metric's marginal
  improvement first drops below an analyst-chosen slack. The default
  pick when no operational constraint forces a different choice.
* **Tier confusion.** A confusion-matrix view over the four
  `ConfidenceTier` values. The primary diagnostic for sweeps over
  threshold-style parameters in §2.1.
* **Conflict-loss rate.** The fraction of cases in which a given
  rule's mapping is overridden during conflict resolution
  ([`engine.py:_resolve_conflicts`](https://github.com/cogant-contributors/cogant/blob/main/py/cogant/translate/engine.py)).
  The trigger metric for several markers in §2.2 and §2.3.

---

Agent notes: [AGENTS.md](AGENTS.md) · Hub: [../index.md](../index.md)
