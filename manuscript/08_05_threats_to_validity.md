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
`ROLE_MATCH_THRESHOLD = 0.5` precisely because, in the suite's own words, the
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

When a rule does not fire, matrix construction falls back to identity tensors
and a uniform prior (the $(0.9, 0.1)$ mass split of
@sec:02-01-program-graph-and-formal-foundations). A model dominated by such
fallbacks is *structurally* valid yet *semantically* near-empty, and a
structure-only validator score of 100/100 does not by itself exclude this case
(@sec:08-04-world-models-boundaries-and-compatibility already warns against
"over-interpreting matrix defaults or high validator scores as end-to-end
correctness"). The guard is the ledger, not the validator: the strict-isomorphism
gate requires generated-code compile success and zero matrix/section deltas, and
the per-target `s_role` denominator handling in
@sec:S01-appendix-roundtrip-epsilon assigns the vacuous one-sided case
`s_role = 0.0` rather than rewarding it. Readers auditing a *new* corpus should
report the fallback fraction and the non-default role distribution alongside the
validator score; the shipped fixtures expose these via the per-target
`metrics.json` (`role_confusion`, `graph_delta`, `matrix_delta`).

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

The figure set is generated and provenance-bearing, but that is not the same as proving that the visual workbench improves human judgment. The current evidence answers a **functional** question: the PNG exists, is nonblank, has a sidecar, records displayed counts, links to a source artifact, and is cited from the manuscript. It does not answer a **human-grounded** question: whether researchers using the dashboard more accurately find a failed mapping, explain a matrix fallback, or decide whether a roundtrip should be trusted. Visualization research treats domain task, abstraction, encoding, algorithm, and user validation as separable layers [@munzner2009nested; @sedlmair2012design; @brehmer2013typology]. COGANT currently claims the first four layers only for the registered static figures and dashboard artifacts; a design-study or user-task evaluation remains future work before stronger interpretability claims should be made.

## Legacy ε-corpus dataset state

The shipped `cogant/evaluation/dataset/roundtrip_results.jsonl` ledger
currently holds **{{TOTAL_TARGETS}}** rows in the v0.5 ε-bucket schema
(`tier`, `epsilon`, `orig_n_*`, `synth_n_*`, `elapsed_s`) without the v0.6
`role_preservation_score` or `roundtrip_status` fields. The
`tools/regenerate_metrics.py:_status()` legacy guard tags every such row
as `STALE_LEGACY` and the role-preserved counter (`role_preserved_count`)
excludes them by construction; the same regenerator records aggregate score
provenance as `{{ROLE_PRESERVATION_SCORE_SOURCE}}` and leaves native v0.6
mean/median/min/max role-preservation score fields unset when no row carries
the native `role_preservation_score` key. See the inline comment "Relabelling
tier=ISOMORPHIC as a fresh v0.6 'ROLE_PRESERVED' verdict is laundering,
not a measurement" in that file. The corpus is therefore retained
deliberately as a **role-recall regression set** rather than as a fresh
v0.6 result: any non-zero `role_preserved_count` in METRICS.yaml
indicates that a v0.6 evaluation run has subsequently landed
`role_preservation_score`-bearing rows into the same ledger. The
abstract's "fresh-v0.6 role-preserved targets" phrasing inherits this
provenance — a reader interpreting the abstract should consult the
per-target `roundtrip_status` field in METRICS.yaml to confirm whether
the cited count is sourced from STALE_LEGACY rows or from fresh v0.6
measurements. **Live per-run roundtrip metrics on the canonical
shipped fixtures** (calculator and friends, run via `run_all.py`) are
the v0.6-native signal; the ε-corpus is a regression anchor, not the
primary evidence vehicle.

## Summary

None of these threats refute the load-bearing, independently-checkable claims:
fixpoint determinism, the $O(V+E)$ Markov-blanket bound, and the reported
repeatability/provenance gates over fixed inputs. They do bound the *semantic*
reading of the round-trip evidence: COGANT is best understood as a
deterministic, provenance-bearing structural transducer and reproducible-research
instrument whose round-trip ledger is a self-consistency and regression signal,
with the strict-isomorphism subset (**{{STRICT_ISOMORPHISM_COUNT}}**/**{{TOTAL_TARGETS}}**)
as the conservative fidelity claim — not a semantic-equivalence oracle over
arbitrary Python.
