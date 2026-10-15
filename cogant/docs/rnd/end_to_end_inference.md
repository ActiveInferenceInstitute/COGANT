# End-to-end inference: representation, execution, and evidence

What does a reproducible codebase-to-GNN-to-inference trace establish, and which claims require independent behavioral evidence?

**Status: provisional methodology note, 2026-10-15.** Review baseline:
COGANT commit e5c3b473b78aeb4ca8fcbc9104af32193f667859. This note describes
the subsequent shared-worktree implementation, not an assertion that those
changes were present at the baseline. It is not a manuscript citation source.

## Source roles

| Primary source | Supported use here | Limit |
| --- | --- | --- |
| [Kaelbling, Littman and Cassandra, author-hosted paper](https://people.csail.mit.edu/lpk/papers/aij98-pomdp.pdf), DOI 10.1016/S0004-3702(98)00023-X | Belief-state planning under partial observability | Does not establish the adequacy of source-extracted state abstractions |
| [Da Costa et al., author manuscript](https://arxiv.org/html/2001.07203v2), DOI 10.1016/j.jmp.2020.102447 | Discrete active-inference formulation; outcome-risk and ambiguity in Appendix C | Outcome-risk is a specified formulation; parameter novelty and richer policy inference are separate |
| [Smith, Friston and Whyte, institutional publication record and manuscript](https://discovery.ucl.ac.uk/id/eprint/10143770/), DOI 10.1016/j.jmp.2021.102632 | Practical model construction, simulation and empirical fitting workflow | Simulation alone is not an empirical fitting result |
| [Heins et al., JOSS paper](https://joss.theoj.org/papers/10.21105/joss.04098) | Related discrete-state active-inference software | No numerical parity with an external package is claimed |
| [Oberkampf and Trucano, publisher article](https://www.sciencedirect.com/science/article/pii/S0376042102000052), DOI 10.1016/S0376-0421(02)00005-2 | Verification versus empirical validation distinction | CFD methodological analogy, not validation evidence for COGANT |

The Oberkampf journal metadata are Progress in Aerospace Sciences 38(3),
209–272 (2002). The [Sandia institutional record](https://www.sandia.gov/research/publications/details/verification-and-validation-in-computational-fluid-dynamics-2002-03-01/)
also links the associated SAND2002-0529 report, whose DOI 10.2172/793406 is
distinct from the journal article DOI. The manuscript bibliography cites the
journal version.

## Contracts that compose

1. Source analysis emits graph and mapping evidence. Structural defaults and
   normalized adjacency remain labeled model-construction choices.
2. GNN serialization carries the actual A/B/C/D coefficients. Runtime parsing
   rejects incomplete or malformed matrix representations instead of
   fabricating replacement dynamics.
3. Filtering conditions on a specified observation using the incoming prior.
   Action prediction becomes the next prior. The trace stores all three
   distributions separately.
4. The controller evaluates the outcome-risk plus likelihood-ambiguity score
   for each one-step action. Ties use the lowest index.
5. Plot admission checks source and matrix digests and replays the numerical
   trace. A plausible picture without those checks is insufficient evidence.

The relevant implementation boundaries are cogant.runtime.categorical,
cogant.runtime.loop, cogant.runtime.inference and
cogant.runtime.inference_records. The public command is cogant infer;
--observations accepts a JSON array of observation indices. Otherwise the
mode is model_rollout, with modal observations generated from the model.
Such a rollout supplies no independent observation of program behavior.

## Algebra checked against the implementation

With incoming prior r, observed outcome o, and posterior q:

F(q) = KL(q || r) - sum_s q(s) log A[o,s].

Positive evidence Z gives q(s) = A[o,s]r(s)/Z and F(q) = -log Z.
The initial D is used at initialization; subsequent VFE refers to the current
predicted prior. Zero total evidence is an error, and zero support is not
replaced with epsilon mass.

For predicted state q_a = B_a q and predicted outcome u_a = A q_a:

G(a) = KL(u_a || softmax(C)) + sum_s q_a(s) H(A[:,s]).

Expanding this *implemented score* gives
G(a) = -E[C] - I(S;O) + logsumexp(C), where the mutual information is under
q_a(s)A[o,s]. This is an algebraic consequence of fixed categorical matrices;
it does not assert that every broader definition of expected free energy is
identical under arbitrary posterior approximations or parameter uncertainty.
The CLI uses a one-step greedy policy. Scoring an explicitly supplied longer
action sequence does not create observation-contingent planning.

## Verification and validation remain separate

Authored finite kernels can be checked coefficient by coefficient against their
declarations. That establishes representation fidelity on the supplied finite
domain. Repository-derived variables instead index structural candidates and
need not enumerate joint program valuations. Adjacency normalization supplies
a stochastic matrix, not measured transition frequencies.

The calculator trace is an execution smoke control: its single-state model
already fixes the state belief, and its uniform observation likelihood gives
flat scores. It cannot demonstrate uncertainty recovery. More discriminative
authored matrices can test filtering, action effects and preference shifts,
but their successful execution still does not validate a repository
abstraction. That latter claim needs independently collected executions,
a justified observation/state mapping, and predictive comparisons that can fail.

Package context: [finite-model API](../api/finite_models.md) and
[implementation status](../reference/implementation_status.md).
