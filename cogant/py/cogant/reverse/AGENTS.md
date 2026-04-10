# Agents — py/cogant/reverse

## Owner

Semantic Lead

## Responsibilities

Reverse synthesis: GNN markdown → Python package (`parse_gnn`, `plan_package`, `synthesize_package`). Defines graph-level round-trip isomorphism expectations (`verify_roundtrip`, `verify_repo_roundtrip`, `compute_isomorphism_report`, matrix/role comparators).

## Coordination

Forward path is ingest → graph → translate → GNN; reverse closes the loop for benchmarks and validation. Runtime execution lives in `runtime/` on synthesized matrix modules.

## Files

- `parser.py` — `ReverseGNNModel`, `parse_gnn`.
- `planner.py` — `PackagePlan`, `NodePlan`, `plan_package`.
- `synthesizer.py` — `synthesize_package`.
- `callable.py` — `MatrixFunctions`, `make_matrix_functions`.
- `idempotency.py` — round-trip verification.
- `metrics.py` — isomorphism reports and comparators.
- `__init__.py` — public API.
