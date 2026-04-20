# Appendix D — Inference Loop Mathematics {#sec:S04-appendix-inference-mathematics}

This appendix formalizes the discrete-time active inference loop executed
by `cogant process` on the extracted A/B/C/D matrices and reported
empirically in [`../cogant/docs/evaluation/EMPIRICAL_CLAIM.md`](../cogant/docs/evaluation/EMPIRICAL_CLAIM.md)
(VFE trace tables per zoo fixture). The variational free-energy discussion in
[`05_conclusion.md`](05_conclusion.md) ties the same functions to shipped capabilities. The
formalism follows Da Costa et al. (2020) and the pymdp reference
(Heins et al., 2022); we restate it here in notation consistent with
COGANT's `cogant.process` module.

### D.1 POMDP formulation

The extracted model is a discrete-time Partially Observable Markov Decision
Process `(S, O, A, π, A_mat, B_mat, C_mat, D_mat)` with:

> **S = {s_1, …, s_|S|}** — finite set of hidden states. Cardinality is
> the product of factor cardinalities: `|S| = ∏_f |S_f|`.
>
> **O = {o_1, …, o_|O|}** — finite set of observations. For multi-modality
> models, `|O| = ∏_m |O_m|`.
>
> **A ⊆ {1, …, |A|}** — finite set of discrete actions (control states).
>
> **π ∈ Π** — policies, i.e. finite sequences
> `(a_0, a_1, …, a_{T−1}) ∈ A^T` over horizon `T`.
>
> **A_mat ∈ ℝ^{|O|×|S|}**, `A_mat[o, s] = P(o | s)` — likelihood.
>
> **B_mat ∈ ℝ^{|S|×|S|×|A|}**, `B_mat[s', s, a] = P(s' | s, a)` —
> state‑transition tensor.
>
> **C_mat ∈ ℝ^{|O|}**, `C_mat[o]` — log‑preference over observations.
>
> **D_mat ∈ ℝ^{|S|}**, `D_mat[s] = P(s_0 = s)` — prior over initial states.

All COGANT-extracted matrices satisfy the stochasticity conditions
`∑_o A_mat[o, s] = 1` for all `s` and `∑_{s'} B_mat[s', s, a] = 1` for all
`(s, a)`; the GNN validator enforces these invariants at emission time.

### D.2 Variational free energy functional

Let `Q(s)` be an approximate posterior over hidden states and `P(o, s)` the
joint distribution defined by the generative model
`P(o, s) = A_mat[o, s] · D_mat[s]`. The variational free energy (VFE) is

> **F[Q] = 𝔼_{Q(s)}[ log Q(s) − log P(o, s) ]**
>
>       = **KL( Q(s) ∥ P(s | o) ) − log P(o)**

The second equality (the "Helmholtz decomposition") shows that minimizing
`F` is equivalent to finding the posterior that best approximates
`P(s | o)` up to a constant `log P(o)` that depends only on the observation.
Equivalently,

> **F[Q] = 𝔼_{Q(s)}[−log A_mat[o, s]] − H[Q(s)] − 𝔼_{Q(s)}[log D_mat[s]]**

