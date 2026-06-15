# `cogant.runtime`

The `cogant.runtime` package provides the Active Inference agent runtime —
the perception-action loop that consumes synthesized matrices (or any
object exposing `A`, `B`, `C`, `D`) and executes belief updates,
action selection, and multi-episode learning.

## Package

::: cogant.runtime
    options:
      show_root_heading: true
      show_source: true
      members_order: source

## Loop

`AgentRuntime`, `run_n_steps`, `run_until_convergence`, and the
multi-episode `run_multi_episode` learning driver.

::: cogant.runtime.loop
    options:
      show_root_heading: true
      show_source: true
      members_order: source

## Config

`AgentConfig` — knobs for convergence threshold, max steps, and
learning-update hyperparameters.

::: cogant.runtime.config
    options:
      show_root_heading: true
      show_source: true

## Metrics

Numerically-stable free-energy and KL divergence helpers that back the
runtime loop.

::: cogant.runtime.metrics
    options:
      show_root_heading: true
      show_source: true

## Examples

`AgentRuntime`, `AgentConfig`, the `run_n_steps` / `run_until_convergence` / `run_multi_episode` drivers, and the free-energy / KL helpers are exercised by:

- **Zoo:** [`examples/zoo/04_pomdp_minimal/`](https://github.com/ActiveInferenceInstitute/COGANT/tree/main/cogant/examples/zoo/04_pomdp_minimal) — minimal POMDP that the runtime loop can drive end-to-end.
- **Zoo:** [`examples/zoo/09_policy/`](https://github.com/ActiveInferenceInstitute/COGANT/tree/main/cogant/examples/zoo/09_policy) — policy + action selection target for `run_until_convergence`.
- **Zoo:** [`examples/zoo/12_full_pomdp/`](https://github.com/ActiveInferenceInstitute/COGANT/tree/main/cogant/examples/zoo/12_full_pomdp) — the canonical multi-episode learning target for `run_multi_episode`.
- **Cookbook:** [Recipe 17: Benchmarking the runtime](../cookbook/17_benchmark.md) — wall-clock characterization of the loop.
- **Tutorial:** [Tutorial 6: Reverse mode — GNN to code](../tutorials/06_reverse_mode.md) — runs the synthesized package under `AgentRuntime` after reverse synthesis.
