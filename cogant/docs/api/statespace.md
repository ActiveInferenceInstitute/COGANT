# `cogant.statespace`

The `cogant.statespace` package compiles the rule output into a behavioral state-space model: variables with declared domains, actions with source spans, and transitions with confidence tiers.

## Package

::: cogant.statespace

## Compiler

::: cogant.statespace.compiler

## Variables

::: cogant.statespace.variables

## Temporal

::: cogant.statespace.temporal

## Examples

The state-space compiler, variable / domain helpers, and temporal utilities documented above are exercised by:

- **Zoo:** [`examples/zoo/01_simple_state/`](https://github.com/docxology/cogant/tree/main/cogant/examples/zoo/01_simple_state) — single-variable state space, smallest possible compiler input.
- **Zoo:** [`examples/zoo/05_multi_factor/`](https://github.com/docxology/cogant/tree/main/cogant/examples/zoo/05_multi_factor) — multi-factor state space exercising the variable builder's domain inference.
- **Zoo:** [`examples/zoo/07_event_driven/`](https://github.com/docxology/cogant/tree/main/cogant/examples/zoo/07_event_driven) — event-driven temporal patterns the temporal helpers normalize.
- **Cookbook:** [Recipe 4: Customizing the confidence threshold](../cookbook/04_custom_threshold.md) — tier filtering on compiled variables.
- **Cookbook:** [Recipe 15: Visualizing Markov blanket partitions](../cookbook/15_markov_blanket.md) — partitions the compiler exposes on its output.
- **Tutorial:** [Tutorial 5: Reading the A / B / C / D matrices](../tutorials/05_gnn_interpretation.md) — uses compiled state-space variables to label matrix rows / columns.
