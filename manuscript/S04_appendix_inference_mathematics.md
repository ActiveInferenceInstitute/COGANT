# Appendix D — Inference Loop Mathematics {#sec:S04-appendix-inference-mathematics}

This appendix formalizes the discrete-time active inference loop executed
by COGANT's matrix runtime (`cogant.gnn.runner` / `cogant.runtime.loop`, with
the variational free-energy functions in `cogant.simulate.free_energy`) on the
extracted A/B/C/D matrices and reported
empirically in `../cogant/docs/evaluation/EMPIRICAL_CLAIM.md`
(VFE trace tables per zoo fixture). The variational free-energy discussion in
@sec:10-conclusion ties the same functions to shipped capabilities. The
formalism follows the free-energy principle and the discrete-state Active
Inference synthesis [@friston2010free; @dacosta2020active; @parr2022active],
with PyMDP as the closest executable reference implementation for the
matrix-based POMDP loop [@heins2022pymdp]. The discrete POMDP/active-inference loop COGANT closes its evaluation around is
the small-scale instance of a broader lineage; the scale-free, renormalising
generalisation that lifts partially observed Markov decision processes to
include paths as latent variables [@friston2024pixels] is the current
state of that discrete-state generalisation beyond [@dacosta2020active] and
[@parr2022active]. The factor-graph language is used
in the standard sense of a bipartite representation of factored functions and
sum-product message passing [@kschischang2001factor], but COGANT's current
runtime (`cogant.gnn.runner` / `cogant.runtime.loop`) executes the finite
matrix model — the compiled A/B/C/D state space — rather than a
general-purpose loopy factor-graph solver. We restate it here in notation
consistent with COGANT's `cogant.simulate.free_energy` implementation.

### POMDP formulation {#sec:S04-pomdp-formulation}

The extracted model is a discrete-time Partially Observable Markov Decision
Process $(S, O, A, \pi, A_{\mathrm{mat}}, B_{\mathrm{mat}}, C_{\mathrm{mat}}, D_{\mathrm{mat}})$, grounded in the classical
POMDP formulation of belief-state planning under partial observability
[@kaelbling1998planning] and using the A/B/C/D decomposition standard in
discrete active inference [@dacosta2020active; @smith2022stepbystep], with:

> $\mathbf{S} = \{s_1, \ldots, s_{|S|}\}$ — finite set of hidden states.
> Cardinality is the product of factor cardinalities:
> $|S| = \prod_f |S_f|$.
>
> $\mathbf{O} = \{o_1, \ldots, o_{|O|}\}$ — finite set of observations.
> For multi-modality models, $|O| = \prod_m |O_m|$.
>
> $\mathbf{A} \subseteq \{1, \ldots, |A|\}$ — finite set of discrete actions
> (control states).
>
> $\pi \in \Pi$ — policies, i.e. finite sequences
> $(a_0, a_1, \ldots, a_{T-1}) \in A^T$ over horizon $T$.
>
> $\mathbf{A}_{\mathrm{mat}} \in \mathbb{R}^{|O| \times |S|}$,
> $A_{\mathrm{mat}}[o, s] = P(o \mid s)$ — likelihood.
>
> $\mathbf{B}_{\mathrm{mat}} \in \mathbb{R}^{|S| \times |S| \times |A|}$,
> $B_{\mathrm{mat}}[s', s, a] = P(s' \mid s, a)$ — state-transition tensor.
>
> $\mathbf{C}_{\mathrm{mat}} \in \mathbb{R}^{|O|}$, $C_{\mathrm{mat}}[o]$ —
> log-preference over observations.
>
> $\mathbf{D}_{\mathrm{mat}} \in \mathbb{R}^{|S|}$,
> $D_{\mathrm{mat}}[s] = P(s_0 = s)$ — prior over initial states.

All COGANT-extracted matrices satisfy the stochasticity conditions
$\sum_o A_{\mathrm{mat}}[o, s] = 1$ for all $s$ and
$\sum_{s'} B_{\mathrm{mat}}[s', s, a] = 1$ for all $(s, a)$; the GNN
validator enforces these invariants at emission time.

The probability notation is internal to the emitted model. After
normalisation, $A_{\mathrm{mat}}$, $B_{\mathrm{mat}}$, and
$D_{\mathrm{mat}}$ are valid categorical distributions for simulation and
validation, but they are not learned causal mechanisms or empirical transition
frequencies unless external traces supply that evidence. Matrix validation
therefore establishes stochastic well-formedness of the generated artifact,
not semantic adequacy of the repository interpretation.

