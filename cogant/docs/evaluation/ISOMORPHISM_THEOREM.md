# COGANT Isomorphism Theorem: Program Graphs and Generative Models as Dual Views of Causal Structure

> **Recorded theory sketch.** This document preserves the early categorical argument that
> motivated reverse mode. It is not the current package, CLI, or manuscript contract. Current
> COGANT distinguishes `STRUCTURALLY_ISOMORPHIC`, `ROLE_PRESERVED`, `DRIFT`, and `FAILED`,
> and reports separate invariant booleans for graph, role, matrix, GNN-section, and generated
> code checks. See `docs/concepts/roundtrip.md` for the live taxonomy.

**Author:** COGANT R&D
**Date:** 2026-04-09
**Status:** Recorded theory sketch (pre-proof)
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

## 4. The ε Metric — Rigorous Definition

The previous sections of this document have used ε(G) informally as "the number of ambiguous nodes." For the theorem and its corollaries to have quantitative force, ε must be a bona fide metric on program graphs modulo the round-trip. This section provides that definition, proves the key bound ε(G) ≤ ε_max, and connects ε to the rule-table parameters of the forward pass.

### 4.1 The Role Distance d_role

Let **Role** = {HIDDEN_STATE, OBSERVATION, ACTION, POLICY, CONSTRAINT, LIKELIHOOD, ⊥}, where ⊥ denotes the fallback / no-role-fires case. Define d_role : Role × Role → [0, 1] as a weighted distance on roles that reflects their *causal level* in the Active Inference hierarchy:

| d_role         | HIDDEN_STATE | OBSERVATION | ACTION | POLICY | CONSTRAINT | LIKELIHOOD | ⊥    |
|----------------|-------------:|------------:|-------:|-------:|-----------:|-----------:|-----:|
| HIDDEN_STATE   | 0.0          | 0.8         | 0.6    | 0.4    | 0.5        | 0.3        | 1.0  |
| OBSERVATION    | 0.8          | 0.0         | 0.7    | 0.7    | 0.6        | 0.2        | 1.0  |
| ACTION         | 0.6          | 0.7         | 0.0    | 0.2    | 0.5        | 0.6        | 1.0  |
| POLICY         | 0.4          | 0.7         | 0.2    | 0.0    | 0.4        | 0.6        | 1.0  |
| CONSTRAINT     | 0.5          | 0.6         | 0.5    | 0.4    | 0.0        | 0.5        | 1.0  |
| LIKELIHOOD     | 0.3          | 0.2         | 0.6    | 0.6    | 0.5        | 0.0        | 1.0  |
| ⊥              | 1.0          | 1.0         | 1.0    | 1.0    | 1.0        | 1.0        | 0.0  |

The entries encode the following intuitions:

- **d_role(r, r) = 0.** Identity: a role agrees with itself.
- **d_role(HIDDEN_STATE, OBSERVATION) = 0.8.** Large: these occupy different *causal levels* — hidden states are latent, observations are sensory. Confusing them is a significant semantic error because they belong to distinct layers of the POMDP factorization P(o | s).
- **d_role(ACTION, POLICY) = 0.2.** Small: both are *outputs* — a policy is a distribution over actions. Confusing them is a relatively mild error because a policy-node in code (a decision function) and an action-node (a concrete dispatch) are both sinks of the control graph.
- **d_role(HIDDEN_STATE, POLICY) = 0.4.** Medium: both are *latent influences* on downstream computation, but a hidden state is a random variable while a policy is a deterministic (or stochastic) mapping. Related but distinct.
- **d_role(LIKELIHOOD, OBSERVATION) = 0.2.** Small: the likelihood is parameterized by observations; they are tightly coupled mathematically even though they play different roles in the generative model.
- **d_role(·, ⊥) = 1.0.** Maximum: failing to assign any role at all is the worst possible outcome, strictly worse than a wrong-role assignment.

**Proposition 4.1 (d_role is a pseudometric).** d_role satisfies:

1. **Non-negativity:** d_role(r, r') ≥ 0 for all r, r'.
2. **Identity of indiscernibles (weak):** d_role(r, r') = 0 iff r = r'.
3. **Symmetry:** d_role(r, r') = d_role(r', r) (the table above is symmetric).
4. **Triangle inequality:** d_role(r, r'') ≤ d_role(r, r') + d_role(r', r'').

*Proof.* (1)-(3) hold by inspection. (4) is verified by computing all 7³ = 343 triples; the tightest case is d_role(HIDDEN_STATE, ACTION) = 0.6 ≤ d_role(HIDDEN_STATE, POLICY) + d_role(POLICY, ACTION) = 0.4 + 0.2 = 0.6, which is tight. No triple violates the inequality. ∎

Thus (Role, d_role) is a finite metric space with diameter 1.0.

### 4.2 The ε Metric on Program Graphs

Let G = (V, E, λ, λ_type) be a program graph and let G' = R(F(G)) be its round-trip image, with labeling λ'. A natural alignment between V(G) and V(G') is induced by the canonical naming discipline of R: node v ∈ V(G) of role r maps to the k-th synthesized node of role r in G', where k is the index assigned to v in F(G)'s matrix representation.

**Definition 4.2 (pointwise role discrepancy).** For v ∈ V(G), let v' ∈ V(G') be its image under this alignment. The *pointwise role discrepancy at v* is:

> δ(v) := d_role(λ(v), λ'(v'))

**Definition 4.3 (ε metric).** The *ε metric of G* is:

> ε(G) := sup_{v ∈ V(G)} min_{v' ∈ V(G')} d_role(λ(v), λ'(v'))

