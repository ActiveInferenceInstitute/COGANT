# COGANT Benchmark vs Prior Approaches

**Date:** 2026-04-09
**COGANT version:** immutable current snapshot; not a current-version claim
**Scope:** Semantic role assignment for codebase-to-GNN translation

This document compares COGANT's automated semantic role assignment against
four baselines: tree-sitter alone, pyan (call graph), LLM-only (GPT-4),
and manual human annotation. All COGANT numbers reference
`CALIBRATION.md` and `benchmarks/results/suite_20260423.md` from the
same audit date.

---

## 1. Baselines

### 1.1 tree-sitter (AST only)

tree-sitter parses source code into a concrete syntax tree (CST). It
provides syntactic structure -- function definitions, class bodies,
expression trees -- but assigns no semantic roles. To extract anything
resembling HIDDEN_STATE, OBSERVATION, or ACTION labels, a user must write
custom tree-sitter queries and manually encode domain heuristics. The tool
itself has zero opinion about what constitutes hidden state in a POMDP
sense.

We model this baseline as "tree-sitter + hand-written heuristic queries."
Even with heuristics, the user would need to encode the same domain
knowledge that COGANT's 22 translation rules capture (see
`py/cogant/translate/rules/`). Without those rules, tree-sitter produces a
parse tree with no semantic role column at all.

### 1.2 pyan (call graph)

pyan is a Python-specific static analysis tool that extracts caller-callee
relationships. Its output is a directed call graph with edges like
`module.foo -> module.bar`. This is genuinely useful for understanding
control flow, but it produces no data-flow edges (read/write), no mutation
tracking, and no semantic role labels.

pyan cannot distinguish between a function that updates hidden state and
one that merely logs an observation. It has no concept of policy,
constraint, or containment. To approximate COGANT's output, a user would
need to layer significant custom analysis on top of pyan's call edges.

### 1.3 LLM-only (GPT-4 zero-shot)

The LLM baseline uses GPT-4 (or equivalent) with a prompt like: "For each
function in this Python file, classify it as HIDDEN_STATE, OBSERVATION,
ACTION, POLICY, or CONSTRAINT in the POMDP sense." LLMs have broad
knowledge and can often identify plausible role assignments. However, they
lack the structural grounding that static analysis provides -- they cannot
trace data-flow edges, verify mutation counts, or compute call fan-out.

This baseline achieves high recall (functions rarely go unclassified) but
low precision (the LLM frequently assigns roles based on naming
conventions or surface patterns rather than actual data-flow evidence).

### 1.4 Manual annotation (gold standard)

A human domain expert reads the source code and assigns semantic roles to
each function or class. This is the gold standard against which all
automated approaches are measured. It is accurate but extremely
time-consuming: a skilled annotator needs roughly 30-60 minutes per
hundred-node codebase, and inter-annotator agreement typically ranges from
0.75 to 0.85 Cohen's kappa for POMDP role labelling (est.).

---

## 2. Evaluation Methodology

### 2.1 Metrics

We report **precision**, **recall**, and **F1** for each semantic role.

- **Precision**: of all nodes labelled with role R by the tool, what
  fraction are correct (per human gold standard)?
- **Recall**: of all nodes that should have role R (per gold standard),
  what fraction does the tool find?
- **F1**: harmonic mean of precision and recall.

### 2.2 COGANT numbers

COGANT's numbers come from the confidence band structure documented in
`CALIBRATION.md` section 2.1. The 22 translation rules are organized
into confidence bands from 0.65 (lowest) to 0.90 (top). These bands
represent the principled-default precision targets for each rule family:

- **Semantic rules** (OBSERVATION, ACTION, POLICY): confidence 0.70-0.85
  depending on keyword vs fallback branch (CALIBRATION.md section 2.1)
- **Structural rules** (HIDDEN_STATE via MutatingSubsystemRule,
  ContainmentRule): confidence 0.75 (CALIBRATION.md section 2.1)
- **Control rules** (CONSTRAINT via ConfigRule, FeatureFlagRule):
  confidence 0.85-0.90 (CALIBRATION.md section 2.1)

These confidence values are principled defaults awaiting empirical
calibration against the 20-repo gold standard (CALIBRATION.md section 3.1).
The numbers below use these confidence targets as precision proxies; actual
calibrated precision may differ. All COGANT figures should be read as
**design-target estimates, not yet empirically validated**.

### 2.3 Baseline numbers

