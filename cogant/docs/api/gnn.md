# `cogant.gnn`

The `cogant.gnn` package builds, formats, and validates Generalized Notation Notation packages. The on-disk artifact is produced by `GNNPackageBuilder`; `GNNValidator` produces a 0–100 score and an error/warning table.

## Package

::: cogant.gnn

## Package builder

::: cogant.gnn.package

## Matrix builder

Builds the A / B / C / D generative-model matrices from the rule output and the Markov blanket.

::: cogant.gnn.matrices

## Runner

::: cogant.gnn.runner

## Validator

::: cogant.gnn.validator

## JSON export

::: cogant.gnn.json_export

## Upstream bridge

Thin facades to the pinned **generalized-notation-notation** v2.0.0 package, whose upstream implementation is exposed through a repo-style `src.gnn` layout. COGANT callers should not import `src.gnn` directly: use the re-exported symbols on `cogant.gnn` (`run_upstream_validate_gnn`, `parse_upstream_model_gnn_md`, …) or the additional helpers in `cogant.gnn.upstream_bridge` (see `py/cogant/gnn/AGENTS.md`).

::: cogant.gnn.upstream_bridge

## Examples

Every public symbol exported by `cogant.gnn` (`GNNPackageBuilder`, `GNNValidator`, the matrix builder, the runner, the JSON exporter, and upstream bridge helpers) is exercised by the following references:

- **Zoo:** [`examples/zoo/01_simple_state/`](https://github.com/ActiveInferenceInstitute/COGANT/tree/main/cogant/examples/zoo/01_simple_state) — produces the smallest valid on-disk package (1 hidden state, 0 observations).
- **Zoo:** [`examples/zoo/04_pomdp_minimal/`](https://github.com/ActiveInferenceInstitute/COGANT/tree/main/cogant/examples/zoo/04_pomdp_minimal) — produces a complete A / B / C / D quadruple via the matrix builder.
- **Zoo:** [`examples/zoo/12_full_pomdp/`](https://github.com/ActiveInferenceInstitute/COGANT/tree/main/cogant/examples/zoo/12_full_pomdp) — full validator score = 100 / 100 reference.
- **Cookbook:** [Recipe 14: Validating a hand-written GNN against AII spec](../cookbook/14_gnn_validation.md) — `GNNValidator` walk-through.
- **Cookbook:** [Recipe: Interpret GNN output](../cookbook/interpret_gnn_output.md) — reading A / B / C / D from a real bundle.
- **Tutorial:** [Tutorial 5: Reading the A / B / C / D matrices](../tutorials/05_gnn_interpretation.md) — full narrative on the matrix builder + validator.
