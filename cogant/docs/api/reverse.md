# `cogant.reverse`

The `cogant.reverse` package is the inverse of the forward translate
pipeline: it parses GNN markdown, plans a synthesis target, and either
emits a runnable Python package (`synthesize_package`) or binds
runtime-callable closures (`MatrixFunctions`) directly.

## Package

::: cogant.reverse
    options:
      show_root_heading: true
      show_source: true
      members_order: source

## Parser

GNN markdown → `ReverseGNNModel`. Tolerates both the upstream canonical
syntax and the COGANT extended sections.

::: cogant.reverse.parser
    options:
      show_root_heading: true
      show_source: true

## Callable

Runtime-callable closures built directly from a `ReverseGNNModel`.
No code generation, no `exec()` — plain Python function calls.

::: cogant.reverse.callable
    options:
      show_root_heading: true
      show_source: true

## Planner

Planning step that turns a parsed model into a synthesis plan (names,
dimensions, helper signatures).

::: cogant.reverse.planner
    options:
      show_root_heading: true
      show_source: true

## Synthesizer

End-to-end package synthesis. `synthesize_package` writes a runnable
Python package to disk from a parsed model.

::: cogant.reverse.synthesizer
    options:
      show_root_heading: true
      show_source: true

## Matrices

Code-generation helpers used by the synthesizer to render the A/B/C/D
matrices module.

::: cogant.reverse.matrices
    options:
      show_root_heading: true
      show_source: true

## Metrics

Roundtrip error (ε) and isomorphism metrics — the empirical bar the
forward-reverse cycle is held against.

::: cogant.reverse.metrics
    options:
      show_root_heading: true
      show_source: true

## Idempotency

Helpers for the idempotency checks that drive the roundtrip ε metric.

::: cogant.reverse.idempotency
    options:
      show_root_heading: true
      show_source: true
