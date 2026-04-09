# COGANT Isomorphism Theorem: Program Graphs and Generative Models as Dual Views of Causal Structure

**Author:** COGANT R&D  
**Date:** 2026-04-09  
**Status:** Theory (pre-proof)  
**Related:** `ROUNDTRIP_VALIDATION.md`, `SCOPING_REPORT.md`

---

## 1. Informal Claim

A typed program graph and an Active Inference generative model are both representations of the same underlying causal structure.

More precisely: the dependency graph of a Python module — who reads from whom, who writes to whom, what functions call what — encodes precisely the same directed influence structure as the A/B/C/D matrices of a Partially Observable Markov Decision Process (POMDP). The COGANT forward pass (`cogant.translate`) and the COGANT reverse pass (`cogant.reverse`) are not lossy compressions followed by heuristic reconstruction. They are two projections from an abstract object that exists independently of either representation.

The informal claim to be formalized: **COGANT's forward and reverse translations are two legs of a natural transformation between functors on well-defined mathematical categories.**

This document constructs those categories, states the strongest theorem that is actually true, and documents the gap between that theorem and the full adjunction that would hold if the translation were lossless.

---

## 2. Mathematical Setup

### 2.1 Category 𝒫 (Program Graphs)

**Objects.** A program graph is a tuple G = (V, E, λ_role, λ_type) where:

- V is a finite set of nodes (functions, classes, variables, modules)
- E ⊆ V × V × {READS, WRITES, CALLS, IMPORTS} is a set of labeled directed edges
- λ_role : V → {HIDDEN_STATE, OBSERVATION, ACTION, POLICY, CONSTRAINT, LIKELIHOOD} assigns each node an Active Inference role
- λ_type : V → TypeExpr assigns each node a syntactic type annotation (possibly `Any` if unannotated)

**Morphisms.** A morphism f : G → G' is a function f : V → V' such that:

1. **Role preservation:** λ_role(v) = λ_role'(f(v)) for all v ∈ V
2. **Edge preservation:** (u, v, l) ∈ E implies (f(u), f(v), l) ∈ E'

These are role-preserving graph homomorphisms. Note that f need not be injective; a morphism can collapse two nodes of the same role into one (as occurs when deduplication merges structurally equivalent components).

**Composition** is function composition; the identity morphism is the identity on V. 𝒫 is a well-defined small category.

### 2.2 Category 𝒢 (Generative Models)

**Objects.** A generative model is a tuple M = (S, O, A_act, A, B, C, D) where:

- S is a finite set of hidden states (corresponds to HIDDEN_STATE nodes)
- O is a finite set of observations (corresponds to OBSERVATION nodes)
- A_act is a finite set of actions (corresponds to ACTION nodes)
- A : O × S → [0,1] is the likelihood matrix, A[o, s] = P(o | s)
- B : S × S × A_act → [0,1] is the transition matrix, B[s', s, a] = P(s' | s, a)
- C : O → ℝ is the log-preference vector (goal specification)
- D : S → [0,1] is the prior over hidden states, Σ_s D[s] = 1

**Morphisms.** A morphism φ : M → M' is a triple of bijections (σ : S → S', ω : O → O', α : A_act → A_act') such that:

1. A'[ω(o), σ(s)] = A[o, s] for all o ∈ O, s ∈ S
2. B'[σ(s'), σ(s), α(a)] = B[s', s, a] for all s', s ∈ S, a ∈ A_act
3. C'[ω(o)] = C[o] for all o ∈ O
4. D'[σ(s)] = D[s] for all s ∈ S

These are probability-preserving relabeling isomorphisms. In 𝒢, morphisms are sparse: they exist only when models differ by permutation of indices. This is appropriate because GNN semantics are index-invariant.

**Note on matrix sizes.** Because morphisms in 𝒢 are bijections, 𝒢 has no non-identity non-isomorphism morphisms between objects of different sizes. This is a deliberate design choice reflecting the semantics of GNN: two models with different numbers of hidden states are genuinely different objects, not related by a canonical map.

### 2.3 Two Functors

**Forward functor F : 𝒫 → 𝒢** (COGANT forward pass):

Given G = (V, E, λ_role, λ_type), define:

- S = {v ∈ V | λ_role(v) = HIDDEN_STATE}
- O = {v ∈ V | λ_role(v) = OBSERVATION}
- A_act = {v ∈ V | λ_role(v) = ACTION}
- A[o, s] = 1/|{s' | (s', o, WRITES) ∈ E}| if such edges exist, else 1/|S| (uniform)
- B[s', s, a] = 1/|{s'' | (s, s'', READS) ∈ E, λ_role(s'') = HIDDEN_STATE}| if the action node a has a WRITES edge to s', else 0
- C[o] = log(1 + |{e ∈ E | head(e) = o}|) (log in-degree as preference proxy)
- D[s] = 1/|S| (uniform prior, as no dynamic initialization information is extracted)

On morphisms: a role-preserving homomorphism f : G → G' induces a map F(f) : F(G) → F(G') defined by the restriction of f to the HIDDEN_STATE, OBSERVATION, and ACTION subsets. F(f) is a morphism in 𝒢 only when f is a bijection on each role-stratum; for general morphisms, F extends to a functor into a relaxed category where probability-preserving maps allow many-to-one mappings (averaged distributions). We accept this extension for the purpose of this document.

**Reverse functor R : 𝒢 → 𝒫** (COGANT reverse pass, `cogant.reverse`):

Given M = (S, O, A_act, A, B, C, D), define a canonical synthesized program graph:

- For each s ∈ S: generate a Python variable `hidden_{s}` with λ_role = HIDDEN_STATE
- For each o ∈ O: generate a Python function `observe_{o}` with λ_role = OBSERVATION
- For each a ∈ A_act: generate a Python function `act_{a}` with λ_role = ACTION
- For each (o, s) pair with A[o, s] > threshold: generate a WRITES edge from s to o
- For each (s', s, a) triple with B[s', s, a] > threshold: generate READS edges s → s and WRITES edge a → s'
- D induces no structural edges (it is an attribute, not a dependency)
- C induces no edges (it is a scalar preference, not a dependency)

R(φ) for a morphism φ = (σ, ω, α) : M → M' sends each generated node to its renamed counterpart.

---

## 3. Adjunction Claim

The natural hope — following the standard categorical treatment of bidirectional transformations initiated by the lens literature — is that F and R form an adjoint pair:

**Claim (adjunction, to be falsified below):** F ⊣ R, i.e., there is a natural bijection:

> Hom_𝒢(F(G), M) ≅ Hom_𝒫(G, R(M))

This would mean: every way to embed G's GNN into M corresponds bijectively to a way to embed G into M's synthesized codebase. Intuitively, this would express that "information lost in F is exactly information not needed by R," and vice versa.

This is the categorical formulation of the round-trip completeness property that motivates building `cogant.reverse` at all.

---

## 4. Why It Doesn't Quite Work (Lossy Projection)

The adjunction claim is false as stated. F is lossy in ways that R cannot recover:

**Loss class 1 — Implementation identity.** Two functions `f = lambda x: x * 2` and `g = lambda x: x + x` receive the same role assignment (if they have the same in/out edges) but are not equal as program text. R generates exactly one canonical representative per role; the original is not recoverable.

**Loss class 2 — Symbolic names.** F discards variable names except insofar as they match role-assignment keyword rules (e.g., a variable named "dispatch" may be assigned ACTION by a keyword heuristic). R regenerates names from templates (`hidden_0`, `act_1`, etc.). The original names are gone.

**Loss class 3 — Documentation and comments.** Docstrings and inline comments are entirely absent from program graph nodes. F makes no attempt to encode them, and R generates no comments.