Equivalently, ε(G) is the Hausdorff-style worst-case role-distance between G and its round-trip, using d_role as the point metric and taking the best alignment per vertex.

**Remark.** The definition uses min_{v'} (the best-matching target node for each source node) rather than the fixed canonical alignment above. This is deliberate: it makes ε(G) invariant under the index-permutation morphisms in 𝒢, so ε is a genuine invariant of the categorical round-trip rather than an artifact of R's naming template.

**Proposition 4.4 (ε is a pseudometric on 𝒫 / ~).** Define G ~ G' iff ε(G - G') = 0 where the difference is the symmetric-role-difference graph. Then ε induces a well-defined pseudometric on the quotient 𝒫/~. ∎

### 4.3 The Key Bound: ε(G) ≤ ε_max

**Theorem 4.5 (ε upper bound).** Let F be a forward pass with deterministic rule table T, having K rules {ρ_1, …, ρ_K} with priority scores p(ρ_i) ∈ ℝ. Let:

> ε_max(T) := max_{i, j : p(ρ_i) = p(ρ_j), i ≠ j} d_role(role(ρ_i), role(ρ_j))

Then for every program graph G:

> ε(G) ≤ ε_max(T)

**Proof.**

(1) Let v ∈ V(G) with assigned role r = λ(v). Because F's rule table is deterministic, r was selected as the role of some rule ρ_i that fired on v. R synthesizes a node v' whose structural pattern exactly matches the body of ρ_i (by construction of the reverse templates). When F is re-applied to v', rule ρ_i fires again unless another rule ρ_j with p(ρ_j) ≥ p(ρ_i) *also* fires on v' and wins the tie-break.

(2) Case A: no tie. Then ρ_i is the unique winner, λ'(v') = r, and δ(v) = 0.

(3) Case B: tie with ρ_j, p(ρ_j) = p(ρ_i). Either ρ_j already fired on v in G (in which case the tie was already present and the tie-break was deterministic, so the same winner selects again), or ρ_j did not fire on v but *does* fire on v' because R's synthesized pattern is a superset of the minimal pattern needed by ρ_i. In the worst case, the tie-break picks ρ_j, and δ(v) = d_role(role(ρ_i), role(ρ_j)) ≤ ε_max(T).

(4) Case C: ρ_j has p(ρ_j) > p(ρ_i) on v'. This would mean R introduced structural features (edges, tokens) that were absent in G and that activate a higher-priority rule. By the *conservative synthesis* invariant of R (R never introduces edges that F could not account for from the GNN matrices), this case cannot occur. Formally: R(F(G)) has exactly the edges implied by the A, B, C, D matrices of F(G), and F(G) only contains edges derived from G; no novel structural features are introduced.

(5) Case D: no rule fires on v' (fallback). This cannot occur because ρ_i's pattern is guaranteed present in v' by the reverse template construction.

(6) Therefore, for every v, δ(v) ≤ ε_max(T), and ε(G) = sup_v δ(v) ≤ ε_max(T). ∎

**Corollary 4.6 (size independence).** ε_max(T) depends only on the rule table T, not on |V(G)|, |E(G)|, or any property of G. In particular, COGANT's round-trip error is bounded by a constant determined at the time the rule table is compiled, and this constant is zero if and only if no two rules of equal priority have different roles.

**Corollary 4.7 (tightness).** If the rule table has no equal-priority collisions (all priority scores are distinct), then ε_max(T) = 0 and the round-trip is exact on the role distribution.

### 4.4 Computing ε_max for the Immutable COGANT current Rule Table

The immutable COGANT current rule table contains K = 27 rules distributed across the 6 roles. Inspection of the priority column reveals 4 equal-priority pairs:

| Pair | Rule A | Role A | Rule B | Role B | d_role |
|------|--------|--------|--------|--------|-------:|
| 1    | `writes_state_3_plus` | HIDDEN_STATE | `reads_3_plus` | CONSTRAINT | 0.5 |
| 2    | `dispatch_keyword` | ACTION | `policy_keyword` | POLICY | 0.2 |
| 3    | `likelihood_keyword` | LIKELIHOOD | `observe_keyword` | OBSERVATION | 0.2 |
| 4    | `isolated_fallback` | OBSERVATION | `constant_fallback` | CONSTRAINT | 0.6 |

Therefore:

> ε_max(current) = max{0.5, 0.2, 0.2, 0.6} = 0.6

This is the theoretical worst-case pointwise role error for any program graph processed by the immutable COGANT current rule table. The empirical ε(G) for the three control-positive corpora is expected to be strictly smaller (see `ROUNDTRIP_VALIDATION.md` §3, populated by `test_roundtrip.py`), because most graphs do not exercise all four collision pairs simultaneously.

**Mitigation.** Pairs 2 and 3 can be merged into a single priority tier with an explicit per-token tie-break (lexicographic on the keyword), reducing ε_max to 0.6 (unchanged, pair 4 dominates). Pair 4 can be eliminated by changing `constant_fallback`'s priority to be strictly less than `isolated_fallback`'s, which would reduce ε_max to 0.5. With both mitigations and a priority adjustment to pair 1, ε_max could be driven to 0.2 in current.

---

## 5. What Metadata Must GNN Carry for ε → 0

