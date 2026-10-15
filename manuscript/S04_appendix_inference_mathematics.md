# Appendix D — Inference Loop Mathematics {#sec:S04-appendix-inference-mathematics}

This appendix specifies the finite categorical calculation shared by
cogant.runtime.categorical, cogant.runtime.loop, and cogant.runtime.inference.
The public inference path parses exported GNN matrices, conditions on
observations, scores actions, and records the result. Classical belief-state
planning supplies the POMDP setting [@kaelbling1998planning]; discrete
active-inference treatments motivate the likelihood, transition, preference,
and initial-prior decomposition [@dacosta2020active; @smith2022stepbystep].
PyMDP provides a related executable implementation [@heins2022pymdp]. The
equations below specify COGANT's implemented objective and update order,
without claiming the full range of algorithms available in those references.

### POMDP formulation {#sec:S04-pomdp-formulation}

Let $S$, $O$, and $\mathcal{U}$ denote finite, ordered state, observation, and
action domains. Write $A[o,s]=P(o\mid s)$,
$B[s',s,a]=P(s'\mid s,a)$, and $D[s]=P(s_0=s)$. The finite log weights $C[o]$
define the preference distribution

$$
p_C(o)=\frac{\exp C[o]}{\sum_{\tilde o}\exp C[\tilde o]}.
$$

Every column of $A$, every conditional column $B[:,s,a]$, and $D$ must have
nonnegative finite entries and unit mass within the numerical admission
tolerance. Missing or incompatible matrix axes are rejected; an empty matrix
does not define an executable categorical model.

These probabilities describe the emitted model. Normalized repository
adjacency and structural defaults do not become learned empirical dynamics
merely by satisfying stochasticity. Repository variable nodes need not
enumerate complete joint value configurations. A joint factor space has size
$\prod_f |S_f|$ only when those configurations have actually been constructed.
The same distinction applies to combined observation modalities.

### Declared finite kernels {#sec:S04-explicit-finite-kernels}

