# `cogant.static`

The `cogant.static` package runs static analysis on the ingested sources: AST parse, symbol extraction, type inference, import resolution, call-graph construction, and dataflow hints.

## Package

::: cogant.static

## Parser

::: cogant.static.parser

## Symbols

::: cogant.static.symbols

## Types

::: cogant.static.types

## Imports

::: cogant.static.imports

## Calls

::: cogant.static.calls

## Dataflow

::: cogant.static.dataflow

## Examples

The static parser, symbol extractor, type / import resolver, call-graph builder, and dataflow helpers are exercised by:

- **Zoo:** [`examples/zoo/01_simple_state/`](../../examples/zoo/01_simple_state/) — single-file target with one class and three methods (smallest static run).
- **Zoo:** [`examples/zoo/06_hierarchical/`](../../examples/zoo/06_hierarchical/) — multi-class hierarchy that exercises symbol resolution and call-graph edges.
- **Zoo:** [`examples/zoo/11_sensor_fusion/`](../../examples/zoo/11_sensor_fusion/) — multi-module imports + dataflow patterns.
- **Cookbook:** [Recipe 1: Scan your first Python project](../cookbook/01_scan_basic.md) — runs the static stage end-to-end from the CLI.
- **Cookbook:** [Recipe: Analyze a Flask app](../cookbook/analyze_a_flask_app.md) — six-module real-world target for symbol / import / call-graph stages.
- **Tutorial:** [Tutorial 3: Flask walkthrough](../tutorials/03_flask_walkthrough.md) — narrative on the 98-node static output of the Flask fixture.