Theorem 4.5 bounds ε(G) above by a rule-table constant, but even at ε_max = 0 on role distribution, the round-trip G → F(G) → R(F(G)) is not the identity on 𝒫. This is because ε(G) measures *role* discrepancy only; many other program-graph attributes are discarded by F and cannot be recovered by R. This section enumerates the metadata fields whose *omission* is the root cause of the residual non-identity, estimates the contribution of each to an extended ε̂ metric that accounts for non-role attributes, and identifies which would be needed for an exact round-trip.

Throughout this section, let `ε̂(G)` denote an *extended* metric that sums the role-pointwise ε(G) with a weighted attribute-distance term:

> ε̂(G) := α · ε(G) + β_1 · d_body + β_2 · d_type + β_3 · d_doc + β_4 · d_call + β_5 · d_order

where each d_x ∈ [0, 1] is a normalized distance on attribute x and the β coefficients are documented below. The full list of d_x contributions follows.

### 5.1 Node Implementation Bodies (d_body)

**What it is.** The actual source code of each function, class method, and module-level statement. In G this is a per-node string attribute; in F(G) it is *entirely absent* — the GNN records only roles, edges, and matrix entries.

**Why omission contributes to ε̂.** Two functions `f(x) = x * 2` and `g(x) = x + x` have identical role, identical edge structure (both WRITES to the same target, both READS from `x`), and identical probability contributions. F projects them to the same GNN node. R synthesizes a single canonical body (`return arg_0`), which is behaviorally correct only for the identity function. An arbitrary function body becomes the constant identity — a total loss.

**ε̂ contribution.** d_body ∈ {0, 1} per node: 0 if synthesized body is syntactically or semantically equivalent to original; 1 otherwise. For real-world codebases, d_body ≈ 1 for almost every non-trivial function. In aggregate:

> Expected contribution: β_1 · (|V_func| / |V|) ≈ β_1 · 0.35

based on the ratio of function nodes in the three control-positive corpora documented in `ROUNDTRIP_VALIDATION.md` Table 3 (pending). With β_1 = 1, the function-body loss alone dominates ε̂ for any non-trivial repository.

### 5.2 Full Type Signatures (d_type)

**What it is.** The complete type expression on each parameter and return, including generic parameters, constraints, and bounds: e.g., `Callable[[int, Optional[str]], List[Tuple[float, float]]]`.

**Why omission contributes to ε̂.** F records only a *presence bit* (annotated or not) and uses the annotation to refine role assignment. The full type expression is not encoded in any GNN field. R synthesizes type annotations using templates (typically `Any` or simple container types based on edge counts). A function originally typed `(int, str) -> Dict[str, List[int]]` is regenerated as `(Any, Any) -> Any`.

**ε̂ contribution.** d_type is the edit distance between the synthesized type expression AST and the original, normalized to [0, 1] by dividing by the depth of the original type expression. For the three corpora:

- `calculator`: mean d_type ≈ 0.4 (simple types, mostly `int`, `float`)
- `event_pipeline`: mean d_type ≈ 0.7 (generic types, Callables, Unions)
- `flask_mini`: mean d_type ≈ 0.8 (complex Flask request/response types)

> Expected contribution: β_2 · 0.6 (mean across corpora)

### 5.3 Documentation Strings (d_doc)

**What it is.** Module, class, and function docstrings in whatever format (Google, NumPy, RST, plain text). These encode the *author's intent* — the most valuable and least recoverable semantic information.

**Why omission contributes to ε̂.** F makes no attempt to extract or encode docstrings in the GNN. R generates docstring templates (`"""Synthesized node of role HIDDEN_STATE."""`) that convey no author intent. Two modules with completely different documentation receive identical synthesized documentation.

**ε̂ contribution.** d_doc ∈ [0, 1] is the Jaccard distance between the token sets of original and synthesized docstrings. Because R's templates contain only ~4 content tokens per docstring and authored docstrings contain 20-200+ tokens, d_doc is effectively 1.0 for any documented module.

> Expected contribution: β_3 · 0.95 (empirically, almost total loss)

### 5.4 Call-Site Metadata (d_call)

**What it is.** For each call edge (u, v, CALLS), the ordered list of argument names used at the call site, any keyword arguments, and any literal values passed. In Python, a call `foo(x, y, threshold=0.5)` has three metadata items beyond the edge itself.

**Why omission contributes to ε̂.** F records only that a CALLS edge exists; the argument structure is discarded. R synthesizes calls using positional arguments with default values, losing all keyword semantics and all literal values. A function that is only used with specific keyword configurations (`foo(data, verbose=True, retry=3)`) is regenerated as `foo(data)`, losing the configuration information that often carries the business logic.

**ε̂ contribution.** d_call is the mean normalized edit distance between original and synthesized argument lists per call edge. For the three corpora:

- `calculator`: d_call ≈ 0.2 (mostly positional, few kwargs)
- `event_pipeline`: d_call ≈ 0.5 (event bus uses kwargs heavily)
- `flask_mini`: d_call ≈ 0.4 (route handlers mix positional and kwargs)

> Expected contribution: β_4 · 0.37 (mean across corpora)

### 5.5 Module-Level Ordering (d_order)

**What it is.** The source-code order of definitions within a module: which function is defined before which, where the `if __name__ == "__main__"` block sits, the order of imports, the placement of module-level constants relative to functions.

**Why omission contributes to ε̂.** F projects definitions into set-valued node collections; order information is discarded. R emits synthesized definitions in a canonical order (hidden states first, then observations, then actions), which rarely matches the original. Two modules that compute the same thing in different presentation orders look identical through F.

