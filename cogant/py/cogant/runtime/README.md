# `cogant.runtime`

Pure-Python Active Inference runtime that executes the matrices
synthesised by [`cogant.reverse`](../reverse/AGENTS.md). Given the
A/B/C/D arrays from a generated `matrices.py`, the runtime steps a
perception–action loop, returning per-step traces and aggregate
statistics.

## Public API

Re-exported from `cogant/runtime/__init__.py`:

| Symbol | Role |
| --- | --- |
| `AgentRuntime` | Core perception–action loop wrapping a matrices module. |
| `AgentConfig` | Hyperparameters (max steps, convergence ε, planning horizon). |
| `AgentStep` | Immutable record of one inference step (belief, action, observation, free energy). |
| `EpisodeResult` | Aggregate of one episode (steps, total free energy, converged?). |
| `MultiEpisodeResult` | Aggregate of N episodes (per-episode results + summary stats). |
| `run_n_steps(matrices, n, *, config=…)` | Convenience: run exactly `n` steps. |
| `run_until_convergence(matrices, *, config=…)` | Convenience: run until belief stabilises within `config.convergence_eps`. |

## Conventions

* No NumPy dependency: the runtime works with the nested-list matrices
  emitted by `cogant.reverse.synthesizer.synthesize_package` so the
  generated package stays zero-deps.
* Free-energy minimisation is the inner loop; the configured
  `convergence_eps` decides when belief updates stop.
* `AgentRuntime.reset()` rewinds belief to the initial prior so the
  same instance can run multiple independent episodes.

See [`AGENTS.md`](AGENTS.md) for invariants and the reverse-path
overview in [`../reverse/AGENTS.md`](../reverse/AGENTS.md).