### Variational free energy functional {#sec:S04-variational-free-energy}

Let $Q(s)$ be an approximate posterior over hidden states and $P(o, s)$ the
joint distribution defined by the generative model
$P(o, s) = A_{\mathrm{mat}}[o, s] \cdot D_{\mathrm{mat}}[s]$. The variational free energy (VFE) is

$$
F[Q] = \mathbb{E}_{Q(s)}[\log Q(s) - \log P(o, s)]
     = \mathrm{KL}(Q(s) \Vert P(s \mid o)) - \log P(o).
$$

The second equality (the "Helmholtz decomposition") shows that minimizing
$F$ is equivalent to finding the posterior that best approximates
$P(s \mid o)$ up to a constant $\log P(o)$ that depends only on the observation.
Equivalently,

$$
F[Q] =
\mathbb{E}_{Q(s)}[-\log A_{\mathrm{mat}}[o, s]]
- H[Q(s)]
- \mathbb{E}_{Q(s)}[\log D_{\mathrm{mat}}[s]].
$$

decomposes VFE into three interpretable terms: the expected negative
log‑likelihood (prediction error), the negative entropy of the posterior
(ambiguity), and the expected log‑prior (complexity). COGANT's
`variational_free_energy` (`cogant.simulate.free_energy`) computes this
decomposition directly from the extracted matrices.

### Variational inference via belief propagation {#sec:S04-belief-propagation}

For a single-factor discrete POMDP with observation $o_t$ at time $t$, the
posterior update is the normalized product

$$
Q(s_t) \propto A_{\mathrm{mat}}[o_t, s_t] \cdot Q(s_{t\mid t-1}).
$$

where $Q(s_{t\mid t-1})$ is the predicted state (the result of applying the
transition tensor to the previous posterior:
$Q(s_{t\mid t-1}) = \sum_{s_{t-1}} B_{\mathrm{mat}}[s_t, s_{t-1}, a_{t-1}]
\cdot Q(s_{t-1})$). Because the represented posterior is a categorical
distribution over a finite set and the implemented update uses one likelihood
factor, the update has emitted-model exactness and the inner loop
terminates in a single normalization step. That scoped exactness does not
show that the extracted model is semantically adequate for the source
repository. The belief-propagation terminology is retained because the same
normalized-product update is the single-factor specialization of
sum-product message passing on factor graphs [@kschischang2001factor]; in
multi-factor or loopy graphs, the corresponding message-passing algorithm may
be approximate.

### VFE = 0.0 in the identity model {#sec:S04-identity-model-vfe}

The zoo/01\_simple\_state fixture demonstrates the identity case where
VFE evaluates to 0.0. The extracted model has

> $|S| = 1$ (single factor, single cardinality after aggregation)
>
> `A_mat = [[1.0]]` (identity likelihood)
>
> $B_{\mathrm{mat}}[:, :, a] = [[1.0]]$ for all $a$ (identity transition, all actions)
>
> `C_mat = [0.0]` (no preference gradient)
>
> `D_mat = [1.0]` (fully certain prior)

Substituting into the VFE decomposition:

> $F = \mathbb{E}_{Q(s)}[-\log A_{\mathrm{mat}}[o, s]] - H[Q(s)] - \mathbb{E}_{Q(s)}[\log D_{\mathrm{mat}}[s]]$
>
> $= -\log(1.0) - 0 - \log(1.0)$
>
>   = **0.0**

The three terms vanish separately: the prediction error is zero because
`A_mat[0, 0] = 1.0` and the observation is guaranteed, the entropy is zero
because `Q(s) = [1.0]` is a Dirac delta on the single state, and the
complexity term is zero because the prior is also a Dirac. This is the
correct and expected behaviour for any fixture where the extracted model is
a degenerate single-state POMDP; the ten-step trace in
`../cogant/docs/evaluation/EMPIRICAL_CLAIM.md` confirms $F = -0.000000$ at every step, which is
the expected numerical signature (the signed zero arises from the sign of
$\log(1.0) = 0$ after the negation in the prediction-error term).

### Other regimes observed in the empirical runs {#sec:S04-other-regimes}