For the explicit finite-model interface, let $T(s'\mid s,a)$ and $L(o\mid s)$
be authored tables on ordered finite domains. The compiler assigns

$$
B[j,i,k]=T(s_j\mid s_i,a_k),\qquad A[\ell,i]=L(o_\ell\mid s_i),
$$

and copies the declared prior and log preferences into $D$ and $C$.
Unlisted outcomes have zero mass. For any represented state distribution $q$,

$$
q'(s_j)=\sum_i B[j,i,k]q(s_i)
      =\sum_i T(s_j\mid s_i,a_k)q(s_i).
$$

This is a representation identity for the declared kernel. The compiler
preserves parsed floating-point coefficients; the independent checker compares
all entries with the sparse declaration, including implied zeros. It does not
establish exact real arithmetic or behavioral adequacy of the declaration.
For repository-derived models, the interpretation of structural nodes and
transitions requires separate evidence from the analyzed program.

### Variational free energy functional {#sec:S04-variational-free-energy}

At observation time $t$, let $r_t(s)$ be the incoming predicted prior and let
$o_t$ be the supplied observation. Initially $r_0=D$. For a candidate posterior
$q$, the implemented variational free energy is

$$
F_t[q]=\mathrm{KL}(q\Vert r_t)
       -\sum_s q(s)\log A[o_t,s].
$$

The terms are complexity relative to the incoming prior and negative expected
log likelihood. Posterior entropy alone is not the likelihood ambiguity term
used for policy scoring below. When observation evidence
$Z_t=\sum_s A[o_t,s]r_t(s)$ is positive,

$$
F_t[q]=\mathrm{KL}(q\Vert P(s\mid o_t,r_t))-\log Z_t.
$$

Thus the exact represented posterior has $F_t=-\log Z_t$. Later steps use their
incoming predicted prior, not a repeated comparison against the initial $D$.
The general helper can also accept an explicit distribution over observations,
replacing $\log A[o_t,s]$ by its expectation under that distribution; it does
not invent an observation when none is provided.

Zero probabilities retain their support meaning: positive posterior mass where
the prior or observed likelihood is zero yields infinite free energy.
Conditioning on zero total evidence is undefined and is rejected. No positive
epsilon is inserted to manufacture a finite score.

### Categorical filtering and control prediction {#sec:S04-belief-propagation}

Filtering uses the normalized likelihood-prior product

$$
q_t(s)=\frac{A[o_t,s]r_t(s)}{Z_t}.
$$

This is exact Bayesian conditioning for the represented finite categorical
model, up to floating-point arithmetic. After evaluating actions and choosing
$a_t$, prediction advances the prior:

$$
r_{t+1}(s')=\sum_s B[s',s,a_t]q_t(s).
$$

A trace distinguishes incoming prior $r_t$, filtered posterior $q_t$, and
predicted next belief $r_{t+1}$. This update uses one likelihood factor;
it does not implement general loopy factor-graph inference. The runtime
records VFE before advancing to the next prior.

### Analytic identity-model control {#sec:S04-identity-model-vfe}

For a single state and a single certain observation, $A=[[1]]$, $D=[1]$,
and identity transition columns imply $q=r=[1]$. Both terms of $F$ vanish.
This is an analytic verification case, not evidence of successful uncertainty
recovery. A single-state model with uniform likelihood over its observation
axis instead has $F=\log |O|$: the hidden state is already certain, while the
observed outcome remains uncertain.

### Distinguishing execution regimes {#sec:S04-other-regimes}

An informative likelihood can change beliefs, an uninformative likelihood can
leave them unchanged, and an impossible observation must fail conditioning.
These mathematical cases require distinct controls.
The calculator figure in @fig:cogant-inference-trace belongs to the
single-state, uniform-likelihood case. Its flat trace verifies execution of
that exported artifact; it does not demonstrate hidden-state recovery or
improved control performance. Invalid or incomplete GNN matrices are reported
as admission errors rather than assigned a finite uncertainty floor.

### Optional episode adaptation {#sec:S04-d-update-convergence}

The source-bound inference CLI holds its parsed matrices fixed throughout
a trace. Separate AgentRuntime episode helpers can update $D$ using a running
mean of normalized final posteriors,

$$
D^{(k+1)}=\frac{kD^{(k)}+q_{\mathrm{final}}^{(k)}}{k+1},
$$

where $k$ counts previously completed updates. For nonnegative observation-state
counts $n_{os}$ and learning rate $\eta$, the optional likelihood update is

$$
A'_{os}=(1-\eta)A_{os}+\eta\frac{n_{os}}{\sum_{\tilde o}n_{\tilde o s}}
$$

for columns with positive total count; unseen-state columns are unchanged.
These adaptation helpers are not invoked by the fixed-matrix CLI trace.
They do not establish a convergence guarantee, identify causal transition
dynamics, or perform Bayesian structure learning.

### Expected free energy and policy selection {#sec:S04-expected-free-energy}

For an action $a$, predict $q_a=B_aq_t$ and $q_a^O=Aq_a$. COGANT implements
the outcome-risk plus likelihood-ambiguity objective

$$
G(a)=\mathrm{KL}(q_a^O\Vert p_C)+\sum_s q_a(s)H(A[:,s]).
$$

This is a particular discrete active-inference formulation. Broader treatments
distinguish state risk, outcome risk, and additional parameter-learning terms
[@dacosta2020active; @smith2022stepbystep]. For the fixed joint distribution
$q_a(s)A[o,s]$, expanding the implemented expression gives

$$
G(a)=-\mathbb{E}_{q_a^O}[C(o)]-I_{q_a}(S;O)
     +\log\sum_o \exp C[o].
$$

This algebraic identity follows from
$I(S;O)=H(q_a^O)-\sum_s q_a(s)H(A[:,s])$; the final term is constant across
candidate actions for fixed $C$. Expected log preference alone is therefore
not the implemented objective.

The CLI evaluates each available action at a one-step horizon and chooses the
lowest score, breaking ties by the lowest action index. It does not enumerate
all finite-horizon policies or claim globally optimal POMDP control. The
lower-level policy scorer can sum this objective along an explicitly supplied
finite action sequence, without branching over future observations.

### Source-bound execution and evidential scope

Inference artifacts bind the exact GNN text and parsed matrix snapshot with
separate SHA-256 digests. Supplied observation indices are recorded as external
inputs. In the default model-rollout mode, each observation is the lowest-index
mode of the predicted observation distribution. Such generated observations
are not measurements of source-program behavior. Figure admission checks
source and matrix digests and replays canonical execution before plotting.

These checks address representation and numerical execution. Behavioral
adequacy additionally requires an independently justified relation between
program executions and the model's states, observations, and controls.
Oberkampf and Trucano's distinction between computational verification and
comparison with experimental evidence provides a methodological analogy from
computational fluid dynamics [@oberkampf2002verification]; that citation is not
evidence that COGANT has achieved empirical model validation.
