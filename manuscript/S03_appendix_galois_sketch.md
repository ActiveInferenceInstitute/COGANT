# Appendix C — Galois Connection Proof Sketch {#sec:S03-appendix-galois-sketch}

This appendix gives the formal statement and proof sketch of the ε-approximate
Galois connection between the category of Python program graphs and the
category whose objects are **GNN** bundles in the **Generalized Notation Notation** sense (Active Inference Institute structured notation; not graph neural networks). The informal version appears in Section
8.3 of the main text.

### C.1 Categories

Let **Prog** be the category whose objects are typed Python program graphs
`G = (V, E, λ_V, λ_E, τ)` in the sense of Section 2.2 ({{NODE_KIND_COUNT}} node kinds, {{EDGE_KIND_COUNT}}
edge kinds in the shipped schema; the Python front end emits a subset) and whose morphisms are graph homomorphisms that preserve node
and edge labels. Let **GNN** be the category whose objects are GNN v1.1
bundles (the Markdown sections `StateSpaceBlock`, `Connections`,
`InitialParameterization`, `ActInfOntologyAnnotation`, plus the
A/B/C/D matrices) and whose morphisms are role-preserving bundle embeddings.

Both categories are posets under the pointwise subset order: `G ≤ G'` in
**Prog** iff `V ⊆ V'`, `E ⊆ E'`, and the labelings agree on the common
subset; `M ≤ M'` in **GNN** iff each bundle section of `M` is included in
the corresponding section of `M'`.

### C.2 Forward and reverse functors

Define two order-preserving maps:

> **F : Prog → GNN** — the forward pipeline. `F(G)` is the GNN bundle
> emitted by `cogant translate G`: it runs ingest → static → normalize →
> graph → translate → statespace → process → export → validate and returns
> the `gnn_package/model.gnn.md` bundle together with the derived A/B/C/D
> matrices.
>
> **R : GNN → Prog** — the reverse pipeline. `R(M)` is the typed program
> graph extracted by running `cogant reverse M` (which internally invokes
> `parse_gnn → plan_package → synthesize_package`) and then re-parsing the
> synthesized Python package through the static + graph stages of the
> forward pipeline.

Both `F` and `R` are monotone because each underlying stage is monotone:
adding a node or edge to the input graph can only add mappings to
`semantic_mappings.json`, which can only add declarations to the GNN bundle,
which can only add planned nodes to `plan_package`, which can only add
synthesized code artefacts.

### C.3 Role multiset functor

Define the role-multiset functor **ρ : Prog → Mset(Roles)** that sends a
program graph `G` to the multiset of Active Inference roles assigned to its
nodes by the translate engine, where
`Roles = {HIDDEN_STATE, OBSERVATION, ACTION, POLICY, PREFERENCE, CONSTRAINT, CONTEXT}`.
Extend `ρ` to **GNN → Mset(Roles)** by counting the declarations in each
role-tagged section of a GNN bundle (`StateSpaceBlock` → HIDDEN\_STATE,
observation modalities → OBSERVATION, control states → ACTION, etc.).
Both extensions agree on the image of `F`: `ρ(F(G)) = ρ_GNN(F(G))` for every
`G ∈ Prog`, because the forward pipeline emits one section entry per
mapping in the translate output. The PREFERENCE role is included in `Roles`
because `PreferenceRule` emits PREFERENCE mappings that are recorded in the
GNN `Preferences/Constraints` section; Definition 2 in @sec:02-01-formal-definitions lists all seven roles.

### C.4 Adjunction (approximate)

**Proposition C.1 (ε-approximate Galois connection).** The forward/reverse
pair `(F, R)` satisfies the approximate Galois condition

> **F(G) ≤_GNN M ⟺_ε G ≤_Prog R(M)**

where `⟺_ε` means "the two inequalities agree on at least the ε-fraction of
the role multiset", i.e. for every `G ∈ Prog` and `M ∈ GNN`:

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
   the wave‑14 CONSTRAINT fix, the mapping from `NodePlan` to emitted
   artefact is injective on role multiplicity.
5. Re‑running `F` on the synthesized package recovers the same role
   multiset up to the **synthesizer gap**: extra OBSERVATION/CONSTRAINT
   nodes produced by scaffolding, which inflate `count_ρ(R(F(G)), r)` for
   those roles but preserve the origin roles exactly.