decomposes VFE into three interpretable terms: the expected negative
log‑likelihood (prediction error), the negative entropy of the posterior
(ambiguity), and the expected log‑prior (complexity). COGANT's `cogant
process` computes this decomposition directly from the extracted matrices.

### D.3 Variational inference via belief propagation

For a single-factor discrete POMDP with observation `o_t` at time `t`, the
posterior update is the normalized product

> **Q(s_t) ∝ A_mat[o_t, s_t] · Q(s_{t|t−1})**

where `Q(s_{t|t−1})` is the predicted state (the result of applying the
transition tensor to the previous posterior: `Q(s_{t|t−1}) = ∑_{s_{t−1}}
B_mat[s_t, s_{t−1}, a_{t−1}] · Q(s_{t−1})`). Because the posterior is a
categorical distribution over a finite set, the update is exact — there is
no approximation — and convergence of the inner loop is trivial
(single step). The belief propagation terminology is retained because the
formalism extends to factor-graph inference when the hidden state is
factorized into multiple independent factors.

### D.4 VFE = 0.0 in the identity model

The zoo/01\_simple\_state fixture demonstrates the identity case where
VFE converges to exactly zero. The extracted model has

> `|S| = 1` (single factor, single cardinality after aggregation)
>
> `A_mat = [[1.0]]` (identity likelihood)
>
> `B_mat[·, ·, a] = [[1.0]]` for all `a` (identity transition, all actions)
>
> `C_mat = [0.0]` (no preference gradient)
>
> `D_mat = [1.0]` (fully certain prior)

Substituting into the VFE decomposition:

> `F = 𝔼_{Q(s)}[−log A_mat[o, s]] − H[Q(s)] − 𝔼_{Q(s)}[log D_mat[s]]`
>
>   = `−log(1.0) − 0 − log(1.0)`
>
>   = **0.0**

The three terms vanish separately: the prediction error is zero because
`A_mat[0, 0] = 1.0` and the observation is guaranteed, the entropy is zero
because `Q(s) = [1.0]` is a Dirac delta on the single state, and the
complexity term is zero because the prior is also a Dirac. This is the
correct and expected behaviour for any fixture where the extracted model is
a degenerate single-state POMDP; the ten-step trace in
`../cogant/docs/evaluation/EMPIRICAL_CLAIM.md` confirms `F = −0.000000` at every step, which is
the expected numerical signature (the `−0` arises from the sign of
`log(1.0) = 0` after the negation in the prediction-error term).

### D.5 Other regimes observed in the empirical runs

Three qualitatively distinct VFE regimes appear in the four zoo fixtures
reported in `../cogant/docs/evaluation/EMPIRICAL_CLAIM.md`:

1. **`VFE = 0.0` (flat certainty).** `zoo/01_simple_state` and
   `zoo/02_observer` — identity A/B with `D = [1.0]`, no free energy
   gradient, no belief update happens because the prior is already exact.

2. **`VFE = 23.025851` (maximum uncertainty floor).** `zoo/04_pomdp_minimal`
   — observation-only GNN where the likelihood matrix `A_mat` is empty
   (the extracted model has no hidden-state factor). The runtime evaluates
   `−log(1e-10) = 23.025850929940457` as the floor for an unresolvable
   observation, which is the expected floor for the `cogant.process`
   implementation when the likelihood is vacuously defined.

3. **`VFE → 0.798508` (converging plateau).** `zoo/06_hierarchical` —
   two-factor hierarchical model with discriminative likelihood
   `A_mat = [[0.9, 0.1], [0.1, 0.9]]`. The posterior collapses from the
   uniform prior `D_mat = [0.5, 0.5]` to the certain state
   `Q(s) = [1.0, 0.0]` by `t = 2`; VFE rises from `F(t=0) = 0.751435` to
   the equilibrium `F(t≥4) = 0.798508`. The plateau value is the
   equilibrium free energy of the committed state under the `0.9 / 0.1`
   likelihood and corresponds to the residual complexity term
   `−∑_s Q(s) log D_mat[s]` evaluated at the collapsed posterior.

### D.6 Multi-episode D update rule and convergence

For multi-episode runs, the prior `D_mat` is updated via empirical Bayes:

> **D_mat^{(k+1)}[s] = α · D_mat^{(k)}[s] + (1 − α) · 𝔼_τ[Q^{(k)}(s_0)]**

where `α ∈ [0, 1)` is a learning rate, `τ` indexes episodes in the current
batch, and `𝔼_τ[Q^{(k)}(s_0)]` is the average initial posterior across
episodes. The update is a convex combination of the previous prior and the
empirical distribution of inferred initial states; since both sides lie on
the probability simplex and the mapping is a contraction (the average of a
bounded distribution is bounded), the iteration converges to a fixed point
`D_mat^*` at which `D_mat^* = 𝔼_τ[Q(s_0 | D_mat^*)]`. Convergence rate is
geometric with ratio `α`; in COGANT's default configuration `α = 0.9`, so
the D update takes on the order of ten episodes to converge to within
10⁻³ of the fixed point. The update is implemented in `cogant.process` as
`update_prior_from_episodes(prior, episodes, alpha=0.9)` and is disabled by
default for the single-episode runs reported in `../cogant/docs/evaluation/EMPIRICAL_CLAIM.md`.

### D.7 Expected free energy and policy selection

For policy selection, COGANT uses the expected free energy (EFE) for each
candidate policy `π`:

> **G(π) = ∑_τ [ 𝔼_{Q(o_τ, s_τ | π)}[log Q(s_τ | π) − log P(o_τ, s_τ)] ]**
>
>        = **∑_τ [ risk(π, τ) + ambiguity(π, τ) ]**

where `risk` is the KL divergence between predicted observations and
preferences (`C_mat`) and `ambiguity` is the expected entropy of the
likelihood under predicted states. The implementation in
`cogant.process.evaluate_policies` computes `G(π)` for every policy in the
finite policy space and selects the argmin (softmax with temperature = 0 in
the deterministic default). On zoo/01\_simple\_state with `C_mat = [0.0]`,
both `u_c0` and `u_c1` score `G = 0.0` identically; the argmin tie-break
returns `u_c0` every step, which is the behaviour observed in
`../cogant/docs/evaluation/EMPIRICAL_CLAIM.md` §3.

## See also (MkDocs)

Active inference primer (package): [`../cogant/docs/theory/active_inference_primer.md`](../cogant/docs/theory/active_inference_primer.md).

---