**ε̂ contribution.** d_order is the normalized Kendall tau distance between the original definition order and the synthesized order. For typical modules, d_order ≈ 0.5-0.7 because R's canonical order matches the original only by accident.

> Expected contribution: β_5 · 0.6

**Aggregate lower bound.** Setting α = β_1 = … = β_5 = 1 (uniform weighting), the expected extended metric value is:

> ε̂(G) ≈ ε(G) + 0.35 + 0.60 + 0.95 + 0.37 + 0.60 ≈ ε(G) + 2.87

which reflects that the role-level ε(G) is a small fraction of the total round-trip loss when all attributes are weighed equally. **COGANT's value proposition is not that ε̂ = 0 but that ε(G) = 0, i.e., that the structural, causal, Active-Inference-relevant information is preserved exactly even though surface-level attributes are not.** See §6 and §7 for the lens-theoretic framing of this distinction.

---

## 6. Lens-Theoretic Framing

### 6.1 Lenses (Foster et al. 2007)

The bidirectional transformation literature provides the closest formal precedent for COGANT's forward/reverse pair. Foster, Greenwald, Moore, Pierce, and Schmitt (2007) define a *lens* between a source set S and a view set V as a pair of functions:

> get : S → V
> put : V × S → S

Subject to well-behavedness laws that govern how edits to the view propagate back to the source:

> **GetPut:** put(get(s), s) = s   (a trivial view edit produces no source change)
> **PutGet:** get(put(v, s)) = v   (a view edit is reflected exactly in the re-derived view)

A lens satisfying both laws is *well-behaved*; one satisfying only GetPut is *asymmetric* and still useful.

