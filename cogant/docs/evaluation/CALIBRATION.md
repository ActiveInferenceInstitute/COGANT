# CALIBRATION.md — COGANT Parameter Registry & Backlog

**Audit date:** 2026-04-09
**Scope:** All magic numbers, thresholds, and confidence values in
`cogant/py/cogant/` that affect translation or GNN-model outputs.
**Purpose:** Every threshold referenced in the COGANT manuscript must be
justified here. This file is the single source of truth for principled
defaults, stability constants, and the calibration backlog.

---

## 1. Methodology

### 1.1 Number classification

Every numeric constant in the codebase is categorised as one of:

| Class | Meaning | Calibration needed? |
| --- | --- | --- |
| **Stability constant** | Floating-point safety margin (e.g. `1e-9` epsilon, `1e-6` row-sum tolerance). Dictated by IEEE 754 semantics, not calibratable. | No |
| **Principled default** | Default value motivated by convention, literature, or explicit algebraic rationale. May still be empirically validated. | Optional — sweep and report |
| **Empirical estimate** | Hard-coded value that must be re-fit on the target corpus. | **Yes — backlog item** |
| **Placeholder** | Maximum-entropy or uninformative prior inserted so that the schema validates; intended to be replaced by learned values downstream. | No (but document) |

### 1.2 Calibration corpus

All empirical thresholds are to be calibrated against the **20-repo
fixture corpus** (Python + JS/TS, balanced small/medium/large,
discovered via `cogant/tests/fixtures/repos/`). Human-labelled
gold-standards are stored under `evaluation/gold_standards/` (TBD — see
backlog §4).

The calibration methodology is:

1. Sweep candidate values in the range documented per-parameter.
2. Score against the gold-standard using precision, recall, and F1 for
   classification parameters; or L2 error against ground-truth
   matrices for continuous parameters.
3. Report the sweep curve in the manuscript supplement; pick the value
   at the elbow.
4. Update the inline annotation with "empirically validated — see
   CALIBRATION.md §X" to signal that the TODO is resolved.

### 1.3 Fixpoint convergence

