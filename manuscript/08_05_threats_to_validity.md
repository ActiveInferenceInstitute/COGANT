# Threats to validity {#sec:08-05-threats-to-validity}

This section consolidates, in one place, the validity threats that are stated in
scoped form across @sec:01-introduction, @sec:04-examples-and-failure-modes,
@sec:08-04-world-models-boundaries-and-compatibility ("When the extraction story
weakens"), the Limitations paragraph of @sec:10-conclusion, and
@sec:S01-appendix-roundtrip-epsilon. It is deliberately adversarial: each
subsection states the strongest objection a hostile reviewer would raise and the
precise artifact that bounds it. Nothing here changes a reported number; it
fixes the *interpretation* of what those numbers do and do not establish.

## Construct validity: what role-preservation measures

The single most important caveat. `s_role`
(`cogant.reverse.idempotency.role_preservation_score`) is computed over a
**forward → reverse → forward** loop in which the reverse synthesiser consumes
the same provenance-bearing IR that the forward pass annotated. A round-trip
score is therefore a measure of **encode/decode self-consistency**, not of
agreement with an external semantic ground truth: there is no independent oracle
that says which Active Inference role a given Python construct "should" carry.
The ceiling case is explicit — a degenerate translator that merely echoed the
roles it was handed would also score `s_role = 1.0`. Consequently
`role_preservation_score` on its own is **not** evidence of faithful semantic
translation, and the manuscript never rests the contribution on it alone. This
is exactly why the v{{VERSION}} roundtrip contract (@sec:00-abstract) reports an
**invariant ledger** rather than a single number: `structurally_isomorphic`
additionally requires zero node/edge deltas, preserved edge-kind counts, matrix
shape/value preservation, GNN-section preservation, **and generated-code compile
success**, while `role_confusion`, `role_edit_distance`, and
`graph_edit_distance` quantify *how far* a reconstruction deviates rather than
collapsing to a pass/fail an identity map would saturate. The defensible reading
is: `s_role` certifies that the IR is lossless **with respect to its own role
vocabulary**; the strict-isomorphism and edit-distance fields are what
distinguish a faithful reconstruction from a vacuous one, and only
**{{STRICT_ISOMORPHISM_COUNT}}** of **{{TOTAL_TARGETS}}** targets clear that
stricter bar.

That the metric is **not** identity-saturable is demonstrated, not merely
asserted, by the shipped negative-control tests. `verify_repo_roundtrip` is
exercised on uncurated repositories under a deliberately *lenient*
`role_threshold = 0.5` precisely because, in the suite's own words, the
GNN ↔ Python projection is "lossy" and the test must "catch catastrophic
regressions (e.g. the synthesizer dropping every action)"
(`tests/integration/test_reverse_roundtrip.py`); the contract model test pins a
sub-unity `role_preservation_score == 0.85`
(`tests/unit/test_server_models_contract.py`); stability-gap integration
explicitly tolerates `s_role` below 1.0
(`tests/integration/test_roundtrip_stability_gaps.py`); and role-dictionary
corruption is caught by `tests/unit/test_markov_blanket_boundary_cases.py`. A
degenerate echo cannot reach these scores when actions are dropped, so the
canonical-set uniformity (`min = max = 1.0` over **{{TOTAL_TARGETS}}** targets in
`METRICS.yaml`) reflects a deliberately curated **regression corpus**, not an
unfalsifiable metric — the falsifying behaviour exists and is tested on
uncurated input.

## Degeneracy and the vacuity floor

When a rule does not fire, matrix construction uses identity tensors
and a uniform prior (the $(0.9, 0.1)$ mass split of
@sec:02-01-program-graph-and-formal-foundations). A model dominated by such
degraded-output defaults is *structurally* valid yet *semantically* near-empty, and a
structure-only validator score of 100/100 does not by itself exclude this case
(@sec:08-04-world-models-boundaries-and-compatibility already warns against
"over-interpreting matrix defaults or high validator scores as end-to-end
correctness"). The guard is the ledger, not the validator: the strict-isomorphism
gate requires generated-code compile success and zero matrix/section deltas, and
the per-target `s_role` denominator handling in
@sec:S01-appendix-roundtrip-epsilon assigns the vacuous one-sided case
`s_role = 0.0` rather than rewarding it. Readers auditing a *new* corpus should
report the degraded-output fraction and the non-default role distribution alongside the
validator score; the shipped fixtures expose these via the per-target
`metrics.json` (`role_confusion`, `graph_delta`, `matrix_delta`).

## Lexical construct validity of forward role assignment

The roundtrip `s_role` caveat above concerns the *reverse* direction. The
*forward* role assignment carries its own construct-validity limit that the
rule-evidence trace makes inspectable but does not eliminate. Semantic-family
roles (OBSERVATION / ACTION / POLICY / PREFERENCE / CONTEXT) are assigned by
tokenising an identifier on underscore and camel-case boundaries and matching
the resulting whole tokens against per-role keyword vocabularies
(`OBSERVATION_KEYWORDS`, `ACTION_KEYWORDS`, and the policy/preference/context
sets). Role assignment is therefore a **lexical heuristic anchored to whole
tokens**, not a behavioural analysis, and it is fallible in two opposite
directions:

- **False positives (mis-naming).** A method whose name contains a registered
  keyword token but whose behaviour differs --- a `get_*` accessor that in fact
  mutates state --- is mis-roled by name. The structural rules partially counter
  this: COGANT suppresses an OBSERVATION mapping for a function that has WRITES
  or MUTATES edges (the mutation fact outranks the lexical hint), and HIDDEN\_STATE
  is driven by edges rather than names. Where no such structural signal exists,
  the OBSERVATION/ACTION/POLICY split rests on the name.
- **False negatives (non-canonical morphology).** Because matching is anchored to
  whole tokens rather than raw substrings, an inflected or affixed form of a
  keyword is *not* matched: `reroute` and `routes` do not match POLICY keyword
  `route`, `download` does not match ACTION keyword `load`, and `environment`
  does not match CONTEXT keyword `env`, so a legitimately role-bearing method can
  be left unmapped and silently drop out of the generative model. (Whole-token
  agentive nouns that are *themselves* registered keywords --- `dispatcher`,
  `router`, `coordinator` in the POLICY vocabulary --- are unaffected and match
  directly.) This is a deliberate precision-over-recall choice --- raw-substring
  matching produced false positives such as `set_target` matching the keyword
  `get` (the substring inside `target`) and `reset`/`dataset` matching `set` ---
  and the recall loss is partially recovered by prefix-form keywords (the
  OBSERVATION vocabulary registers `get_`, `read_`, and `sensor_` alongside the
  bare forms) and by the structural edge rules.
  The trade-off is pinned by a regression test
  (`tests/unit/test_semantic_role_token_anchoring.py`) so any future move to
  morphological normalisation is a deliberate change rather than silent drift.

Two behaviourally distinct methods that share a keyword token collapse to the
same `MappingKind`. This is precisely why the manuscript reports per-mapping
provenance and the reviewer-facing rule-evidence trace rather than a single
role-assignment accuracy figure: a human reviewer is expected to confirm or
reject each role, and the keyword vocabularies were tuned on the shipped
fixtures (see below).

## External validity: corpus and tuning

The canonical roundtrip result is measured on **{{TOTAL_TARGETS}}** targets
weighted toward curated fixtures (stated in the @sec:10-conclusion Limitations
paragraph). The {{TRANSLATION_RULES}} rules and keyword sets were authored with
these fixtures visible, so in-sample scores upper-bound, and do not estimate,
performance on never-tuned repositories; there is no held-out split and no
confidence interval. The cross-language `13_js_observer` round-trip and the
real-world `flask_app` / `requests_lib` / `json_stdlib` reductions are evidence
that the pipeline *generalises mechanically* (the parser/IR/state-space layers
run on unseen, non-Python input), not that role assignment is *accurate*
out-of-distribution. Claims phrased as "generalises" should be read as
"runs end-to-end on", and users are directed (@sec:10-conclusion) to validate
exports on their own corpora before trusting downstream model metrics.

This is also a benchmark-design limitation, not just a corpus-size limitation.
SIGPLAN empirical-evaluation guidance warns that empirical evidence should match
the claim and that benchmark choice can bias the conclusion [@sigplanEmpiricalGuidelines2026].
The ACM SIGSOFT empirical standards similarly treat conclusion validity,
construct validity, internal validity, reliability, objectivity, and
reproducibility as separate review dimensions [@sigsoftEmpiricalStandards2026].
COGANT's current evidence is therefore strongest for artifact generation,
traceability, and in-sample regression behavior. It is weaker for broad
comparative performance claims, accuracy on unseen ecosystems, and claims that
would require an independently selected benchmark suite or external replication.

The software-repository setting adds its own validity risks. Empirical
software-data guidance treats repository mining as an end-to-end measurement
problem: sampling frame, cleaning, deduplication, feature extraction, and
statistical interpretation all affect the conclusion [@bird2015softwareData].
For downstream machine-learning-on-code consumers, code duplication is a
particularly concrete leakage channel: Allamanis showed that duplicate code in
large scraped corpora can materially inflate reported model performance
relative to deduplicated evaluation [@allamanis2019adverse]. COGANT can record
stable identifiers, graph hashes, source paths, provenance rows, and run
manifests that make deduplication and leakage audits easier to perform, but it
does not solve benchmark leakage by itself. Any claim about learned downstream
model accuracy still needs an independently specified split, duplicate policy,
and held-out evaluation protocol outside the COGANT export step.

## Static-fragment scope

The program graph is built from a static front end. Dynamic and reflective
Python — `exec`/`eval`, metaclass- or decorator-synthesised members,
`__getattr__` proxies, monkey-patching, conditionally constructed import graphs,
and effects realised only at runtime — is not represented unless optional
runtime evidence is supplied. Role-preservation and the Markov-blanket
$O(V+E)$ bound are therefore properties **of the statically-recovered subgraph**,
which may silently undercount the program's true behaviour
(@sec:08-04-world-models-boundaries-and-compatibility, "When the extraction
story weakens"). This bounds, but does not invalidate, the determinism and
complexity claims, which hold by construction over whatever graph is built.

## Abstraction soundness (Galois)

@sec:S03-appendix-galois-sketch frames the forward/reverse pair as a
Galois-style preorder-quotient comparison, not as a proved adjunction for the
whole implementation. In an ordinary Galois connection, $\gamma \circ \alpha$
is an **inflationary closure**, i.e. abstraction is lossy by construction; the
COGANT round-trip analogy is therefore an identity only on the
**normal-form sub-image** the reverse synthesiser is designed to preserve, not
a global bijection over arbitrary program graphs. S03 already states it is "not
a replacement for label-preserving graph kernels"; the explicit consequence is
that perfect role-preservation is expected *on the closed sub-image* and is not
claimed to be a faithfulness theorem over all Python.

## Why a deterministic rule engine rather than an LLM mapper

The contemporary default for "code → X" is often to prompt a large language model, as reflected in recent LLM-for-code and LLM-for-software-engineering surveys [@zheng2023surveyCodeLLMs; @fan2023llmSESurvey]; a reviewer will reasonably ask why {{TRANSLATION_RULES}} hand-authored rules are preferable. The deliberate trade is **reproducibility and provenance over coverage**: a deterministic monotone fixpoint yields canonicalized, repeatable outputs under fixed inputs and a pinned environment, with a 4-tier provenance trail in which every role is traceable to a rule firing. A stochastic mapper may cover more unruled idioms, but it forfeits the run-to-run reproducibility and per-decision auditability properties that make the artifact usable as *scientific record* rather than a one-off suggestion. This is a positioning choice, not an empirical claim of superiority: a head-to-head comparison against an LLM-based mapper (accuracy on the un-ruled long tail vs. reproducibility and auditability) is explicit future work, and is not asserted here.

## Visualization validity

The figure set is generated and provenance-bearing, but that is not the same as proving that the visual workbench improves human judgment. The current evidence answers a **functional** question: the PNG exists, is nonblank, has a sidecar, records displayed counts, links to a source artifact, and is cited from the manuscript. It does not answer a **human-grounded** question: whether researchers using the dashboard more accurately find a failed mapping, explain a matrix degraded-output default, or decide whether a roundtrip should be trusted. Visualization research treats domain task, abstraction, encoding, algorithm, and user validation as separable layers [@munzner2009nested; @sedlmair2012design; @brehmer2013typology]. COGANT currently claims the first four layers only for the registered static figures and dashboard artifacts; a design-study or user-task evaluation remains future work before stronger interpretability claims should be made.

## Current native roundtrip ledger

The shipped `cogant/evaluation/dataset/roundtrip_results.jsonl` ledger is a
**current native** ledger of **{{TOTAL_TARGETS}}** rows regenerated by
`tools/regenerate_roundtrip_ledger.py`, which runs `verify_repo_roundtrip`
(forward → reverse → forward) on every locally-available fixture (zoo,
control-positive, real-world reductions) and records each target's
`roundtrip_status`, native `role_preservation_score` (the per-role mean of
$\min/\max$ multiset similarity), per-role multiset counts, graph size, and
file/LOC. Because every row carries an explicit `roundtrip_status`,
`tools/regenerate_metrics.py:_status()` routes it through the native path,
and `tools/check_metrics_fresh.py` re-derives the
count distribution from the same rows as an anti-laundering gate. METRICS.yaml
reports `role_preservation_score_source: {{ROLE_PRESERVATION_SCORE_SOURCE}}`
with native mean/median **{{MEAN_ROLE_PRESERVATION_SCORE}}** /
**{{MEDIAN_ROLE_PRESERVATION_SCORE}}**, **{{ROLE_PRESERVED_COUNT}}**
role-preserved, **{{STRICT_ISOMORPHISM_COUNT}}** strictly structurally
isomorphic, and **{{DRIFT_COUNT}}** drift targets.

Three caveats bound this result. First, **role preservation is symmetric
role-overlap, not isomorphism and not recall**: the strict subset contains
{{STRICT_ISOMORPHISM_COUNT}} of {{TOTAL_TARGETS}} targets that clear the strict bar (zero node/edge deltas,
preserved edge-kind counts, matrix shape/value preservation, GNN-section
preservation, generated-code compile success). The strict target is the
hand-authored `roundtrip_strict_minimal` reversible subset, so a role-preserved
verdict on the remaining application fixtures means the synthesized package's role multiset has high per-role
`min/max` overlap with the original's [@wu2018weightedMinhash] — not that the
two program graphs are isomorphic. Graph edit distance and graph-similarity
measures expose a much broader structural comparison space than this role
quotient [@sanfeliu1983distance; @grohe2024similarity]. Second, the
**{{DRIFT_COUNT}} drift targets** (role score below
{{THRESHOLD_ROLE_PRESERVED}}) are reported alongside the successes rather than
suppressed; the ledger records honest failures. Third, and most important,
**the fixtures are in-sample**: the {{TRANSLATION_RULES}} translation rules and
their keyword vocabularies were authored with these fixtures visible, so the
native scores *upper-bound* role-overlap behavior and do **not** estimate
performance on never-tuned repositories — the external-validity caveat above
applies in full.
Part of this circularity is *constructive*, not merely sample-tuned: the reverse
synthesizer emits role-keyword-prefixed identifiers (e.g. `get_`/`read_` for
observations, action-verb stems for actions) that the forward keyword rules are
built to match, so a fraction of any role-preservation score reflects the
synthesizer reproducing the cues the extractor keys on rather than independent
recovery of the original program's roles. This token-level circularity is
disclosed here qualitatively; it is *not* separately quantified, and the
per-row `scaffolding_fraction` does **not** measure it. That generator-computed
field (`tools/regenerate_metrics.py`) measures a different, dimensional kind of
inflation — `(Σ synth_n − Σ orig_n) / Σ synth_n` over the state-space count
fields — and is `0.0` on all {{TOTAL_TARGETS}} targets because the round-trip is
state-space-dimension-preserving here; it therefore bounds *count* scaffolding
to zero but says nothing about the keyword-token circularity above. Read the two
caveats separately: role preservation is therefore
necessary but not sufficient evidence of faithful structural capture.

## Semantics-preserving robustness suite

A reviewer's natural threat is that COGANT's role assignment is brittle to
edits that change a program's surface form without changing its behaviour —
the exact failure a keyword-driven rule could exhibit. The
`cogant/evaluation/robustness/` harness measures this directly: for each
semantics-preserving source transform it runs the forward pipeline on a base
fixture and on a transformed copy, then scores role drift with the **same
semantic oracle** the roundtrip evaluator uses
(`cogant.reverse.metrics.compare_role_distributions`). A transform is *robust*
only when **both** the role multiset is preserved (similarity $\geq$ 0.99)
**and** the transformed fixture still imports — the harness subprocess-imports
every transformed module, so a transform that parses but breaks at definition
time (a renamed parameter that orphans a keyword call site, a reordered
`@property`/`@x.setter` pair) is scored BROKEN, not robust. This makes the
transforms genuine behaviour-preserving edits rather than merely
role-multiset-stable ones: `rename_locals` renames only function-local
variables (never parameters, which are visible at keyword call sites), and
`reorder_methods` leaves decorator-coupled method groups in place. The assertions are pinned by
`tests/integration/test_semantic_preservation.py` (which also asserts
importability and a `@property` reordering case), and a negative control
(`drop_half_definitions`) that genuinely removes behaviour must be *detected* by
the oracle, so the suite cannot pass vacuously.

| Transform | Class | Role similarity | Verdict |
|---|---|---:|---|
| `reformat` (AST round-trip / formatting) | semantics-preserving | 1.0000 | ROBUST |
| `insert_comments` (comment + whitespace) | semantics-preserving | 1.0000 | ROBUST |
| `insert_dead_code` (`if False:` blocks) | semantics-preserving | 1.0000 | ROBUST |
| `rename_locals` (local-variable renaming) | semantics-preserving | 1.0000 | ROBUST |
| `reorder_methods` (definition reordering) | semantics-preserving | 1.0000 | ROBUST |
| `swap_if_branches` (equivalent branch rewrite) | semantics-preserving | 1.0000 | ROBUST |
| `outline_first_function` (outlining refactor) | sensitivity probe | 1.0000 | PRESERVED |
| `drop_half_definitions` | **negative control** | < 0.99 | DETECTED |

: Role-preservation and importability under source transforms (`evaluation/robustness/`, exact role-multiset equality + subprocess-import equivalence pinned by `test_semantic_preservation.py`). {#tbl:robustness-transforms}

On the shipped control-positive fixtures, all six semantics-preserving
transforms leave the extracted role multiset **exactly** unchanged: COGANT's
role assignment is robust to formatting, comments, dead code, parameter
renaming, definition reordering, and equivalent branch rewrites, because the
structural translation rules (containment, mutation, read/write edges) carry
the role signal even when keyword cues are perturbed, and the keyword rules
fall back to that structure. The negative control is detected, confirming the
oracle measures real role drift. Two boundaries remain explicit: the suite runs
on in-sample fixtures (it demonstrates *invariance to edits*, not out-of-sample
generalization), and `outline_first_function` is reported as a sensitivity
probe rather than a robustness claim because outlining can, on other code,
introduce a function node that shifts the multiset. Extending the corpus with
held-out repositories and adding cross-language (JS/TS) transform variants
remains future work.

## Summary

None of these threats refute the load-bearing, independently-checkable claims:
fixpoint determinism, the $O(V+E)$ Markov-blanket bound, and the reported
repeatability/provenance gates over fixed inputs. They do bound the *semantic*
reading of the round-trip evidence: COGANT is best understood as a
deterministic, provenance-bearing structural transducer and reproducible-research
instrument whose round-trip ledger is a self-consistency and regression signal,
with the strict-isomorphism subset (**{{STRICT_ISOMORPHISM_COUNT}}**/**{{TOTAL_TARGETS}}**)
as the conservative fidelity claim and currently a deliberately minimal fixed
point — not a semantic-equivalence oracle over arbitrary Python.
