# Runtime maintenance

Read [README.md](README.md) for the public numerical and episode contracts.

## Change routing

- Numerical changes belong in `categorical.py`. It is the standard-library-only
  implementation shared by runtime, simulation, reverse callables, and generated
  matrix modules. Keep its source self-contained: the reverse renderer embeds it.
- Perception/action ordering and learning belong in `loop.py`; episode record
  definitions and posterior count accumulation belong in `records.py`.
- GNN artifact execution belongs in `inference.py`; admission, immutable snapshots,
  source digests, and trace schemas belong in `inference_records.py`. This boundary
  uses Pydantic. The numerical kernel and episode loop do not depend on it.
- Configuration changes belong in `config.py`; expose only implemented behavior.

## Invariants

Use A[observation][state], B[next_state][current_state][action], C[observation]
as log preferences, and D[state] as the initial prior. Require complete, finite,
dimensionally compatible stochastic matrices. Invalid observations and zero
observation evidence raise errors.

One step filters the incoming predicted prior, evaluates VFE on that posterior,
scores every declared one-action policy by outcome risk plus expected likelihood
ambiguity, selects the lowest score with the lowest-index tie, then predicts the
next belief. `AgentStep.posterior` and `free_energy` precede control;
`state_dist` is the next prediction. `policy_scores` follows action-axis order.

Observation-state learning counts use the corrected posterior. A updates blend
column-conditional empirical frequencies; unseen state columns stay unchanged.
D updates are arithmetic running averages of episode-final posteriors. These are
frequency updates, not parameter posterior inference or gradient optimization.

## Verification

For numerical or ordering changes, run these from the inner package root:

```bash
uv run pytest tests/unit/test_categorical_inference_contracts.py tests/unit/test_categorical_shared_execution.py tests/unit/test_runtime*.py tests/integration/test_convergence_learning.py --no-cov
```

Also run affected reverse/simulation tests, repository Ruff, and strict mypy.
The standalone generated-module test runs Python with `-I -S` to prove it does
not import COGANT or third-party packages. Preserve rejection controls for
zero evidence, inconsistent axes, and corrupt matrix fences.

For source-bound trace changes, run `tests/unit/test_inference_trace_artifact.py`
and inspect an actual `inference_trace.json` produced from exported
`gnn_package/model.gnn.md`. Use the trace's explicit mode to distinguish
externally supplied observations from deterministic model rollouts.