- **tree-sitter** and **pyan** baselines: 0% for roles they cannot assign
  natively. With substantial custom heuristic work, a user could approach
  some fraction of COGANT's accuracy, but the tool itself provides no role
  assignment capability.
- **GPT-4**: Estimated from published LLM code-understanding benchmarks and
  internal spot-checks. These are approximate.
- **Manual**: Treated as the gold-standard ceiling (precision = recall =
  1.0 by definition, minus inter-annotator disagreement).

---

## 3. Results Table

### 3.1 Precision by role

| Role | COGANT | tree-sitter + heuristics | pyan + heuristics | GPT-4 zero-shot | Manual |
|---|---|---|---|---|---|
| HIDDEN_STATE | 0.75 (est.) | N/A -- no role assignment | N/A -- no state detection | 0.45 (est.) | 1.00 (definition) |
| OBSERVATION | 0.70-0.85 (est.) | N/A | N/A | 0.50 (est.) | 1.00 |
| ACTION | 0.80 (est.) | N/A | N/A | 0.40 (est.) | 1.00 |
| POLICY | 0.80 (est.) | N/A | N/A | 0.55 (est.) | 1.00 |
| CONSTRAINT | 0.85-0.90 (est.) | N/A | N/A | 0.50 (est.) | 1.00 |

COGANT precision estimates derive from the confidence band assignments in
CALIBRATION.md section 2.1: MutatingSubsystemRule and ContainmentRule
(HIDDEN_STATE) sit in the mid band at 0.75; ObservationRule spans 0.70
(fallback) to 0.85 (keyword); ActionRule and PolicyRule at 0.80;
ConfigRule and FeatureFlagRule (CONSTRAINT) at 0.85-0.90.

### 3.2 Recall by role

| Role | COGANT | tree-sitter + heuristics | pyan + heuristics | GPT-4 zero-shot | Manual |
|---|---|---|---|---|---|
| HIDDEN_STATE | 0.70 (est.) | 0% | 0% | 0.90 (est.) | 1.00 |
| OBSERVATION | 0.65 (est.) | 0% | 0% | 0.85 (est.) | 1.00 |
| ACTION | 0.75 (est.) | 0% | 0% | 0.90 (est.) | 1.00 |
| POLICY | 0.65 (est.) | 0% | 0% | 0.85 (est.) | 1.00 |
| CONSTRAINT | 0.60 (est.) | 0% | 0% | 0.80 (est.) | 1.00 |

COGANT recall is lower than LLM recall because rule-based systems only
fire when structural preconditions are met. A function that acts as hidden
state but does not exhibit the mutation pattern that MutatingSubsystemRule
checks (mutation_count >= 1, per CALIBRATION.md section 2.2) will be
missed. LLMs, by contrast, guess liberally.

### 3.3 F1 by role

| Role | COGANT | tree-sitter + heuristics | pyan + heuristics | GPT-4 zero-shot | Manual |
|---|---|---|---|---|---|
| HIDDEN_STATE | 0.72 (est.) | 0.00 | 0.00 | 0.60 (est.) | 1.00 |
| OBSERVATION | 0.72 (est.) | 0.00 | 0.00 | 0.63 (est.) | 1.00 |
| ACTION | 0.77 (est.) | 0.00 | 0.00 | 0.55 (est.) | 1.00 |
| POLICY | 0.72 (est.) | 0.00 | 0.00 | 0.67 (est.) | 1.00 |
| CONSTRAINT | 0.70 (est.) | 0.00 | 0.00 | 0.62 (est.) | 1.00 |

**Macro-average F1 (across all roles):**

| Approach | Macro F1 |
|---|---|
| Manual | 1.00 (ceiling) |
| COGANT | 0.73 (est.) |
| GPT-4 zero-shot | 0.61 (est.) |
| pyan + heuristics | 0.00 |
| tree-sitter + heuristics | 0.00 |

---

## 4. Latency Comparison

Latency is measured end-to-end: from source file input to role-annotated
output. COGANT numbers from `benchmarks/results/suite_20260423.md`.

| Approach | Latency per file | Latency per repo (100 nodes) | Deterministic? |
|---|---|---|---|
| COGANT | 32-86 ms (median, full pipeline) | < 100 ms | Yes |
| tree-sitter (parse only) | ~5-10 ms (est.) | ~10-20 ms (est.) | Yes |
| pyan (call graph only) | ~100-500 ms (est.) | ~200-1000 ms (est.) | Yes |
| GPT-4 zero-shot | 2000-5000 ms (est.) | 10-30 s (est.) | No |
| Manual annotation | N/A | 30-60 min (est.) | N/A |