**Loss class 4 — Type signature specificity.** F records whether a node has a type annotation and uses that annotation to inform matrix indices, but it does not encode the full type expression as a matrix entry. R cannot reconstruct `List[Tuple[int, str]]` from the GNN; it generates `Any`.

**Consequence for the adjunction.** Because F is not full (non-isomorphic graphs can have the same image under F), the unit of the putative adjunction η : id_𝒫 → R ∘ F is not a natural isomorphism. Specifically, η_G : G → R(F(G)) exists as a morphism (there is a role-preserving map from G to its synthesized counterpart) but is not generally invertible.

**What we actually have: a Galois connection.** If we collapse 𝒫 and 𝒢 to preorders (ordered by structural refinement: G ≤ G' if there exists a role-preserving injection G → G', and M ≤ M' if M is a sub-model of M'), then F and R form a **Galois connection**:

> F(G) ≤ M ⟺ G ≤ R(M)

This is a weaker but still useful structure. It means that COGANT's forward pass is monotone (more refined programs produce larger GNNs) and the reverse pass is monotone (larger GNNs produce more refined synthesized programs), and these two monotonicities are adjoint in the preorder sense.

---

## 5. What IS Preserved: The Role Isomorphism Theorem

Despite the lossiness of F, the most computationally important structure is preserved exactly.

**Definition (role distribution).** For a program graph G, define:

> R_dist(G) = (|V_H|, |V_O|, |V_A|, |V_P|, |V_C|)

where V_H = {v | λ_role(v) = HIDDEN_STATE}, V_O the OBSERVATION nodes, V_A the ACTION nodes, V_P the POLICY nodes, V_C the CONSTRAINT nodes.

**Theorem (Role Isomorphism).** For any program graph G, the round-trip satisfies:

> |R_dist(G) - R_dist(R(F(G)))| ≤ ε(G)

where |·| denotes the L1 norm of the difference vector and ε(G) is the number of nodes in G whose role assignment is ambiguous (matched by two or more COGANT rules with equal priority score).

**Proof sketch.**

(1) F(G) records exact role assignments in the `annotations` field of the GNN output for each node. No role information is lost in F with respect to the role distribution.

(2) R(F(G)) generates exactly one node per recorded role entry in F(G). By construction of R, |V_H(R(F(G)))| = |S| = |V_H(G)|, and similarly for OBSERVATION and ACTION nodes.

(3) When F is applied to R(F(G)), role re-assignment fires on the synthesized code. For each node generated by R with role r, R generates Python code whose structural pattern (in-edge types, out-edge types, keyword tokens) was chosen to match the structural predicate that assigned role r in the original code. Provided the structural predicate is deterministic and the synthesized pattern is correct, the same role fires.

(4) The only failure mode is an **ambiguous node**: one where two rules P_1 and P_2 each have equal claim (by priority score) on the same node. In the original graph, tie-breaking is arbitrary (or uses a fixed priority order). In the synthesized graph, R generates code that matches whichever pattern was chosen at tie-break time. If the tie-break order is stable (fixed priority table), the same winner fires. If the priority table has changed between the two F invocations, roles may differ. This contributes at most ε(G) mismatches.

(5) Therefore |R_dist(G) - R_dist(R(F(G)))| ≤ ε(G). ∎

**Corollary.** For programs with no ambiguous nodes (ε(G) = 0), the role distribution is exactly preserved: R_dist(G) = R_dist(R(F(G))). The GNN matrix dimensions (|S|, |O|, |A_act|) are invariants of the round-trip.

---

## 6. Counterexamples and Loss Cases

The following four cases enumerate the primary failure modes of round-trip fidelity and document why they do or do not affect the role isomorphism.