Three qualitatively distinct VFE regimes appear in the four zoo fixtures
reported in `../cogant/docs/evaluation/EMPIRICAL_CLAIM.md`:

1. **`VFE = 0.0` (flat certainty).** `zoo/01_simple_state` and
   `zoo/02_observer` — identity A/B with `D = [1.0]`, no free energy
   gradient, no belief update happens because the point-mass prior already
   fixes the posterior.

2. **`VFE = 23.025851` (maximum uncertainty floor).** `zoo/04_pomdp_minimal`
   — observation-only GNN where the likelihood matrix `A_mat` is empty
   (the extracted model has no hidden-state factor). The runtime evaluates
   `-log(1e-10) = 23.025850929940457` as the floor for an unresolvable
   observation, which is the expected floor for the `cogant.simulate.free_energy`
   implementation when the likelihood is vacuously defined.

3. **VFE approaches 0.798508 (converging plateau).** `zoo/06_hierarchical` —
   two-factor hierarchical model with discriminative likelihood
   `A_mat = [[0.9, 0.1], [0.1, 0.9]]`. The posterior collapses from the
   uniform prior `D_mat = [0.5, 0.5]` to the certain state
   $Q(s) = [1.0, 0.0]$ by $t = 2$; VFE rises from $F(t=0) = 0.751435$ to
   the equilibrium $F(t \ge 4) = 0.798508$. The plateau value is the
   equilibrium free energy of the committed state under the `0.9 / 0.1`
   likelihood and corresponds to the residual complexity term
   $-\sum_s Q(s)\log D_{\mathrm{mat}}[s]$ evaluated at the collapsed posterior.

### Multi-episode D update rule and convergence {#sec:S04-d-update-convergence}

For multi-episode runs, the runtime updates `D_mat` as an arithmetic running mean of episode
posteriors:

$$
D_{\mathrm{mat}}^{(k+1)}[s] =
\frac{k \cdot D_{\mathrm{mat}}^{(k)}[s] + Q^{(k)}_{\mathrm{final}}(s)}{k + 1}.
$$

where `k` is the number of completed episodes before the update and
`Q^{(k)}_{\mathrm{final}}` is the normalized final posterior from the latest episode. The helper
`AgentRuntime.update_D_from_posterior()` mutates `D` in place and renormalizes to guard against
floating-point drift. The companion `update_A_from_counts()` blends empirical
observation-state frequencies into each A entry with a configurable `learning_rate`, then
renormalizes columns. These are pragmatic count/posterior updates for deterministic smoke
experiments; the manuscript does not claim a geometric-contraction proof for the implemented
runtime. This running-mean scheme is a substitute for, not an implementation of, Bayesian
model reduction for structure learning [@friston2017curiosity; @friston2025reasoning], which selects or prunes model
structure by expected free energy / information gain and would be the principled route to
learning $D$ --- and the underlying factor structure --- across episodes rather than averaging
posteriors at fixed cardinality.

### Expected free energy and policy selection {#sec:S04-expected-free-energy}

For policy selection, COGANT uses the expected free energy (EFE) for each
candidate policy $\pi$, following the risk-plus-ambiguity decomposition used
in discrete active inference [@dacosta2020active; @parr2022active; @parr2019generalised]:

$$
G(\pi) =
\sum_{\tau}
\mathbb{E}_{Q(o_\tau, s_\tau \mid \pi)}
[\log Q(s_\tau \mid \pi) - \log P(o_\tau, s_\tau)]
= \sum_{\tau} [\mathrm{risk}(\pi,\tau) + \mathrm{ambiguity}(\pi,\tau)].
$$

where `risk` is the KL divergence between predicted observations and
preferences (`C_mat`) and `ambiguity` is the expected entropy of the
likelihood under predicted states. The implementation in
`GNNModelRunner._evaluate_policies` (`cogant.gnn.runner`, scoring policies
with `expected_free_energy` from `cogant.simulate.free_energy`) computes
$G(\pi)$ for every policy in the finite policy space and selects the argmin
(softmax with temperature = 0 in the deterministic default). On zoo/01\_simple\_state with `C_mat = [0.0]`,
both `u_c0` and `u_c1` score `G = 0.0` identically; the argmin tie-break
returns `u_c0` every step, which is the behaviour observed in
`../cogant/docs/evaluation/EMPIRICAL_CLAIM.md` §3.