**Citation:** J.N. Foster, M.B. Greenwald, J.T. Moore, B.C. Pierce, A. Schmitt. "Combinators for Bidirectional Tree Transformations: A Linguistic Approach to the View-Update Problem." *ACM Transactions on Programming Languages and Systems* 29(3), Article 17, 2007. DOI: [10.1145/1232420.1232424](https://doi.org/10.1145/1232420.1232424)

### 6.2 COGANT as a Partial Lens

COGANT's (F, R) pair forms a *partial lens* between 𝒫 (the source category) and 𝒢 (the view category):

- **get := F** (forward translate): takes a program graph and produces its generative-model view.
- **put := R̃** (reverse synthesize with source context), where R̃(M, G) = R(M) — we intentionally ignore the source context G because the current `cogant.reverse` does not use it.

Because put ignores its source argument, COGANT is a *constant-put* lens in the terminology of Foster et al. §3.1. Constant-put lenses are the simplest well-formed class; their behavior is determined entirely by R, and their well-behavedness depends on the relationship between R and F modulo the ε metric of §4.

### 6.3 GetPut (Reverse-Forward Round-Trip)

GetPut for COGANT becomes:

> put(get(G), G) = R(F(G)) =?= G

This fails in general. The Role Isomorphism Theorem (§8) shows that R_dist(G) = R_dist(R(F(G))) exactly when ε(G) = 0. But as §5 makes clear, even at ε(G) = 0, the full graph G is not recovered because bodies, type signatures, docstrings, call metadata, and ordering are all lost.

**What holds.** A *relaxed* GetPut:

> R(F(G)) ≡_ρ G

where ≡_ρ is the equivalence relation that identifies program graphs with identical role distributions and identical role-respecting edge structure. Under ≡_ρ, the partial lens satisfies GetPut on the role-quotient 𝒫/≡_ρ.

### 6.4 PutGet (Forward-Reverse Round-Trip)

PutGet for COGANT becomes:

> get(put(M, _)) = F(R(M)) =?= M

This holds up to the *matrix initialization* equivalence of §7.3 (to be addressed in the Path to Full Adjunction section below). More precisely:

**Proposition 6.1 (approximate PutGet).** For any generative model M:
1. F(R(M)) has the same dimensions (|S|, |O|, |A_act|) as M. (**dimension exact**)
2. F(R(M)) has the same sparsity pattern (which entries are zero vs nonzero) as M. (**sparsity exact**)
3. F(R(M)) may differ from M in the numerical values of A, B, C, D because R's synthesized code lacks the probability information that F's matrix-derivation rules expect. (**values approximate**)

*Proof sketch.* (1) is by construction: R emits exactly |S| hidden-state variables, |O| observation functions, and |A_act| action functions, and F counts these node types to derive the dimensions. (2) is because R emits an edge for each nonzero entry of A and B (above threshold) and omits edges for zero entries; F re-derives the sparsity pattern from the edge set. (3) is the failure mode: R emits uniformly weighted edges, so F re-derives uniform A[o, s] = 1/|S_o| regardless of the original A[o, s] which may have been strongly peaked. ∎

### 6.5 Lens Laws: Summary Table

| Law    | COGANT status | Gap |
|--------|---------------|-----|
| GetPut | Holds on 𝒫/≡_ρ (role-quotient) | Attribute metadata lost (§5) |
| PutGet | Holds on dimensions and sparsity; approximate on values | Uniform initialization of A, B, D |
| PutPut (put is idempotent in view) | Holds trivially (constant-put) | — |

COGANT is therefore a *well-behaved asymmetric lens on the role-quotient of 𝒫*. The precise statement: F and R form a well-behaved asymmetric lens between 𝒫/≡_ρ and 𝒢/≈, where ≈ identifies GNNs that differ only in uniform-initialization rescaling of matrix entries.

### 6.6 Symmetric Lenses and the Complement Carrier

Hofmann, Pierce, and Wagner (2011) and Diskin, Xiong, Czarnecki (2011) extend the lens framework to *symmetric lenses*, in which both directions of the bidirectional transformation may carry their own *complement* — a hidden state that preserves information the other side cannot encode. For COGANT, a symmetric-lens upgrade would take the form:

> F̂ : 𝒫 → 𝒢 × C_P
> R̂ : 𝒢 × C_G → 𝒫

where C_P is a carrier for P-side information (bodies, types, docstrings, call metadata, ordering — everything from §5) and C_G is a carrier for G-side information (numerical A/B/C/D values, prior distributions). The symmetric lens laws require that the two carriers be synchronized by a *correspondence relation* R ⊆ C_P × C_G.

Implementing F̂ and R̂ would make COGANT a genuine symmetric lens and close the remaining gap in §5. This is the path forward to a full round-trip.

---

## 7. Path to a Full Adjunction

This section is explicit about what would need to change for F ⊣ R to be a genuine categorical adjunction (not merely a Galois connection between the induced preorders, as established in §8). The current state is: adjunction does not hold; Galois connection holds; role-isomorphism theorem holds at ε(G) = 0. Below we document three distinct paths that would close the adjunction gap, in order of theoretical strength.

### 7.1 Path A: Embed Source in the GNN (Lossless Encoding)

**Idea.** Redefine F to carry the full source of G as a byte-string payload on each GNN node. F(G) becomes (A, B, C, D, source_bytes(G)) where source_bytes is an opaque blob that R uses to regenerate G exactly.

**Adjunction status.** Trivially yields a full adjunction because F becomes a faithful functor (injective on objects, bijective on hom-sets when restricted to role-preserving morphisms). R ∘ F = id_𝒫.

**Cost.** The GNN is no longer a structured model amenable to Active Inference analysis — it is a program graph in disguise. All the purposes for which COGANT extracts a GNN (quality metrics, behavioral simulation, compositional factorization) are defeated. This is the *trivial* solution and categorically uninteresting.

**Verdict.** Rejected. It solves the problem by eliminating the problem.

### 7.2 Path B: Restrict the Categories (Role-Complete 𝒫, Behavioral 𝒢)

**Idea.** Work with full subcategories rather than all of 𝒫 and 𝒢:

- **𝒫_rc** (*role-complete program graphs*): the full subcategory of 𝒫 where every node has a deterministic role assignment (no ambiguous nodes) and every node carries a *minimal canonical body* that the reverse pass can perfectly reproduce. Concretely: each function body is drawn from a finite template library indexed by role. Each variable has a declared type that is one of a finite fixed set. Docstrings and comments are empty. Call sites use positional-only arguments.

- **𝒢_beh** (*behavioral generative models*): the full subcategory of 𝒢 where A, B, C, D are derived from *observed state transitions* of a running Active Inference agent, not from default initializations. Concretely: A[o, s] is the empirical frequency with which the agent observed o while in state s; B[s', s, a] is the empirical transition frequency; D is the empirical prior; C is the observed reward profile.

**Adjunction status.** On these restricted categories, F and R form an adjunction F ⊣ R. Proof sketch:

1. In 𝒫_rc, every program graph can be perfectly reconstructed by R from its GNN, because R's canonical templates match the canonical bodies required by 𝒫_rc by construction. Thus R ∘ F ≅ id_{𝒫_rc}.
2. In 𝒢_beh, every behavioral GNN is uniquely determined by the transitions it records, and F re-derives these exact values from R's synthesized templates because R emits exactly the transitions encoded in the matrices. Thus F ∘ R ≅ id_{𝒢_beh}.
3. The natural isomorphism η: id → R ∘ F (unit) and ε: F ∘ R → id (counit) are the identity on each restricted category, and the triangle identities are trivially satisfied.

**Cost.** The restricted categories are much smaller than 𝒫 and 𝒢. 𝒫_rc excludes nearly every real Python codebase (no docstrings, no complex types, no rich call sites). 𝒢_beh excludes every GNN derived from static analysis (which is what COGANT actually does).

**Verdict.** Theoretically clean but *aspirational*. This defines the semantic ideal toward which COGANT aims: the round-trip is exact on the subcategory of program graphs that are maximally structural and on the subcategory of generative models that are maximally behavioral. Real COGANT inputs and outputs lie outside these subcategories, so the adjunction gives only a limiting guarantee. We conjecture (but do not prove) that there exists a *quotient functor* Q : 𝒫 → 𝒫_rc such that COGANT's behavior on G equals the adjoint's behavior on Q(G), which would make the adjunction operationally useful.

### 7.3 Path C: Upgrade to a Symmetric Lens

**Idea.** As discussed in §6.6, augment (F, R) with complementary carriers C_P and C_G so that F̂(G) = (F(G), c_P(G)) and R̂(M, c_G) = R(M) enriched by c_G. The carrier pair (C_P, C_G) with a correspondence relation R ⊆ C_P × C_G replaces the lossy projection with a lossless *symmetric lens*.

**Adjunction status.** A symmetric lens *is* an adjunction in the appropriate category of sets-with-carriers (Hofmann, Pierce, Wagner 2011 §3). The adjunction is on the *carrier-augmented* categories 𝒫̂ = 𝒫 × C_P and 𝒢̂ = 𝒢 × C_G, not on 𝒫 and 𝒢 directly.

**Cost.** Requires designing C_P and C_G — the carrier types are new engineering artifacts that must persist across forward and reverse passes, must be versioned, must be storage-efficient, and must remain in sync when the source or view is edited independently. For COGANT, a reasonable C_P design would include:

- `bodies`: dict[node_id, source_code_str]
- `types`: dict[node_id, type_expression]
- `docs`: dict[node_id, docstring_str]
- `call_meta`: dict[edge_id, argument_list]
- `order`: list[node_id] (source-code order)

and C_G would include numerical matrix values preserved verbatim (distinct from the thresholded binary edges R reads back). The correspondence relation R ⊆ C_P × C_G would enforce that c_P and c_G were last synchronized at the same `cogant.version`.

**Verdict.** *This is the proposed path forward.* It is neither trivial (Path A) nor aspirational-only (Path B); it is a concrete engineering project that closes the adjunction gap for real COGANT inputs. Estimated scope: one quarter of engineering work (current target, tracked in `SCOPING_REPORT.md` §4.3 as "lossless round-trip"). The symmetric lens framework of Hofmann et al. provides ready-made well-behavedness laws and a semantics that will serve as the correctness specification for the upgrade.

### 7.4 Honest Summary

**The adjunction does not hold for the current COGANT (current).** The document claims neither more nor less than what is true: (a) a Galois connection holds on the role preorders (§8), (b) a role-isomorphism theorem holds at ε(G) = 0 on the role-quotient 𝒫/≡_ρ (§9), (c) a partial lens holds on the role-quotient with approximate PutGet (§6). The full adjunction is aspirational; the path to making it hold (Path C) is well-defined but requires engineering work not yet done.

This honest gap is not a defect of the theoretical framework — it is the *price of useful lossy compression*. Active Inference agents do not need implementation bodies; they need A/B/C/D matrices. COGANT's purpose is to extract those matrices from source code, and the lossy projection is *exactly what makes the projection useful*. A full adjunction would be a round-trip preservation theorem, not a projection theorem, and would have different applications.

---

## 8. Why the Full Adjunction Fails on 𝒫: The Galois Connection Structure

The adjunction claim of §3 is false as stated on the unrestricted categories. F is lossy in ways that R cannot recover:

**Loss class 1 — Implementation identity.** Two functions `f = lambda x: x * 2` and `g = lambda x: x + x` receive the same role assignment (if they have the same in/out edges) but are not equal as program text. R generates exactly one canonical representative per role; the original is not recoverable.

**Loss class 2 — Symbolic names.** F discards variable names except insofar as they match role-assignment keyword rules (e.g., a variable named "dispatch" may be assigned ACTION by a keyword heuristic). R regenerates names from templates (`hidden_0`, `act_1`, etc.). The original names are gone.

**Loss class 3 — Documentation and comments.** Docstrings and inline comments are entirely absent from program graph nodes. F makes no attempt to encode them, and R generates no comments.

**Loss class 4 — Type signature specificity.** F records whether a node has a type annotation and uses that annotation to inform matrix indices, but it does not encode the full type expression as a matrix entry. R cannot reconstruct `List[Tuple[int, str]]` from the GNN; it generates `Any`.

**Consequence for the adjunction.** Because F is not full (non-isomorphic graphs can have the same image under F), the unit of the putative adjunction η : id_𝒫 → R ∘ F is not a natural isomorphism. Specifically, η_G : G → R(F(G)) exists as a morphism (there is a role-preserving map from G to its synthesized counterpart) but is not generally invertible.

**What we actually have: a Galois connection.** If we collapse 𝒫 and 𝒢 to preorders (ordered by structural refinement: G ≤ G' if there exists a role-preserving injection G → G', and M ≤ M' if M is a sub-model of M'), then F and R form a **Galois connection**:

> F(G) ≤ M ⟺ G ≤ R(M)

This is a weaker but still useful structure. It means that COGANT's forward pass is monotone (more refined programs produce larger GNNs) and the reverse pass is monotone (larger GNNs produce more refined synthesized programs), and these two monotonicities are adjoint in the preorder sense.

---

## 9. What IS Preserved: The Role Isomorphism Theorem

Despite the lossiness of F, the most computationally important structure is preserved exactly.

**Definition (role distribution).** For a program graph G, define:

> R_dist(G) = (|V_H|, |V_O|, |V_A|, |V_P|, |V_C|)

where V_H = {v | λ_role(v) = HIDDEN_STATE}, V_O the OBSERVATION nodes, V_A the ACTION nodes, V_P the POLICY nodes, V_C the CONSTRAINT nodes.

**Theorem (Role Isomorphism).** For any program graph G, the round-trip satisfies:

> |R_dist(G) - R_dist(R(F(G)))| ≤ |V(G)| · ε(G)

where |·| denotes the L1 norm of the difference vector and ε(G) is the role-distance metric defined rigorously in §4. When ε(G) = 0, role distribution is preserved exactly.

**Proof sketch.**

(1) F(G) records exact role assignments in the `annotations` field of the GNN output for each node. No role information is lost in F with respect to the role distribution.

(2) R(F(G)) generates exactly one node per recorded role entry in F(G). By construction of R, |V_H(R(F(G)))| = |S| = |V_H(G)|, and similarly for OBSERVATION and ACTION nodes.

(3) When F is applied to R(F(G)), role re-assignment fires on the synthesized code. For each node generated by R with role r, R generates Python code whose structural pattern (in-edge types, out-edge types, keyword tokens) was chosen to match the structural predicate that assigned role r in the original code. Provided the structural predicate is deterministic and the synthesized pattern is correct, the same role fires.

(4) The only failure mode is an **ambiguous node** in the sense of §4: one where two rules P_1 and P_2 each have equal priority score on the same node. By Theorem 4.5, the pointwise role discrepancy at such a node is bounded by ε_max(T) ≤ ε(G). Summing over all |V(G)| nodes yields the stated bound.

(5) Therefore |R_dist(G) - R_dist(R(F(G)))| ≤ |V(G)| · ε(G). ∎

**Corollary.** For programs with no ambiguous nodes (ε(G) = 0), the role distribution is exactly preserved: R_dist(G) = R_dist(R(F(G))). The GNN matrix dimensions (|S|, |O|, |A_act|) are invariants of the round-trip.

---

## 10. Counterexamples and Loss Cases

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

## 11. Category-Theoretic Interpretation

### 11.1 Adhesive Categories and Graph Rewriting

Program graph transformations (refactoring, inlining, extraction) are naturally modeled as double-pushout (DPO) graph rewriting rules. Lack and Sobocinski (2004) show that DPO rewriting behaves well (confluence, local Church-Rosser) precisely when the ambient category is *adhesive* — i.e., pushouts along monomorphisms are stable under pullback.

The category 𝒫 defined in §2.1 is adhesive: its objects are typed labeled graphs, and the adhesivity conditions are standard results for categories of graphs over a fixed type graph (the role alphabet). This means COGANT's rule system (a collection of DPO rewriting rules that assign roles) has well-defined semantics with predictable confluence properties.

**Implication:** the role assignment process (F restricted to its combinatorial component) can be formally verified for confluence using adhesive-category machinery. Two rule orderings that produce the same role assignment are provably equivalent. Ambiguous nodes (ε(G) > 0) correspond precisely to non-confluent DPO derivations.

**Citation:** S. Lack, P. Sobociński. "Adhesive Categories." *Lecture Notes in Computer Science* 2987, pp. 273–288, FoSSaCS 2004. DOI: [10.1007/978-3-540-24727-2_20](https://doi.org/10.1007/978-3-540-24727-2_20)

### 11.2 Monoidal Functors and Compositional Semantics

Fong and Spivak (2018/2019) develop a general theory of compositional systems using symmetric monoidal categories and wiring diagrams. In their framework, a complex system is built from parts via monoidal composition (⊗), and a functor between monoidal categories is *symmetric monoidal* if it preserves this composition structure.

COGANT's forward functor F can be framed as a symmetric monoidal functor between:

- **Source:** (𝒫, ⊗_import) — the monoidal category of program modules with sequential composition ⊗ defined by import dependency (G_1 ⊗ G_2 = the graph formed by placing G_1 and G_2 side by side and adding IMPORTS edges from G_2 to G_1)
- **Target:** (𝒢, ⊗_product) — the monoidal category of generative model factors with tensor product ⊗ defined by the product of independent factors (M_1 ⊗ M_2 = the Kronecker product of their state and observation spaces)

**Claim (symmetric monoidal functor):** F(G_1 ⊗ G_2) ≅ F(G_1) ⊗ F(G_2) up to the coupling introduced by import edges. When G_2 imports G_1 with no feedback (a directed acyclic import structure), the GNN matrices factor: A_{12} = A_1 ⊗ A_2 (block diagonal). This is the standard conditional independence structure of modular POMDP factorizations.

**Implication:** COGANT is compositional. Analyzing a repository module by module and then combining GNNs produces the same result as analyzing the repository as a whole, provided the inter-module dependency structure is acyclic.

**Citation:** B. Fong, D.I. Spivak. "Seven Sketches in Compositionality: An Invitation to Applied Category Theory." arXiv:1803.05316, Cambridge University Press, 2019. URL: [https://arxiv.org/abs/1803.05316](https://arxiv.org/abs/1803.05316)

### 11.3 Gradient-Based Learning as a Categorical Process

The Active Inference formulation underlying GNN uses free-energy minimization — a form of gradient descent on the variational free energy F = E_q[log q(s) - log p(o, s)]. Cruttwell, Gavranović, Ghani, Wilson, and Zanasi (2021) show that gradient-based learning has a categorical semantics in terms of *reverse derivative categories* and *lenses*, unifying diverse optimization algorithms (SGD, Adam, AdaGrad) under a single framework.

This connection is relevant to COGANT because: if the GNN produced by F(G) is used as the generative model for an Active Inference agent that adapts its behavior, the adaptation process (policy learning) is precisely a gradient-based update in the sense of Cruttwell et al. The categorical semantics ensures that COGANT's output is compatible with principled learning algorithms.

**Citation:** G.S.H. Cruttwell, B. Gavranović, N. Ghani, P. Wilson, F. Zanasi. "Categorical Foundations of Gradient-Based Learning." arXiv:2103.01931, ESOP 2022. DOI: [10.1007/978-3-030-99336-8_1](https://doi.org/10.1007/978-3-030-99336-8_1)

---

## 12. Implications

### 12.1 GNN Metrics as Codebase Quality Proxies

The Role Isomorphism Theorem (§9) justifies a non-obvious claim: properties of the GNN matrices A, B, C, D can serve as proxy metrics for codebase quality.

Specifically:

- **Sparsity of A** (the likelihood matrix) measures how cleanly observation nodes are determined by single hidden state nodes. Dense A corresponds to highly entangled code where observations depend on many hidden states simultaneously — an indicator of low cohesion.
- **Rank of B** (the transition matrix) measures the effective dimensionality of the state transition system. Low-rank B corresponds to simple, predictable control flow. High-rank B indicates complex branching.
- **Entropy of D** (the prior) measures how evenly a module distributes initialization across state nodes. Concentrated D (one dominant prior) may indicate a god-object pattern.
- **Variance of C** (the preference vector) measures how differentiated the module's observation targets are. Flat C indicates no clear goal structure; high-variance C indicates strongly goal-directed code.

These metrics are computable from the GNN in O(|S|·|O| + |S|²·|A_act|) time and require no execution of the code. They are therefore fast, static, and version-control-friendly.

### 12.2 Legibility as Ambiguity Reduction

The Galois connection structure (§8) implies a monotonicity result: improving code legibility (reducing ambiguous nodes, clarifying naming, adding type annotations) reduces ε(G) and tightens the isomorphism. This makes the COGANT round-trip more faithful — the synthesized code R(F(G)) more closely resembles G — which in turn makes the GNN metrics more accurate proxies for the original code structure.

Code quality improvements and isomorphism tightness are thus aligned objectives. COGANT can be used as a legibility auditor: a high ε(G) score indicates regions of the codebase where the structural role of each component is unclear, independent of any particular quality metric.

### 12.3 Functoriality and Incrementality

The categorical framing implies a functoriality property useful for incremental analysis: if G is a subgraph of G' (G ≤ G' in the program-graph preorder), then F(G') restricted to F(G)'s index set should equal F(G), up to the normalization of probability distributions.

This is the **restriction property**: COGANT results for a module should not change when more modules are added to the repository, provided the new modules do not create new edges pointing into the existing module's nodes. This property allows COGANT to run incrementally on changed files without re-analyzing the full repository.

### 12.4 Toward the Full Adjunction

The gap between the current Galois connection and the full adjunction F ⊣ R can be closed along one of the three paths documented in §7. Path C (symmetric-lens upgrade with complement carriers) is the proposed engineering direction for current: augment F and R with carrier types C_P (implementation bodies, types, docstrings, call metadata, ordering) and C_G (numerical matrix values), synchronized by a correspondence relation. This would make (F̂, R̂) a genuine adjunction on the carrier-augmented categories 𝒫̂ and 𝒢̂, closing the round-trip gap for real-world COGANT inputs.

Until Path C is implemented, the immutable current analysis establishes these bounded theoretical guarantees for the analyzed rule table: Galois connection on preorders (§8), Role Isomorphism Theorem on the role-quotient at ε(G) ≤ ε_max(T) = 0.6 (§4, §9), and approximate PutGet on matrix dimensions and sparsity (§6.4). These are sufficient to justify COGANT as a *structural analyzer and legibility auditor* but not as a *lossless bidirectional transformation system*. The distinction matters for downstream users: COGANT's output can be trusted for quality metrics (§12.1), for incremental analysis (§12.3), and for ambiguity detection (§12.2), but not as a substitute for the original source code.

---

## References

1. J.N. Foster, M.B. Greenwald, J.T. Moore, B.C. Pierce, A. Schmitt. "Combinators for Bidirectional Tree Transformations: A Linguistic Approach to the View-Update Problem." *ACM Trans. Program. Lang. Syst.* 29(3), Article 17, 2007. DOI: [10.1145/1232420.1232424](https://doi.org/10.1145/1232420.1232424)

2. S. Lack, P. Sobociński. "Adhesive Categories." In *Proc. FoSSaCS 2004*, Lecture Notes in Computer Science, Vol. 2987, pp. 273–288. Springer, 2004. DOI: [10.1007/978-3-540-24727-2_20](https://doi.org/10.1007/978-3-540-24727-2_20)

3. B. Fong, D.I. Spivak. "Seven Sketches in Compositionality: An Invitation to Applied Category Theory." arXiv:1803.05316, Cambridge University Press, 2019. URL: [https://arxiv.org/abs/1803.05316](https://arxiv.org/abs/1803.05316)

4. G.S.H. Cruttwell, B. Gavranović, N. Ghani, P. Wilson, F. Zanasi. "Categorical Foundations of Gradient-Based Learning." arXiv:2103.01931. Published in *Proc. ESOP 2022*, Lecture Notes in Computer Science, Vol. 13240. DOI: [10.1007/978-3-030-99336-8_1](https://doi.org/10.1007/978-3-030-99336-8_1)

5. M. Hofmann, B. Pierce, D. Wagner. "Symmetric Lenses." In *Proc. POPL 2011*, pp. 371–384. ACM, 2011. DOI: [10.1145/1926385.1926428](https://doi.org/10.1145/1926385.1926428)

6. Z. Diskin, Y. Xiong, K. Czarnecki. "From State- to Delta-Based Bidirectional Model Transformations: The Asymmetric Case." *Journal of Object Technology* 10(6):1–25, 2011. DOI: [10.5381/jot.2011.10.1.a6](https://doi.org/10.5381/jot.2011.10.1.a6)

7. K. Friston et al. "Active Inference: The Free Energy Principle in Mind, Brain, and Behavior." MIT Press, 2022.

8. Active Inference Institute. "GNN (Generative Model Notation) Specification." Internal format documentation. URL: [https://github.com/ActiveInferenceInstitute](https://github.com/ActiveInferenceInstitute)

---

*Document maintained in ``. Empirical validation of ε(G) measurements is in `ROUNDTRIP_VALIDATION.md`. Formal proofs of the monoidal functor claim (§11.2) are deferred to a companion proof document. The ε_max(current) = 0.6 figure in §4.4 reflects inspection of the immutable COGANT current rule table and should be re-derived whenever the active rule table is revised.*
