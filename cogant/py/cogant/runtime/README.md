# Categorical runtime

COGANT executes a complete categorical generative model using one shared
standard-library numerical implementation. The model axes are:

| Matrix | Shape | Meaning |
| --- | --- | --- |
| A | observation, state | P(observation given state) |
| B | next state, current state, action | Controlled transition probabilities |
| C | observation | Log preferences; softmax supplies the preferred outcome distribution |
| D | state | Initial categorical prior |

A columns and each B current-state/action column sum to one. D sums to one.
Empty, nonfinite, negative, incompatible, or incomplete models fail validation.

## Filtering and control

`categorical.posterior(prior, A, observation)` computes the normalized
likelihood-times-prior update. An observation with zero evidence fails instead
of manufacturing a posterior.

`categorical.variational_free_energy(q, prior, A, observation_distribution)`
computes `KL(q || prior) - E_q log P(observation | state)`. The prior is the
current prediction, not necessarily the initial D. Positive posterior mass on
an impossible likelihood or prior produces infinite mathematical free energy.

`CategoricalModel.score(beliefs, policy)` sums over the supplied finite action
sequence:

```text
KL(predicted_outcomes || softmax(C))
+ sum_state predicted_belief[state] * entropy(A[:, state])
```

The log-normalization is stable under common offsets of C. A one-step agent
evaluates every action and chooses the minimum score, breaking ties by declared
index. `preference_score` is a separate expected-log-preference diagnostic.

## Episode API

```python
from cogant.runtime.loop import AgentRuntime

runtime = AgentRuntime.from_matrices_dict(
    {
        "A": [[0.9, 0.1], [0.1, 0.9]],
        "B": [[[1.0], [0.0]], [[0.0], [1.0]]],
        "C": [0.0, 0.0],
        "D": [0.5, 0.5],
    }
)
step = runtime.step([0.5, 0.5], obs_idx=0)
assert step.posterior == [0.9, 0.1]
episode, logs = runtime.run_episode_with_logging([0, 1, 0])
```

A step records its incoming observation, corrected `posterior`, filtering
`free_energy`, per-action `policy_scores`, selected `action`, and next
predicted `state_dist`. Episode `final_posterior` is the last corrected
posterior. Observation-state counts use that same corrected belief.

`run_n_steps(n)` and `run_episode(n)` generate modal observations from the
model's current prediction. They are deterministic model rollouts.
`run_episode_with_logging(observations)` consumes the supplied observation
sequence. `run_until_convergence` checks KL between successive predictions
subject to its configured step limit; that stopping rule does not establish
physical adequacy or policy optimality beyond the evaluated candidates.

`update_A_from_counts(counts, learning_rate)` blends each state column with its
observed conditional outcome frequencies. Zero-count state columns are retained.
`update_D_from_posterior(posterior)` maintains an arithmetic running average.
`run_multi_episode` applies these updates after each episode. These operations
mutate the agent's matrices; `reset()` clears episode bookkeeping and the last
free-energy value while retaining learned matrices. Use `to_dict()` and
`from_dict()` for state serialization.

## Source-bound GNN execution

`run_gnn_inference(text, InferenceOptions(...))` parses the exported GNN,
validates complete matrices, and returns an immutable Pydantic trace. It records
source and matrix SHA-256 digests, declared axis labels, admitted matrices,
observation mode, and each filtering/control step. The GNN package runner and
CLI consume this same driver.

The trace layer uses Pydantic for input and artifact validation. The mathematical
kernel and episode loop contain standard-library implementations; importing the
installed COGANT package also loads its normal package dependencies. Generated
matrix modules embed the kernel and execute with standard-library Python alone.

Tests include independent arithmetic controls, informative-versus-aliased
likelihoods with identical marginals, preference-offset invariance, invalid
observation rejection, learning-count timing, exact matrix-fence preservation,
and generated execution with site packages disabled.
