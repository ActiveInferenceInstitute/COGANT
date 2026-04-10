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


---

*Full proof continues in `../evaluation/ISOMORPHISM_THEOREM.md`.*