The translation engine runs rule application as a fixpoint iteration
(Cousot & Cousot, POPL '77). The **max-iteration cap** is a
principled default at 10; empirical convergence on the P3 fixture
suite (`calculator`, `event_pipeline`, `flask_mini`) happens within
≤5 iterations. The cap exists only to prevent runaway loops in
pathological cases and is not calibratable in any meaningful sense.

---

## 2. Parameter Registry

### 2.1 Translation rule confidence bands

All 22 translation rules share a flat priority of 0 and are resolved
at conflict time via the tuple `(priority, confidence_score)`. The
confidence bands below are **principled defaults** chosen to align
rules of similar reliability. Each is a TODO(calibration) target
against the 20-repo gold-standard.

| Band | Score | Rules |
| --- | --- | --- |
| **Top** | 0.90 | `ConfigRule` (`control.py`) |
| **High** | 0.85 | `PreferenceRule` (`semantic.py`), `TestAssertionRule` (`behavioral.py`), `FeatureFlagRule` (`control.py`), `ObservationRule` keyword branch (`semantic.py`) |
| **Upper-mid** | 0.80 | `ActionRule`, `PolicyRule`, `ContextRule` (`semantic.py`); `OrchestratorRule` (`behavioral.py`); `CircuitBreakerRule` (`resilience.py`) |
| **Mid** | 0.75 | `MutatingSubsystemRule`, `ContainmentRule`, `DataPipelineRule` (`structural.py`); `EventBusRule` (`behavioral.py`) |
| **Bottom** | 0.70 | `ReadOnlyInputRule`, `InheritanceRule` (`structural.py`); `ObservationRule` fallback branch (`semantic.py`); `RetryPatternRule`, `ErrorBoundaryRule` (`resilience.py`) |
| **Lowest** | 0.65 | `SingletonAccessRule` (`resilience.py`) |

**Parser certainty** is a separate field (range 0.70–0.95) that
reflects the precision of the underlying AST/tree-sitter extraction,
not the semantic confidence. Full per-rule breakdown is in the inline
docstrings under `py/cogant/translate/rules/`.

### 2.2 Rule-specific thresholds

| Parameter | Value | Rule | Class | Notes |
| --- | --- | --- | --- | --- |
| Mutation count (`mutation_count >= N`) | 1 | `MutatingSubsystemRule` | Principled default | Lowest reasonable threshold; calibrate against gold |
| Method count (`methods >= N`) | 5 | `ContainmentRule` | Principled default | Miller 1956 "5±2 chunking limit" |
| Call fan-out (`len(call_edges) >= N`) | 3 | `OrchestratorRule` | Principled default | Setup/work/cleanup triad |
| Write-edge count (`writes >= N`) | 2 | `ActionRule` fallback | Principled default | Avoids single-write helpers |
| Singleton read-edge count | 3 | `SingletonAccessRule` | Principled default | Plus module-count ≥ 3 |
| Singleton module-count | 3 | `SingletonAccessRule` | Principled default | Cross-module spread |

### 2.3 Confidence combiner (`cogant/translate/confidence.py`)

| Parameter | Value | Class | Notes |
| --- | --- | --- | --- |
| `STATIC_ONLY` threshold | 0.5 | Principled default | Baseline for unverified-by-runtime mappings |
| `STATIC_PLUS_RUNTIME` threshold | 0.65 | Principled default | Aligns with lowest rule band |
| `RUNTIME_ONLY` threshold | 0.4 | Principled default | Penalises absence of static corroboration |
| `HUMAN_REVIEWED` threshold | 0.9 | Principled default | Aligns with top rule band |
| `diversity_bonus` multiplier | 0.1 | Principled default | Small bonus per distinct provenance source |
| `conflict_penalty` multiplier | 0.05 | Principled default | Half the bonus — conflict is softer than corroboration |
| Divergence threshold (`detect_conflicts`) | 0.3 | Principled default | Two mappings diverge if `|c1-c2| > 0.3` |
| Conflict penalty (high) | 0.15 | Principled default | Applied to severe divergences |
| Conflict penalty (low) | 0.1 | Principled default | Applied to mild divergences |
| `get_high_confidence_mappings` threshold | 0.7 | Principled default | Above bottom band |
| `get_low_confidence_mappings` threshold | 0.6 | Principled default | Below lowest band |

### 2.4 GNN matrix defaults (`cogant/gnn/matrices.py`)

| Parameter | Value | Class | Rationale |
| --- | --- | --- | --- |
| `_DEFAULT_DIRECT_MASS` | 0.9 | Principled default | PyMDP convention for direct-evidence mass (Da Costa et al. 2020) |
| `_DEFAULT_INDIRECT_MASS` | 0.1 | Principled default | Complement of direct mass |
| `_EPSILON` | 1e-9 | Stability constant | scipy/pymdp convention; float64 safety |
| A-row normalization tolerance | 1e-6 | Stability constant | 8 orders of magnitude over float64 drift |
| D-vector sum tolerance | 1e-6 | Stability constant | Same rationale as A-row |

### 2.5 GNN validator scoring (`cogant/gnn/validator.py`)

| Parameter | Value | Class | Notes |
| --- | --- | --- | --- |
| `max_points` | 100 | Principled default | Percentage scale |
| `points_per_error` | 10 | Principled default | 10 errors → 0 score |
| `points_per_warning` | 2 | Principled default | 5:1 severity ratio vs errors |
| `valid` threshold (`score >= N`) | 80 | Principled default | "At most 2 errors" intuition — TODO(calibration) |
| A-row / D-sum tolerance | 1e-6 | Stability constant | Row-normalization safety |

### 2.6 Scoring metrics (`cogant/scoring/metrics.py`)

| Parameter | Value | Class | Notes |
| --- | --- | --- | --- |
| `max_nodes` (log-scale ceiling) | 1000 | Principled default | "Very large" Python module |
| Complexity density weight | 0.6 | Principled default | Favours structural coupling |
| Complexity size weight | 0.4 | Principled default | Complement of density weight |

### 2.7 State-space extraction (`cogant/statespace/*.py`)

| Parameter | Value | Class | File | Notes |
| --- | --- | --- | --- | --- |
| `ConfidenceLevel.DEFINITE` threshold | 0.95 | Principled default | `variables.py`, `compiler.py` | Near-1 mapping |
| `ConfidenceLevel.HIGH` threshold | 0.80 | Principled default | `variables.py`, `compiler.py` | ≥ upper-mid rule band |
| `ConfidenceLevel.MEDIUM` threshold | 0.60 | Principled default | `variables.py`, `compiler.py` | Below lowest rule band |
| `ConfidenceLevel.LOW` threshold | 0.40 | Principled default | `variables.py`, `compiler.py` | Aligned with RUNTIME_ONLY |
| `independence_score` placeholder | 0.5 | Placeholder | `variables.py` | Maximum-entropy until graded implementation |
| Sequential edge confidence | 0.95 | Principled default | `temporal.py` | Near-DEFINITE (sync Python semantics) |
| Parallel edge confidence | 0.70 | Principled default | `temporal.py` | Bottom band (async ambiguity) |
| Async regime threshold | 0.3 | Principled default | `temporal.py` | async_fraction > 0.3 → ASYNCHRONOUS |
| Stage extraction confidence | 0.6 | Principled default | `process/extractor.py` | Below lowest rule band |
| Bernoulli p default | 0.5 | Placeholder | `compiler.py` | Max-entropy Bernoulli prior |
| Categorical alpha default | 1.0 | Placeholder | `compiler.py` | Symmetric Dirichlet prior |
| Gaussian mean / variance defaults | 0.0 / 1.0 | Placeholder | `compiler.py` | Standard normal prior |

### 2.8 Engine fixpoint (`cogant/translate/engine.py`)

| Parameter | Value | Class | Notes |
| --- | --- | --- | --- |
| `max_iterations` | 10 | Principled default | Empirical convergence ≤ 5 on P3 fixtures (Cousot & Cousot 1977 fixpoint model) |

---

## 3. Calibration Backlog

Each item below is a standing calibration task. Items are ordered by
expected impact on manuscript claims.

### 3.1 Priority 1 — Confidence bands (rules)

**Goal:** validate that the 0.65–0.90 band assignment across 22 rules
matches human judgment on the 20-repo corpus.

**Method:**

1. For each rule, run it on the corpus and collect all triggered
   mappings.
2. Have two independent reviewers label each mapping as
   `{correct, incorrect, partial}`.
3. Compute per-rule precision and recall.
4. Re-centre each band so that the confidence reflects observed
   precision: 0.90 band should have ≥ 0.90 precision, etc.
5. Report the relabelling in the manuscript supplement.

**Deliverable:** `evaluation/gold_standards/rule_labels.csv` + calibration
note in this file.

### 3.2 Priority 2 — Structural thresholds

Sweep the following on the 20-repo corpus and report F1 curves:

| Parameter | Sweep range |
| --- | --- |
| `OrchestratorRule` call-count | {2, 3, 5, 8} |
| `ContainmentRule` method-count | {3, 5, 7, 9} |
| `SingletonAccessRule` read-edge count | {2, 3, 5} |
| `SingletonAccessRule` module-count | {2, 3, 4} |
| `MutatingSubsystemRule` mutation-count | {1, 2, 3} |
| `ActionRule` write-edge fallback | {1, 2, 3} |

### 3.3 Priority 3 — Confidence combiner dials

Sweep the combiner multipliers on synthetic corroboration/conflict
scenarios:

| Parameter | Sweep range |
| --- | --- |
| `diversity_bonus` | {0.05, 0.10, 0.15, 0.20} |
| `conflict_penalty` | {0.02, 0.05, 0.08, 0.10} |
| Divergence threshold | {0.2, 0.3, 0.4} |
| High divergence penalty | {0.10, 0.15, 0.20} |

### 3.4 Priority 4 — Validator score threshold

Calibrate the `score >= 80` validity cutoff against human ship/don't-
ship labels on generated GNN bundles:

1. Generate GNN bundles for all 20 corpus repos.
2. Have reviewers label each bundle as `{ship, don't ship}`.
3. Sweep `valid_threshold ∈ {70, 75, 80, 85, 90}`.
4. Report precision and recall per threshold.

### 3.5 Priority 5 — Complexity weights

The 0.6/0.4 density/size split in `CodebaseMetrics.complexity_score`
should be re-fit via ridge regression against human complexity
ratings on the 20-repo corpus. Target: Pearson correlation ≥ 0.70.

### 3.6 Priority 6 — Temporal regime threshold

Sweep `async_fraction ∈ {0.2, 0.25, 0.3, 0.35, 0.4}` and report
regime-classification accuracy against hand-labelled regimes.

### 3.7 Priority 7 — Stage extraction confidence

Re-fit `confidence=0.6` in `process/extractor.py` against precision
measured on hand-labelled process maps.

### 3.8 Priority 8 — Independence score

Replace the `independence_score=0.5` placeholder with a graded score
derived from fraction of overlapping mutation/read edges; calibrate
against a human-labelled factorization gold standard.

---

## 4. Stability Constants (not calibratable)

These values are fixed by IEEE 754 float64 semantics or library
convention and do **not** appear in the calibration backlog. They are
documented here for completeness.

| Constant | Value | Use | Source |
| --- | --- | --- | --- |
| `_EPSILON` | 1e-9 | Log-domain safety in matrix construction | pymdp / scipy convention |
| Row-sum tolerance | 1e-6 | Stochastic matrix validation | 8 orders headroom over float64 drift (~1e-14 for n≤100) |
| D-sum tolerance | 1e-6 | Initial-prior validation | Same as row-sum |

---

## 5. Placeholder Priors (max-entropy, replace when learned)

These values exist so the GNN schema validates; they are **not** part
of any claim and are intended to be replaced by posterior/learned
values in production use.

| Placeholder | Default | Distribution | Source |
| --- | --- | --- | --- |
| Bernoulli `p` | 0.5 | Max-entropy (1 bit) | Information-theoretic prior |
| Dirichlet `alpha` | 1.0 | Symmetric (uniform simplex) | pymdp default |
| Gaussian `mean` / `variance` | 0.0 / 1.0 | Standard normal | Friston et al. 2017, Neural Computation 29(1) |
| `independence_score` | 0.5 | Maximum-entropy placeholder | Pending graded implementation |

---

## 6. Audit log

| Date | Change | Author |
| --- | --- | --- |
| 2026-04-09 | Initial calibration audit; all magic numbers annotated inline | COGANT team |

---

## See also

- **Published calibration summary:** [`docs/rnd/calibration.md`](../rnd/calibration.md)
- **Active Inference mapping (theory):** [ACTIVE_INFERENCE_MAPPING.md](ACTIVE_INFERENCE_MAPPING.md)
- **Translation rules reference:** [`docs/reference/translation_rules.md`](../reference/translation_rules.md)
- **Implementing modules:**
  [`py/cogant/translate/confidence.py`](https://github.com/cogant-contributors/cogant/blob/main/py/cogant/translate/confidence.py) (confidence combiner),
  [`py/cogant/translate/engine.py`](https://github.com/cogant-contributors/cogant/blob/main/py/cogant/translate/engine.py) (fixpoint cap),
  [`py/cogant/translate/rules/`](https://github.com/cogant-contributors/cogant/blob/main/py/cogant/translate/rules/) (22 rules across semantic/structural/behavioral/control/resilience),
  [`py/cogant/gnn/matrices.py`](https://github.com/cogant-contributors/cogant/blob/main/py/cogant/gnn/matrices.py) (matrix defaults / stability constants),
  [`py/cogant/gnn/validator.py`](https://github.com/cogant-contributors/cogant/blob/main/py/cogant/gnn/validator.py) (validator scoring),
  [`py/cogant/statespace/compiler.py`](https://github.com/cogant-contributors/cogant/blob/main/py/cogant/statespace/compiler.py) (confidence-tier mapping),
  [`py/cogant/statespace/temporal.py`](https://github.com/cogant-contributors/cogant/blob/main/py/cogant/statespace/temporal.py),
  [`py/cogant/scoring/metrics.py`](https://github.com/cogant-contributors/cogant/blob/main/py/cogant/scoring/metrics.py)
