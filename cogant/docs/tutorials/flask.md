# Flask app walkthrough

> **What this page is:** An end-to-end COGANT walkthrough on a six-module, 853-line Flask fixture, with role distributions and Markov blanket inspection.
>
> **Prerequisites:** [Calculator walkthrough](calculator.md) or [Tutorial 2](02_small_repo_walkthrough.md), and basic Flask familiarity.
>
> **Reading time:** ~15 minutes
>
> **Next steps:** [Tutorial 3: Flask app walkthrough (98 nodes, 597 edges)](03_flask_walkthrough.md) · [Tutorial 5: Reading the A/B/C/D matrices](05_gnn_interpretation.md) · [Markov blankets in codebases](../concepts/markov_blanket.md)

A walkthrough of COGANT on the `flask_app` fixture under `examples/real_world/flask_app/`: a six-module Flask application (`__init__.py`, `app.py`, `config.py`, `models.py`, `services.py`, `utils.py`) totalling **853 lines** of Python, analyzed end-to-end by the pipeline.

> **Theory background:** This walkthrough is the bigger sibling of `calculator.md` and exercises
> the same conceptual machinery on real-world code. The role distribution table below is
> produced by [role assignment](../concepts/role_assignment.md), the agent / non-agent split is
> the [Markov blanket](../concepts/markov_blanket.md) over the [program graph](../concepts/program_graph.md),
> and the exported bundle format is documented under [GNN](../concepts/gnn.md).

## Run it

```bash
cogant translate examples/real_world/flask_app \
  --output output/flask_app \
  --layout-output
cogant validate output/flask_app/gnn_package
```

## Repository-level numbers

Canonical metrics from `../evaluation/figures/metrics.json`:

| Metric | Value |
| --- | --- |
| Source files discovered | 6 |
| Lines analyzed | 853 |
| **Nodes** | **98** |
| **Edges** | **597** |
| Total semantic mappings | 51 |
| GNN package files | 19 |
| GNN validation | PASS (score 100.0, 0 errors, 0 warnings) |

## Node kind distribution

| Node kind | Count | Percentage |
| --- | ---: | ---: |
| MODULE | 6 | 6.1% |
| CLASS | 25 | 25.5% |
| METHOD | 57 | 58.2% |
| FUNCTION | 10 | 10.2% |

The v0.1.x Python front end emits the structural core: `MODULE`, `CLASS`, `METHOD`, `FUNCTION`. The richer taxonomy declared in `cogant.schemas.core.NodeKind` (variables, parameters, type references, control-flow nodes) is roadmap — tracked as P1-2 / P1-3 in `../evaluation/SCOPING_REPORT.md`.

## Edge kind distribution

| Edge kind | Count | Percentage |
| --- | ---: | ---: |
| CALLS | 433 | 72.5% |
| CONTAINS | 92 | 15.4% |
| READS | 38 | 6.4% |
| WRITES | 15 | 2.5% |
| IMPORTS | 10 | 1.7% |
| INHERITS | 9 | 1.5% |

The CALLS-heavy distribution reflects `CallGraphBuilder`, which walks every `ast.Call` and attaches an edge between the enclosing function or method and its callee when the callee resolves inside the project.

## Active Inference role assignments

On the related `flask_mini` fixture the same rule set produces:

| Role | Count | Representative nodes |
| --- | ---: | --- |
| HIDDEN_STATE | 3 | `Request`, `Response`, `Application` (hold mutated attrs) |
| OBSERVATION | 2 | `/routes`-style handlers that only read app state |
| ACTION | 8 | `db_write`, setter/mutator methods |
| POLICY | 6 | `Middleware`, `LoggingMiddleware`, `AuthMiddleware`, `Route`, `route`, `match_route` |
| CONSTRAINT | 0 | — |
| **Total** | **19** | |

Mnemonic: **OBSERVATION = routes**, **ACTION = db_write**, **HIDDEN_STATE = app_state**. Middlewares and routers land in POLICY because they match the `Handler / Middleware / Router / Controller / Manager` keyword set in `PolicyRule`.

## Semantic mapping excerpt

```text
Node: get_users  (kind=FUNCTION, file=routes/users.py:14)
  Matched rule: rule_fn_def_001
  Target role:  FUNCTION_DEF
  Confidence:   0.98  (base=1.0, -0.02 missing docstring penalty)
  Provenance:   SourceCode

Node: db.session.query  (kind=FUNCTION, file=routes/users.py:22)
  Matched rule: rule_method_call_001
  Target role:  METHOD_CALL
  Confidence:   0.82  (base=0.90, -0.08 receiver type inferred heuristically)
  Provenance:   Heuristic

Node: User  (kind=TYPE, file=models/user.py:5)
  Matched rule: rule_type_def_001
  Target role:  TYPE_DEF
  Confidence:   1.00
  Provenance:   SourceCode
```

The `db.session.query` call is a textbook heuristic-provenance hit: the receiver type of `session` is resolved by import tracing rather than explicit annotation, dropping the confidence to 0.82 and landing in the MEDIUM tier.

## State-space excerpt (`/users` endpoint)

When dynamic traces are available, the state-space compiler produces behavioral transitions alongside the static graph:

```json
{
  "variables": [
    {"name": "request.method", "type": "str",  "domain": ["GET", "POST"]},
    {"name": "db_connected",   "type": "bool", "domain": [true, false]},
    {"name": "response_code",  "type": "int",  "domain": [200, 400, 500]}
  ],
  "actions": [
    {"name": "validate_input",  "source": "routes/users.py:18"},
    {"name": "query_database",  "source": "routes/users.py:22"},
    {"name": "format_response", "source": "routes/users.py:30"}
  ],
  "transitions": [
    {
      "from_state": {"request.method": "GET", "db_connected": true},
      "action": "query_database",
      "to_state": {"response_code": 200},
      "confidence": 0.94,
      "tier": "STATIC_PLUS_RUNTIME"
    },
    {
      "from_state": {"request.method": "POST", "db_connected": true},
      "action": "validate_input",
      "to_state": {"response_code": 400},
      "confidence": 0.71,
      "tier": "STATIC_ONLY"
    },
    {
      "from_state": {"db_connected": false},
      "action": "query_database",
      "to_state": {"response_code": 500},
      "confidence": 0.58,
      "tier": "RUNTIME_ONLY"
    }
  ]
}
```

Confidence tiers follow `determine_confidence_tier`:

- **STATIC_PLUS_RUNTIME** (c >= 0.65) — both AST and trace evidence.
- **STATIC_ONLY** (c >= 0.5) — AST only.
- **RUNTIME_ONLY** (c >= 0.4) — trace only, no static corroboration.
- **HUMAN_REVIEWED** (c >= 0.9) — manually curated.

## Failure modes

- **No dynamic traces** — `enrich_graph()` is a no-op; every transition stays in `STATIC_ONLY` or lower. The `evidence_sources` list on the graph metadata is the at-a-glance signal.
- **Partial coverage** — `_enrich_with_coverage` annotates only the matched files and logs unmatched ones informationally; check the enrichment summary count.
- **Unmatched nodes** — `TranslationEngine.get_coverage_report()` exposes `uncovered_node_ids` as an explicit gap list, not an error.
- **Fixpoint non-convergence** — bounded at `max_iterations = 10`; emits `"Max iterations reached without convergence"` and proceeds to conflict resolution.
- **Optional stage failure** — `dynamic`, `translate`, `state_space`, and `process` have `skip_on_error=True`; the bundle still validates with the other stages' outputs.
