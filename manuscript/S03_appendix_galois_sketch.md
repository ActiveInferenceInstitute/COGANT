# Appendix C — Galois-Style Comparison Sketch {#sec:S03-appendix-galois-sketch}

This appendix gives the formal statement and argument sketch for the ε-approximate
Galois-style comparison between typed Python program graphs and **GNN** bundles in the **Generalized Notation Notation** sense (Active Inference Institute structured notation; not graph neural networks). The informal version appears in @sec:08-03-lenses-and-synthesis. The statement is deliberately scoped to the preorder quotients measured by the evaluator; it is not a claim that the unrestricted implementation forms a proven categorical adjunction.

### Categories {#sec:S03-categories}

Let **Prog** be the comparison category whose objects are typed Python program graphs
`G = (V, E, λ_V, λ_E, τ)` in the sense of @sec:02-01-program-graph ({{NODE_KIND_COUNT}} node kinds, {{EDGE_KIND_COUNT}}
edge kinds in the shipped schema; the Python front end emits a subset) and whose morphisms are graph homomorphisms that preserve node
and edge labels. Let **GNN** be the analogous comparison category whose objects are GNN v1.1
bundles (the Markdown sections `StateSpaceBlock`, `Connections`,
`InitialParameterization`, `ActInfOntologyAnnotation`, plus the
A/B/C/D matrices) and whose morphisms are role-preserving bundle embeddings.

The approximate statement below uses preorder quotients of these categories rather than the full homomorphism categories. Write `G ≤_Prog G'` iff `V ⊆ V'`, `E ⊆ E'`, and the labelings agree on the common subset; write `M ≤_GNN M'` iff each bundle section of `M` is included in the corresponding section of `M'` and the matrix dimensions/provenance records agree on shared entries. The maps below are therefore order-preserving maps on these quotients. Calling them "functors" is shorthand for the implemented structure-preserving maps after quotienting by stable identifiers and role labels, not a proof that every implementation detail is functorial.

### Forward and reverse maps {#sec:S03-forward-reverse-functors}

Define two order-preserving maps:

> **F : Prog → GNN** — the forward pipeline. `F(G)` is the GNN bundle
> emitted by `cogant translate G`: it runs ingest → static → normalize →
> graph → dynamic → translate → statespace → process → export → validate and returns
> the `gnn_package/model.gnn.md` bundle together with the derived A/B/C/D
> matrices.
>
> **R : GNN → Prog** — the reverse pipeline. `R(M)` is the typed program
> graph extracted by running `cogant reverse M` (which internally invokes
> `parse_gnn → plan_package → synthesize_package`) and then re-parsing the
> synthesized Python package through the static + graph stages of the
> forward pipeline.

Before conflict resolution, the rule-application operator is monotone over the finite set of
candidate mappings: adding a node or edge can only add candidates. The implemented pipeline
then applies an anti-monotone pruning step (`_resolve_conflicts()`) that keeps the highest
priority/confidence mapping over overlaps. The categorical sketch below therefore applies to
the role-quotient after deterministic conflict resolution, not to arbitrary intermediate
candidate sets.

### Role multiset map {#sec:S03-role-multiset-functor}

Define the role-multiset map **ρ : Prog → Mset(Roles)** that sends a
program graph `G` to the multiset of Active Inference roles assigned to its
nodes by the translate engine, where
`Roles = {HIDDEN_STATE, OBSERVATION, ACTION, POLICY, PREFERENCE, CONSTRAINT, CONTEXT}`.
Extend `ρ` to **GNN → Mset(Roles)** by counting the declarations in each
role-tagged section of a GNN bundle (`StateSpaceBlock` → HIDDEN\_STATE,
observation modalities → OBSERVATION, control states → ACTION, etc.).
Both extensions agree on the image of `F`: `ρ(F(G)) = ρ_GNN(F(G))` for every
`G ∈ Prog`, because the forward pipeline emits one section entry per
mapping in the translate output. The PREFERENCE role is included in `Roles`
because the GNN `Preferences/Constraints` section can record explicit preferences while the
shipped source-code rule set usually emits validator/test evidence as CONSTRAINT mappings;
@sec:def-translation-rule lists the mapping-kind alphabet that contains all Active Inference
roles.
The role multiset is a deliberately low-dimensional quotient of the program
graph. It is not a replacement for label-preserving graph kernels such as the
Weisfeiler-Lehman family [@shervashidze2011weisfeiler]; instead, it is the
invariant that the current reverse synthesizer is designed to preserve.
In a standard Galois connection, $\gamma \circ \alpha$ is an inflationary closure
(abstraction is lossy by construction). The COGANT comparison is weaker: this round-trip is an identity only on
the normal-form sub-image the reverse synthesizer targets — not a global
bijection over arbitrary program graphs, and not a faithfulness theorem over all
Python. @sec:08-05-threats-to-validity states this construct-validity boundary
in full.