**Case 1: Name-only keyword rules.**  
An ACTION node was assigned its role because its function name contains the token "dispatch." The synthesized code uses the name "act_dispatch" (R's naming template). This still contains "dispatch," so the keyword rule fires again on the synthesized code. **Role preserved.**

**Case 2: Complex dataflow rules.**  
A HIDDEN_STATE node was assigned because it receives WRITES edges from exactly 3 other nodes (a threshold rule). R generates exactly 3 WRITES edges pointing to the synthesized hidden-state node (the matrix B encodes which action nodes write to which state nodes). Running F on the synthesized code counts 3 incoming WRITES edges and fires the HIDDEN_STATE rule. **Role preserved.**

**Case 3: Ambiguous nodes.**  
A function reads from an observation and writes to a state — matching both OBSERVATION (has READS) and ACTION (has WRITES). The original rule table assigns ACTION by priority. R synthesizes code that has both a READS and a WRITES edge. Running F again: the same priority table picks ACTION. **Role preserved, provided priority table is stable.** If the priority table version changes between runs, this case contributes to ε(G).

**Case 4: Zero-edge (isolated) nodes.**  
An isolated function has no structural evidence for any role. F assigns it OBSERVATION by a fallback rule (the default role when no predicate fires). R generates an isolated function with no edges. Running F on the synthesized code: no predicate fires, fallback assigns OBSERVATION again. **Role preserved** — both the original and synthesized isolated nodes get the default role.

**Conclusion.** Empirically, ε(G) ≈ 0 for well-structured codebases in which rule priorities are unambiguous. The measured ε values for control-positive test repos are documented in `ROUNDTRIP_VALIDATION.md`.

---

## 7. Category-Theoretic Interpretation

### 7.1 Lens Semantics

The bidirectional transformation literature provides the closest formal precedent. Foster, Greenwald, Moore, Pierce, and Schmitt (2007) define a *lens* as a pair of functions (get, put) satisfying round-trip laws:

> put(get(s), s) = s   (GetPut)
> get(put(v, s)) = v   (PutGet)

COGANT's (F, R) pair satisfies a weakened version of GetPut: R(F(G)) and G have the same role distribution (Theorem above) but differ in other attributes. PutGet holds approximately: F(R(M)) produces a GNN whose matrices are close to M (same dimensions, similar sparsity patterns) but may differ in exact probability values due to the default initialization choices in R.

The lens formalism suggests that COGANT could be tightened to a proper lens by:
(a) Encoding loss information explicitly in F (a "complement" component in the spirit of Bohannon et al.'s symmetric lenses), and
(b) Using that complement in R to reconstruct the lost details.

This would make (F, R) a **symmetric lens** in the sense of Hedges (2018), yielding the full adjunction.

**Citation:** J.N. Foster, M.B. Greenwald, J.T. Moore, B.C. Pierce, A. Schmitt. "Combinators for Bidirectional Tree Transformations: A Linguistic Approach to the View-Update Problem." *ACM Transactions on Programming Languages and Systems* 29(3), 2007. DOI: [10.1145/1232420.1232424](https://doi.org/10.1145/1232420.1232424)

### 7.2 Adhesive Categories and Graph Rewriting

Program graph transformations (refactoring, inlining, extraction) are naturally modeled as double-pushout (DPO) graph rewriting rules. Lack and Sobocinski (2004) show that DPO rewriting behaves well (confluence, local Church-Rosser) precisely when the ambient category is *adhesive* — i.e., pushouts along monomorphisms are stable under pullback.

The category 𝒫 defined in §2.1 is adhesive: its objects are typed labeled graphs, and the adhesivity conditions are standard results for categories of graphs over a fixed type graph (the role alphabet). This means COGANT's rule system (a collection of DPO rewriting rules that assign roles) has well-defined semantics with predictable confluence properties.

**Implication:** the role assignment process (F restricted to its combinatorial component) can be formally verified for confluence using adhesive-category machinery. Two rule orderings that produce the same role assignment are provably equivalent. Ambiguous nodes (ε(G) > 0) correspond precisely to non-confluent DPO derivations.

**Citation:** S. Lack, P. Sobociński. "Adhesive Categories." *Lecture Notes in Computer Science* 2987, pp. 273–288, FoSSaCS 2004. DOI: [10.1007/978-3-540-24727-2_20](https://doi.org/10.1007/978-3-540-24727-2_20)

### 7.3 Monoidal Functors and Compositional Semantics

Fong and Spivak (2018/2019) develop a general theory of compositional systems using symmetric monoidal categories and wiring diagrams. In their framework, a complex system is built from parts via monoidal composition (⊗), and a functor between monoidal categories is *symmetric monoidal* if it preserves this composition structure.

COGANT's forward functor F can be framed as a symmetric monoidal functor between:

- **Source:** (𝒫, ⊗_import) — the monoidal category of program modules with sequential composition ⊗ defined by import dependency (G_1 ⊗ G_2 = the graph formed by placing G_1 and G_2 side by side and adding IMPORTS edges from G_2 to G_1)
- **Target:** (𝒢, ⊗_product) — the monoidal category of generative model factors with tensor product ⊗ defined by the product of independent factors (M_1 ⊗ M_2 = the Kronecker product of their state and observation spaces)

**Claim (symmetric monoidal functor):** F(G_1 ⊗ G_2) ≅ F(G_1) ⊗ F(G_2) up to the coupling introduced by import edges. When G_2 imports G_1 with no feedback (a directed acyclic import structure), the GNN matrices factor: A_{12} = A_1 ⊗ A_2 (block diagonal). This is the standard conditional independence structure of modular POMDP factorizations.

**Implication:** COGANT is compositional. Analyzing a repository module by module and then combining GNNs produces the same result as analyzing the repository as a whole, provided the inter-module dependency structure is acyclic.

**Citation:** B. Fong, D.I. Spivak. "Seven Sketches in Compositionality: An Invitation to Applied Category Theory." arXiv:1803.05316, Cambridge University Press, 2019. URL: [https://arxiv.org/abs/1803.05316](https://arxiv.org/abs/1803.05316)

### 7.4 Gradient-Based Learning as a Categorical Process

The Active Inference formulation underlying GNN uses free-energy minimization — a form of gradient descent on the variational free energy F = E_q[log q(s) - log p(o, s)]. Cruttwell, Gavranović, Ghani, Wilson, and Zanasi (2021) show that gradient-based learning has a categorical semantics in terms of *reverse derivative categories* and *lenses*, unifying diverse optimization algorithms (SGD, Adam, AdaGrad) under a single framework.

This connection is relevant to COGANT because: if the GNN produced by F(G) is used as the generative model for an Active Inference agent that adapts its behavior, the adaptation process (policy learning) is precisely a gradient-based update in the sense of Cruttwell et al. The categorical semantics ensures that COGANT's output is compatible with principled learning algorithms.

**Citation:** G.S.H. Cruttwell, B. Gavranović, N. Ghani, P. Wilson, F. Zanasi. "Categorical Foundations of Gradient-Based Learning." arXiv:2103.01931, ESOP 2022. DOI: [10.1007/978-3-030-99336-8_1](https://doi.org/10.1007/978-3-030-99336-8_1)

---

## 8. Implications

### 8.1 GNN Metrics as Codebase Quality Proxies

The Role Isomorphism Theorem (§5) justifies a non-obvious claim: properties of the GNN matrices A, B, C, D can serve as proxy metrics for codebase quality.

Specifically:

- **Sparsity of A** (the likelihood matrix) measures how cleanly observation nodes are determined by single hidden state nodes. Dense A corresponds to highly entangled code where observations depend on many hidden states simultaneously — an indicator of low cohesion.
- **Rank of B** (the transition matrix) measures the effective dimensionality of the state transition system. Low-rank B corresponds to simple, predictable control flow. High-rank B indicates complex branching.
- **Entropy of D** (the prior) measures how evenly a module distributes initialization across state nodes. Concentrated D (one dominant prior) may indicate a god-object pattern.
- **Variance of C** (the preference vector) measures how differentiated the module's observation targets are. Flat C indicates no clear goal structure; high-variance C indicates strongly goal-directed code.

These metrics are computable from the GNN in O(|S|·|O| + |S|²·|A_act|) time and require no execution of the code. They are therefore fast, static, and version-control-friendly.

### 8.2 Legibility as Ambiguity Reduction

The Galois connection structure (§4) implies a monotonicity result: improving code legibility (reducing ambiguous nodes, clarifying naming, adding type annotations) reduces ε(G) and tightens the isomorphism. This makes the COGANT round-trip more faithful — the synthesized code R(F(G)) more closely resembles G — which in turn makes the GNN metrics more accurate proxies for the original code structure.

Code quality improvements and isomorphism tightness are thus aligned objectives. COGANT can be used as a legibility auditor: a high ε(G) score indicates regions of the codebase where the structural role of each component is unclear, independent of any particular quality metric.

### 8.3 Functoriality and Incrementality

The categorical framing implies a functoriality property useful for incremental analysis: if G is a subgraph of G' (G ≤ G' in the program-graph preorder), then F(G') restricted to F(G)'s index set should equal F(G), up to the normalization of probability distributions.

This is the **restriction property**: COGANT results for a module should not change when more modules are added to the repository, provided the new modules do not create new edges pointing into the existing module's nodes. This property allows COGANT to run incrementally on changed files without re-analyzing the full repository.

### 8.4 Toward the Full Adjunction

The gap between the current Galois connection and the full adjunction F ⊣ R can be closed by extending the functor pair with an explicit *complement* component. In the symmetric lens sense, F would output not just M = F(G) but the pair (M, c(G)) where c(G) encodes the lost information (implementation bodies, variable names, comments, full type signatures). R would then use both M and c(G) to reconstruct G exactly.

Implementing this extension would make COGANT a *lossless bidirectional transformation system* and establish the full adjunction. This is a target for a future version (`cogant.reverse` v2), and would require a complementary intermediate representation (IR) for the lost information.

---

## References

1. J.N. Foster, M.B. Greenwald, J.T. Moore, B.C. Pierce, A. Schmitt. "Combinators for Bidirectional Tree Transformations: A Linguistic Approach to the View-Update Problem." *ACM Trans. Program. Lang. Syst.* 29(3), Article 17, 2007. DOI: [10.1145/1232420.1232424](https://doi.org/10.1145/1232420.1232424)

2. S. Lack, P. Sobociński. "Adhesive Categories." In *Proc. FoSSaCS 2004*, Lecture Notes in Computer Science, Vol. 2987, pp. 273–288. Springer, 2004. DOI: [10.1007/978-3-540-24727-2_20](https://doi.org/10.1007/978-3-540-24727-2_20)

3. B. Fong, D.I. Spivak. "Seven Sketches in Compositionality: An Invitation to Applied Category Theory." arXiv:1803.05316, Cambridge University Press, 2019. URL: [https://arxiv.org/abs/1803.05316](https://arxiv.org/abs/1803.05316)

4. G.S.H. Cruttwell, B. Gavranović, N. Ghani, P. Wilson, F. Zanasi. "Categorical Foundations of Gradient-Based Learning." arXiv:2103.01931. Published in *Proc. ESOP 2022*, Lecture Notes in Computer Science, Vol. 13240. DOI: [10.1007/978-3-030-99336-8_1](https://doi.org/10.1007/978-3-030-99336-8_1)

5. K. Friston et al. "Active Inference: The Free Energy Principle in Mind, Brain, and Behavior." MIT Press, 2022.

6. Active Inference Institute. "GNN (Generative Model Notation) Specification." Internal format documentation. URL: [https://github.com/ActiveInferenceInstitute](https://github.com/ActiveInferenceInstitute)

---

*Document maintained in `projects_in_progress/cogant/_rnd/`. Empirical validation of ε(G) measurements is in `ROUNDTRIP_VALIDATION.md`. Formal proofs of the monoidal functor claim (§7.3) are deferred to a companion proof document.*