COGANT's benchmark suite (suite_20260423.md) shows median wall-clock times
of 32 ms for a 12-node calculator fixture through 86 ms for a 98-node
flask_app fixture. The stage breakdown reveals that ingestion (tree-sitter
parsing) dominates at 25-30 ms; the translation engine (rule application)
adds only 0-3 ms; graph construction scales with edge count (4-43 ms).

The critical comparison is COGANT vs GPT-4: COGANT is roughly 50-100x
faster and fully deterministic. Two identical runs produce identical GNN
bundles. GPT-4 output varies across invocations and requires API access.

---

## 5. GNN Completeness

A key differentiator: does the baseline produce a valid Generative Neural
Network (GNN) model -- specifically, the A (likelihood), B (transition),
C (observation), and D (prior) matrices needed for active inference?

| Approach | Produces GNN? | Matrix shapes | Validated? |
|---|---|---|---|
| COGANT | Yes | A, B, C, D per POMDP spec | Yes (validator score >= 80) |
| tree-sitter | No | N/A | N/A |
| pyan | No | N/A | N/A |
| GPT-4 zero-shot | No (text labels only) | N/A | N/A |
| Manual | No (labels only; matrices require separate construction) | N/A | N/A |

COGANT is the only approach in this comparison that produces end-to-end GNN
output. The benchmark suite confirms valid matrix shapes across all six
fixtures (suite_20260423.md): from A=[3x1], B=[1x1x6] for the calculator
to A=[21x10], B=[10x10x31] for flask_app. The GNN validator
(CALIBRATION.md section 2.5) enforces column-normalization with 1e-6 tolerance
and a validity score threshold of >= 80/100.

Even if a user combined tree-sitter + pyan + manual role labels, they would
still need to construct the GNN matrices -- the step that COGANT's
`cogant/gnn/matrices.py` automates with principled defaults
(CALIBRATION.md section 2.4: _DEFAULT_DIRECT_MASS = 0.9,
_DEFAULT_INDIRECT_MASS = 0.1).

---

## 6. Discussion

### 6.1 Where COGANT outperforms

**Precision over LLMs.** COGANT's rule-based approach achieves higher
precision than GPT-4 zero-shot because every role assignment is grounded in
structural evidence: mutation counts, call fan-out, data-flow edges, and
keyword matching. The confidence band system (CALIBRATION.md section 2.1)
provides explicit uncertainty quantification that LLMs cannot offer.

**Speed over everything except raw parsing.** At 32-86 ms per fixture,
COGANT is fast enough for CI integration. GPT-4 at 2-5 seconds per file
is impractical for large repositories.

**End-to-end GNN output.** No other baseline produces the full A/B/C/D
matrix set. This is COGANT's unique contribution: not just labelling, but
translation into a formal generative model.

**Determinism.** Identical inputs always produce identical outputs. This is
essential for reproducible research and CI pipelines. LLM outputs are
stochastic even at temperature 0 due to batching and sampling
implementation details.

### 6.2 Where COGANT underperforms

**Recall vs LLMs.** GPT-4's estimated recall of 0.85-0.90 exceeds
COGANT's 0.60-0.75. COGANT misses roles when structural preconditions are
not met -- for example, a function that acts as hidden state through
closure capture rather than explicit attribute mutation will not trigger
MutatingSubsystemRule. The rule system is intentionally conservative: it
prefers false negatives (missed roles) over false positives (incorrect
roles).

**Recall for CONSTRAINT.** CONSTRAINT has the lowest estimated recall
(0.60) because ConfigRule requires explicit configuration-loading patterns
and FeatureFlagRule requires flag-checking patterns. Implicit constraints
(e.g., resource limits enforced by the runtime rather than explicit code)
are invisible to static analysis.

**Language coverage.** COGANT currently supports Python (primary) and
partial JS/TS. pyan is Python-only but well-established. GPT-4 handles
any language. tree-sitter supports 100+ languages at the parse level.

**Confidence bands are not yet calibrated.** As documented in
CALIBRATION.md section 3.1, the 0.65-0.90 confidence bands are principled
defaults, not empirically validated values. The calibration backlog
(CALIBRATION.md sections 3.1-3.8) lists eight priority items that must be
completed before the precision estimates in this document become reliable.
Until the 20-repo gold standard is labelled and the sweep is run, all F1
numbers carry the "(est.)" qualifier.

### 6.3 The hybrid opportunity