### Adjunction (approximate) {#sec:S03-approximate-adjunction}

#### Conjecture: Approximate Galois-style comparison {#sec:prop-approximate-galois}

> **Status.** This is a **conjecture**, not a proposition. The "proof
> sketch" that follows is a structural informal argument — *not* a
> machine-checked proof, *not* a paper-and-pencil proof at the level
> of rigor a theorem heading would imply. The argument explains why
> we expect the approximate adjunction to hold on the restricted
> role quotient used by the current evaluator, and identifies the
> non-vacuity condition (`ε_worst < 1`) under which the conjecture
> has empirical content. A formal proof is explicit future work.

On the restricted role quotient used by the current evaluator, the forward/reverse
pair `(F, R)` is conjectured to satisfy the approximate Galois-style condition

> **F(G) ≤_GNN M ⟺_ε G ≤_Prog R(M)**

where `⟺_ε` means "the two inequalities agree on at least the ε-fraction of
the role multiset", i.e. on the canonical fixture/evaluation domain currently exercised by
COGANT:

> `multiset_sim(ρ(G), ρ(R(F(G)))) ≥ 1 − ε_worst`

where `ε_worst` depends only on the rule table and the synthesizer.

**Proof sketch.** The forward pipeline is the composition of a finite
sequence of monotone rule applications (the {{TRANSLATION_RULES}} translation rules in the
translate engine plus the A/B/C/D derivation in `statespace`), each of which
emits exactly one mapping per triggering graph pattern. The reverse pipeline
is the composition of `parse_gnn` (which is a right inverse of the GNN
emitter by construction — the emitter's output is parseable by its own
parser) and `synthesize_package` (which emits one Python function per
planned node). Composing the two:

1. Start with `G ∈ Prog`.
2. `F(G)` emits one GNN declaration per mapping in `translate(G)`; the
   number of declarations of role `r` equals `count_ρ(G, r)`.
3. `parse_gnn(F(G))` recovers the full declaration list bijectively.
4. `synthesize_package(plan)` emits one Python artefact per `NodePlan`; by
   the CONSTRAINT-role synthesizer fix recorded in @sec:S01-appendix-a2-constraint, the mapping from `NodePlan` to emitted
   artefact is injective on role multiplicity.
5. Re‑running `F` on the synthesized package recovers the same role
   multiset up to the **synthesizer gap**: extra OBSERVATION/CONSTRAINT
   nodes produced by scaffolding, which inflate `count_ρ(R(F(G)), r)` for
   those roles while preserving the origin role labels within the measured quotient.

The multiset similarity `min(a,b) / max(a,b)` averaged over roles is
therefore bounded below by `(count_origin) / (count_origin + scaffold_r)`
for each role `r`, where `scaffold_r` is the additive contribution of the
reverse synthesizer's **deficit-based** scaffolding for role `r` — the
`check_*` (CONSTRAINT), POLICY, and CONTEXT scaffolds it emits to fill role
deficits relative to the source bundle (`cogant.reverse.planner`,
`scaffold_*` plans). Because the scaffolding is deficit-based rather than a
fixed template, `scaffold_r` is target-dependent and bounded, not a constant;
the legacy ε-corpus rows illustrate its magnitude on small fixtures. The
large-program regime is the defensible asymptotic case: as origin role counts
grow, this additive term becomes a smaller share of the role distribution. The small-program regime is
diagnostic rather than theorem-friendly, because scaffolding can inflate a
role score that would otherwise reveal weak preservation. The conjecture
therefore has empirical content only when the reported score is read together
with the `scaffolding_fraction` field described below. ∎

### Role-preservation bound {#sec:S03-role-preservation-theorem}

#### Empirical invariant: Bounded role-preservation gap {#sec:thm-bounded-role-preservation-gap}

> **Status.** This is an empirical invariant and analytic bound for the current
> evaluator, not a fully formal theorem over all Python program graphs. It is
> phrased as a falsifiable implementation claim: the role multiset emitted by
> the current forward/reverse pair is measured by the metrics below and is
> invalidated by any future fixture that violates the stated bound.