The multiset similarity `min(a,b) / max(a,b)` averaged over roles is
therefore bounded below by `(count_origin) / (count_origin + scaffold_r)`
for each role `r`, where `scaffold_r` is the fixed contribution of the
reverse synthesizer's scaffolding (4 CONSTRAINT, 7 OBSERVATION, 5 ACTION on
the minimum-case synthesis). The worst-case ε is achieved on targets where
the origin role counts are smaller than the scaffold; on zoo fixtures
(small origin, scaffold dominates) the ratio saturates because both sides
collapse to the scaffold, and on real-world libraries (large origin,
scaffold negligible) the ratio approaches 1.0 once the CONSTRAINT fix is
applied. In both regimes the Galois condition holds up to a bounded ε that
depends only on the rule table and the fixed synthesizer scaffolding.  ∎

### C.5 ε-isomorphism theorem

**Theorem C.2 (ε-Isomorphism).** For any `P ∈ Prog`, the roundtrip
`P → F(P) → R(F(P))` preserves the role distribution up to

> **ε(P, R(F(P))) = JS(ρ_norm(P) ∥ ρ_norm(R(F(P))))**

where `ρ_norm` is the role multiset normalized to a probability distribution
over `Roles`, and `JS` is the Jensen–Shannon distance. When the
multiset-similarity implementation in
`compute_isomorphism_report.role_match_score` is substituted for `JS`, the
theorem holds with the multiset-similarity metric in place of JS‑distance
and yields the values reported in Appendix A.

**Proof sketch.** The translate engine emits one `SemanticMapping` per
triggered rule, and each mapping carries exactly one role label. The forward
GNN bundle's `StateSpaceBlock`, observation modalities, control states, and
constraint annotations are in one-to-one correspondence with those mappings,
so `ρ_norm(F(P)) = ρ_norm(P)` (the forward map is role-preserving up to
normalization). The reverse map introduces scaffolding nodes that inflate
the role counts additively: `count(R(F(P)), r) = count(P, r) + scaffold_r`
for each role. The Jensen–Shannon distance between `P` and `R(F(P))` is
therefore bounded by the JS distance between two distributions that differ
only by a fixed additive shift, which in turn is bounded by a function of
`sum_r scaffold_r / sum_r count(P, r)`. In the limit of large programs
(real-world libraries), this ratio vanishes and ε → 0; in the limit of
small programs (zoo fixtures), the ratio saturates to the scaffold-only
distribution, which is equal on both sides, so ε → 0 again. The worst case
falls at intermediate sizes where origin and scaffold are comparable; this
is exactly where Appendix A.1 shows overall ε ≈ 0.85–0.95.  ∎

### C.6 ISOMORPHIC threshold and role preservation

**Proposition C.3.** The threshold `ε ≥ 0.8` (as defined in `METRICS.yaml`
`threshold_isomorphic`) to classify a target as ISOMORPHIC corresponds to
"at least 80% multiset similarity of the origin role distribution is
preserved in the roundtrip".

**Proof.** The multiset similarity per role is
`min(a,b) / max(a,b)`. Averaging over the `k` roles present on either side
and requiring the mean ≥ 0.8 means that the weighted-average per-role ratio
is at least 0.8. For a single role, `min(a,b) / max(a,b) ≥ 0.8` iff
`max(a,b) ≤ 1.25·min(a,b)` iff the counts are within 25% of each other.
When the reverse synthesizer only adds scaffolding, this is equivalent to
requiring `count_origin ≥ 0.8 · count_synth`, i.e. that the origin
population is at least 80% of the synth population. Summing over roles, the
ISOMORPHIC threshold corresponds to "at least 80% of the origin role multiset
survives the roundtrip without being drowned out by scaffolding". The
CONSTRAINT fix (@sec:S01-appendix-a2-constraint) and the wave-16 POLICY/CONTEXT fix are exactly the
transformations that make this true for constraint-heavy and policy-bearing
real-world libraries: each raises the CONSTRAINT (or POLICY/CONTEXT) component
of `count_synth` from a small scaffold constant to `count_origin` (proportional),
so `min = count_origin` and the per-role ratio jumps to 1.0.  ∎

## See also (MkDocs)

Formal statement: [`../cogant/docs/theory/isomorphism.md`](../cogant/docs/theory/isomorphism.md), [`../cogant/docs/evaluation/ISOMORPHISM_THEOREM.md`](../cogant/docs/evaluation/ISOMORPHISM_THEOREM.md).

---