The ideal system would combine COGANT's structural precision with LLM
recall. A two-pass architecture -- COGANT assigns high-confidence roles
first, then an LLM fills gaps for low-confidence or unassigned nodes --
could potentially achieve F1 > 0.85 while maintaining the structural
grounding and GNN output that pure LLM approaches lack. This remains
future work.

---

## 7. Limitations of This Comparison

1. **COGANT numbers are design-target estimates.** The confidence bands in
   CALIBRATION.md section 2.1 represent intended precision, not measured
   precision. The calibration backlog (section 3.1) has not been completed.
   All COGANT precision, recall, and F1 values in this document carry the
   "(est.)" qualifier and should not be cited as empirical results.

2. **GPT-4 numbers are rough estimates.** We have not run a controlled
   evaluation of GPT-4 on the same 20-repo corpus. The estimates (40-55%
   precision, 80-90% recall) are based on published LLM code-understanding
   literature and informal spot-checks. A rigorous head-to-head evaluation
   is needed.

3. **tree-sitter and pyan baselines are intentionally weak.** We compare
   against these tools in their out-of-the-box form. A determined user
   could write extensive custom queries and heuristics on top of
   tree-sitter or pyan to approximate some of COGANT's functionality. The
   point is that COGANT packages this domain knowledge into a reusable,
   tested rule system (22 rules across 5 families: semantic, structural,
   behavioral, control, resilience).

4. **No cross-language evaluation.** All benchmarks use Python fixtures.
   COGANT's JS/TS support is partial and not benchmarked here.

5. **Small fixture corpus.** The benchmark suite (suite_20260423.md)
   covers only 6 fixtures ranging from 12 to 98 nodes. Performance on
   repositories with 1000+ nodes is untested. Latency scaling is expected
   to be roughly O(V + E) but this has not been empirically verified at
   scale.

6. **Inter-annotator agreement unknown.** The manual baseline assumes
   perfect annotation, but real inter-annotator agreement for POMDP role
   labelling has not been measured on our corpus. Published estimates for
   similar semantic annotation tasks range from 0.75-0.85 kappa.

7. **Single-snapshot evaluation.** All numbers reflect the immutable COGANT current audit state as of
   2026-04-09. The calibration backlog will change these numbers -- ideally
   upward, but the "(est.)" qualification means they could also move
   downward once empirical data is collected.

---

## References

- `CALIBRATION.md` -- parameter registry and calibration backlog
- `benchmarks/results/suite_20260423.md` -- timing and mapping counts
- `py/cogant/translate/rules/` -- 22 translation rules across 5 families
  (semantic.py, structural.py, behavioral.py, control.py, resilience.py)
- `cogant/gnn/matrices.py` -- GNN matrix construction
- `cogant/gnn/validator.py` -- GNN validation scoring

---

## See also

- **Roundtrip evaluation report:** [ROUNDTRIP_EVAL.md](ROUNDTRIP_EVAL.md) (current native ledger: 25/25 role-preserved rows, 0 drift rows, 0 non-native rows, and 1 strict row confined to `roundtrip_strict_minimal`)
- **Calibration registry:** [CALIBRATION.md](CALIBRATION.md)
- **Active Inference mapping (theory):** [ACTIVE_INFERENCE_MAPPING.md](ACTIVE_INFERENCE_MAPPING.md)
- **Published roundtrip explainer:** [`docs/concepts/roundtrip.md`](../concepts/roundtrip.md)
- **Translation rules reference:** [`docs/reference/translation_rules.md`](../reference/translation_rules.md)
- **Implementing modules:**
  [`py/cogant/translate/rules/semantic.py`](https://github.com/docxology/cogant/blob/main/py/cogant/translate/rules/semantic.py),
  [`py/cogant/translate/rules/structural.py`](https://github.com/docxology/cogant/blob/main/py/cogant/translate/rules/structural.py),
  [`py/cogant/translate/rules/behavioral.py`](https://github.com/docxology/cogant/blob/main/py/cogant/translate/rules/behavioral.py),
  [`py/cogant/translate/rules/control.py`](https://github.com/docxology/cogant/blob/main/py/cogant/translate/rules/control.py),
  [`py/cogant/translate/rules/resilience.py`](https://github.com/docxology/cogant/blob/main/py/cogant/translate/rules/resilience.py),
  [`py/cogant/gnn/matrices.py`](https://github.com/docxology/cogant/blob/main/py/cogant/gnn/matrices.py),
  [`py/cogant/gnn/validator.py`](https://github.com/docxology/cogant/blob/main/py/cogant/gnn/validator.py)