For any `P ∈ Prog`, the roundtrip
`P → F(P) → R(F(P))` preserves the role distribution up to

> **ε(P, R(F(P))) = JS(ρ_norm(P) ∥ ρ_norm(R(F(P))))**

where `ρ_norm` is the role multiset normalized to a probability distribution
over `Roles`, and `JS` is the Jensen–Shannon distance [@lin1991divergence]. When the
multiset-similarity implementation in
`role_preservation_score` is substituted for `JS`, the same implemented
bound is reported with the multiset-similarity metric in place of JS-distance
and yields the values reported in @sec:S01-appendix-roundtrip-epsilon.

**Proof sketch.** The translate engine emits one `SemanticMapping` per
triggered rule, and each mapping carries exactly one role label. The forward
GNN bundle's `StateSpaceBlock`, observation modalities, control states, and
constraint annotations are in one-to-one correspondence with those mappings,
so `ρ_norm(F(P)) = ρ_norm(P)` (the forward map is role-preserving up to
normalization). The reverse map introduces scaffolding nodes that inflate
the role counts additively: `count(R(F(P)), r) = count(P, r) + scaffold_r`
for each role where the synthesizer emits fixed support code. The Jensen-Shannon distance between `P` and `R(F(P))` is
therefore bounded by the JS distance between two distributions that differ
only by a fixed additive shift, which in turn is bounded by a function of
`sum_r scaffold_r / sum_r count(P, r)` when the additive model holds. In the
limit of large programs (real-world libraries), this ratio vanishes and
ε approaches 0. In small fixtures, however, scaffolding may dominate the
role distribution; a high score in that regime is treated as a warning to
inspect `scaffolding_fraction`, not as an asymptotic proof. The most
informative cases fall at intermediate sizes where origin and scaffold are
comparable; this is exactly where @sec:S01-appendix-roundtrip-epsilon shows overall role-preservation gaps of roughly 0.85--0.95 on the affected historical rows. ∎

### Role-preservation threshold and strict invariant tier {#sec:S03-role-preservation-threshold}

#### Proposition: Role-preservation threshold {#sec:prop-role-preservation-threshold}

The threshold `s_role >= {{THRESHOLD_ROLE_PRESERVED}}` (as defined in
`METRICS.yaml` `threshold_role_preserved`) to classify a target as
ROLE_PRESERVED corresponds to the configured public multiset-similarity
floor for preserving the origin role distribution in the roundtrip.

**Proof.** The multiset similarity per role is
`min(a,b) / max(a,b)`. Averaging over the `k` roles present on either side
and requiring the mean ≥ `{{THRESHOLD_ROLE_PRESERVED}}` means that the
weighted-average per-role ratio is at least the configured public threshold.
For a single role, `min(a,b) / max(a,b) ≥ t` iff
`max(a,b) ≤ min(a,b) / t`.
When the reverse synthesizer only adds scaffolding, this is equivalent to
requiring `count_origin ≥ t · count_synth`. Summing over roles, the
ROLE_PRESERVED threshold corresponds to "enough of the origin role multiset
survives the roundtrip without being drowned out by scaffolding" under the
configured public threshold. The
CONSTRAINT fix (@sec:S01-appendix-a2-constraint) and the later POLICY/CONTEXT role-preservation fix are the
transformations intended to make this true for constraint-heavy and policy-bearing
real-world libraries: each raises the CONSTRAINT (or POLICY/CONTEXT) component
of `count_synth` from a small scaffold constant toward `count_origin` (proportional),
so `min = count_origin` and the per-role ratio jumps to 1.0.  ∎

**Scaffolding diagnostic emitted with every per-target row.** As of
v{{VERSION}}, `tools/regenerate_metrics.py` emits a `scaffolding_fraction`
field per `per_target` row of `METRICS.yaml.evaluation.roundtrip`,
defined as `(sum(synth_n_*) − sum(orig_n_*)) / sum(synth_n_*)` over
HIDDEN_STATE / OBSERVATION / ACTION role-count fields when present. A
value near 0.0 means the synthesizer emitted ≈ the same role counts
the origin graph had; values near 1.0 mean the synth side is dominated
by scaffolding (newly-introduced roles that did not appear in the
origin multiset). Pinned by `tests/test_scaffolding_fraction.py`. Read
this alongside `role_preservation_score` to know how much of a
saturated 1.0 RP score is measured role preservation versus scaffolding
inflation that happens to clear the min/max similarity ceiling — the
adversarial reading invited by the construct-validity bound in
@sec:08-05-threats-to-validity.
