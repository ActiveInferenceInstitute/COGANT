# Agents — py/cogant/reverse

## Owner

Semantic Lead

## Responsibilities

**GNN → Python synthesis and round-trip validation:**

1. **Parse GNN markdown** (`parser.py`) — read the 18-section GNN format, validate structure, extract matrices (A/B/C/D), state variables, and role counts.
2. **Plan package structure** (`planner.py`) — generate a `PackagePlan` that maps GNN roles to Python classes and functions (HIDDEN_STATE → class attributes, OBSERVATION → @property getters, ACTION → methods, POLICY → decision logic, CONSTRAINT → assertions, CONTEXT → config).
3. **Synthesize Python package** (`synthesizer.py`) — emit runnable Python code with matrix functions (`likelihood`, `transition`, `expected_free_energy`, `best_action`), an `AgentRuntime`, and stubs for each role.
4. **Verify round-trip isomorphism** (`idempotency.py`) — run the forward pipeline on the synthesized package and compare role distributions. v0.5.0 achieves **23/23 ISOMORPHIC** (ε ≥ 0.8, with mean ε = 1.0).
5. **Compute isomorphism metrics** (`metrics.py`) — generate detailed breakdowns of which roles were preserved, lost, or added during synthesis.

## Coordination

- **Input:** GNN markdown bundle from export stage (18 sections, A/B/C/D matrices, semantic mappings).
- **Output:** Synthesized Python package with matrix functions and `AgentRuntime` ready for simulation.
- **Downstream:** `runtime/` executes the synthesized matrices in an active inference agent loop.
- **Validation:** `idempotency.py` feeds the synthesized package back through the forward pipeline to verify semantic fidelity.

## Key improvements (v0.5.0)

- **POLICY stub emission** — generates `decide_*` methods proportional to the origin GNN's POLICY role count.
- **CONTEXT stub emission** — generates `get_context_*` methods for CONFIG/CONTEXT roles.
- **CONSTRAINT fix** — scales `check_*` stub generation to match origin constraint counts (previously fixed scaffolding).

These changes resolved the 19→23 ISOMORPHIC gap in the roundtrip evaluation.

## Files

- `parser.py` — `ReverseGNNModel`, `parse_gnn` — parses GNN markdown and JSON.
- `planner.py` — `PackagePlan`, `NodePlan`, `plan_package` — structure planning for synthetic package.
- `synthesizer.py` — `synthesize_package` — generates Python code with matrix functions and runtime.
- `callable.py` — `MatrixFunctions`, `make_matrix_functions` — non-exec matrix functions (likelihood, transition, EFE, best_action).
- `idempotency.py` — `verify_roundtrip`, `verify_repo_roundtrip`, `compute_isomorphism_report` — round-trip validation.
- `metrics.py` — `RoundtripMetrics`, role and matrix comparators — isomorphism scoring.
- `__init__.py` — public API.
