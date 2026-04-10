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
