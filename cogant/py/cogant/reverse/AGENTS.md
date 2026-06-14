# Agents — py/cogant/reverse

## Owner

Semantic Lead

## Responsibilities

**GNN → Python synthesis and round-trip validation:**

1. **Parse GNN markdown** (`parser.py`) — read the 19-section GNN format (see `cogant.gnn.validator.GNNValidator.CANONICAL_SECTIONS`), validate structure, extract matrices (A/B/C/D), state variables, and role counts.
2. **Plan package structure** (`planner.py`) — generate a `PackagePlan` that maps GNN roles to Python classes and functions (HIDDEN_STATE → class attributes, OBSERVATION → @property getters, ACTION → methods, POLICY → decision logic, CONSTRAINT → assertions, CONTEXT → config).
3. **Synthesize Python package** (`synthesizer.py`) — emit runnable Python code with matrix functions (`likelihood`, `transition`, `expected_free_energy`, `best_action`), an `AgentRuntime`, and stubs for each role.
4. **Verify round-trip status** (`idempotency.py`) — run the forward pipeline on the synthesized package and compute the v0.6 invariant ledger: role preservation, graph deltas, edge-kind deltas, state-space shape preservation, GNN section preservation, matrix preservation, and generated-code smoke status.
5. **Compute roundtrip metrics** (`metrics.py`) — generate detailed breakdowns of which roles were preserved, lost, or added during synthesis.

## Coordination

- **Input:** GNN markdown bundle from export stage (19 sections, A/B/C/D matrices, semantic mappings).
- **Output:** Synthesized Python package with matrix functions and `AgentRuntime` ready for simulation.
- **Downstream:** `runtime/` executes the synthesized matrices in an active inference agent loop.
- **Validation:** `idempotency.py` feeds the synthesized package back through the forward pipeline to report `STRUCTURALLY_ISOMORPHIC`, `ROLE_PRESERVED`, `DRIFT`, or `FAILED`.

## Key improvements (current)

- **POLICY stub emission** — generates `decide_*` methods proportional to the origin GNN's POLICY role count.
- **CONTEXT stub emission** — generates `get_context_*` methods for CONFIG/CONTEXT roles.
- **CONSTRAINT fix** — scales `check_*` stub generation to match origin constraint counts (previously fixed scaffolding).

These changes resolved the earlier role-preservation gap in the roundtrip evaluation. They are not claimed as strict structural isomorphism unless the full invariant ledger passes.

## Files

- `parser.py` — `ReverseGNNModel`, `parse_gnn` — parses GNN markdown and JSON.
- `planner.py` — `PackagePlan`, `NodePlan`, `plan_package` — structure planning for synthetic package.
- `synthesizer.py` — `synthesize_package` — generates Python code with matrix functions and runtime.
- `callable.py` — `MatrixFunctions`, `make_matrix_functions` — non-exec matrix functions (likelihood, transition, EFE, best_action).
- `idempotency.py` — `verify_roundtrip`, `verify_repo_roundtrip`, `compute_isomorphism_report` — round-trip validation.
- `metrics.py` — `RoundtripMetrics`, role and matrix comparators — isomorphism scoring.
- `__init__.py` — public API.
