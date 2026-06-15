# Tutorial 3: Flask app walkthrough — 98 nodes, 597 edges

> **What this page is:** A walkthrough of COGANT on a real-world six-module Flask application — the largest fixture you can still trace by hand.
>
> **Prerequisites:** [Tutorial 2: Small repo walkthrough](02_small_repo_walkthrough.md) and basic Flask familiarity.
>
> **Reading time:** ~25 minutes
>
> **Next steps:** [Tutorial 5: Reading the A/B/C/D matrices](05_gnn_interpretation.md) · [Tutorial 6: Reverse mode](06_reverse_mode.md) · [Markov blankets in codebases](../concepts/markov_blanket.md)

> **Goal.** Translate a six-module real-world Flask application and read the full GNN bundle. This is the largest "hand-traceable" fixture in the repo.

> **Theory background:** The role distribution you will see (HIDDEN_STATE / OBSERVATION /
> ACTION / CONSTRAINT) comes from COGANT's [role assignment system](../concepts/role_assignment.md),
> and the agent / non-agent split shown in the partition table is the
> [Markov blanket](../concepts/markov_blanket.md) over the program graph. Both concept pages are
> short reads and make the numeric tables below much easier to interpret.

The `flask_app` fixture lives at `examples/real_world/flask_app/` and contains six Python
modules totalling 853 lines: `__init__.py`, `app.py`, `config.py`, `models.py`, `services.py`,
`utils.py`. Everything in this tutorial is reproducible from a clean checkout.

> **Companion deep-dive:** see [`flask.md`](flask.md) for the canonical numeric breakdown
> (node kind / edge kind / tier counts). This tutorial walks through the pipeline end-to-end
> with commentary.

## 1. Translate

```bash
uv run cogant translate examples/real_world/flask_app \
    --output output/flask_app \
    --layout-output

uv run cogant validate output/flask_app/gnn_package
```

Expected validator output:

```text
GNN validation: output/flask_app/gnn_package
  Score:    100.0 / 100
  Errors:   0
  Warnings: 0
```

## 2. The numbers

Canonical metrics from `../evaluation/figures/metrics.json` (2026-04-09 run):

| Metric | Value |
| --- | --- |
| Source files | 6 |
| Lines analyzed | 853 |
| **Program graph nodes** | **98** |
| **Program graph edges** | **597** |
| Semantic mappings (after conflict resolution) | 51 |
| GNN package files | 19 |
| GNN validator score | 100.0 / 100 |

### Node kinds (98 total)

| Kind | Count | % |
| --- | ---: | ---: |
| MODULE | 6 | 6.1 |
| CLASS | 25 | 25.5 |
| METHOD | 57 | 58.2 |
| FUNCTION | 10 | 10.2 |

The current Python front end emits these structural kinds for the canonical
Flask fixture, and the selected orchestration path also records call,
containment, import, inheritance, and READS/WRITES edges. The richer taxonomy in
`cogant.schemas.core.NodeKind` (variables, parameters, type references, control-flow
nodes) is still available to parsers and plugins; expanding fixture evidence for
those long-tail kinds is tracked as P1-2 / P1-3 in [`../evaluation/SCOPING_REPORT.md`](https://github.com/ActiveInferenceInstitute/COGANT/blob/main/docs/evaluation/SCOPING_REPORT.md).

### Edge kinds (597 total)

| Kind | Count | % |
| --- | ---: | ---: |
| CALLS | 433 | 72.5 |
| CONTAINS | 92 | 15.4 |
| READS | 38 | 6.4 |
| WRITES | 15 | 2.5 |
| IMPORTS | 10 | 1.7 |
| INHERITS | 9 | 1.5 |

The CALLS-heavy distribution reflects `CallGraphBuilder`, which walks every `ast.Call` and
emits an edge whenever the callee resolves inside the project.

## 3. Role assignments on the closely-related `flask_mini`

The qualitative validator (`tests/unit/test_ai_role_validation.py`) runs against the smaller
`flask_mini` fixture and asserts exact counts per role. Reproduced here so you can map rule
output back to the hand-curated ground truth:

| Role | Count | Representative nodes |
| --- | ---: | --- |
| HIDDEN_STATE | 3 | `Request`, `Response`, `Application` (each has incoming `WRITES`) |
| OBSERVATION | 2 | Route handlers that only `READ` app state |
| ACTION | 8 | `db_write`, `handle_request`, setter methods, ... |
| POLICY | 6 | `Middleware`, `LoggingMiddleware`, `AuthMiddleware`, `Route`, `route`, `match_route` |
| CONSTRAINT | 0 | — |
| **Total** | **19** | |

Mnemonic: **OBSERVATION = read-only routes**, **ACTION = db_write / setters**,
**HIDDEN_STATE = Request / Response / Application**, **POLICY = *Handler / Middleware / Router**.

The full `flask_app` fixture produces 51 mappings (larger codebase, richer inheritance graph);
the role proportions track `flask_mini` closely.

## 4. A semantic mapping with evidence

```bash
uv run python -c "
import json
data = json.load(open('output/flask_app/bundle.json'))
for m in data['stages']['translate']['mappings']:
    if m['qualified_name'].endswith('get_users'):
        print(json.dumps(m, indent=2))
        break
"
```

Expected shape:

```text
Node: get_users  (kind=FUNCTION, file=services.py:14)
  Matched rule: ObservationRule
  Target role:  OBSERVATION
  Confidence:   0.98  (base=1.0, -0.02 missing docstring penalty)
  Provenance:   SourceCode
  Evidence:
    - name keyword match: 'get'
    - READS edge count: 3
    - WRITES edge count: 0
```

An interesting contrast is `db.session.query`: receiver type of `session` is inferred via
import tracing rather than explicit annotation, dropping the confidence to ~0.82 and landing
the node in the MEDIUM confidence tier with `Provenance: Heuristic`.

## 5. State-space excerpt

The `statespace` stage compiles an explicit state-space model for any subsystem that exposes
a recognizable state machine. For the `/users` route:

```json
{
  "variables": [
    {"name": "request.method", "type": "str",  "domain": ["GET", "POST"]},
    {"name": "db_connected",   "type": "bool", "domain": [true, false]},
    {"name": "response_code",  "type": "int",  "domain": [200, 400, 500]}
  ],
  "actions": [
    {"name": "validate_input",  "source": "services.py:18"},
    {"name": "query_database",  "source": "services.py:22"},
    {"name": "format_response", "source": "services.py:30"}
  ],
  "transitions": [
    {"from_state": {"request.method": "GET",  "db_connected": true},
     "action": "query_database",
     "to_state":   {"response_code": 200},
     "confidence": 0.94, "tier": "STATIC_PLUS_RUNTIME"},
    {"from_state": {"request.method": "POST", "db_connected": true},
     "action": "validate_input",
     "to_state":   {"response_code": 400},
     "confidence": 0.71, "tier": "STATIC_ONLY"},
    {"from_state": {"db_connected": false},
     "action": "query_database",
     "to_state":   {"response_code": 500},
     "confidence": 0.58, "tier": "RUNTIME_ONLY"}
  ]
}
```

Confidence tiers (`determine_confidence_tier`):

- **STATIC_PLUS_RUNTIME** (c >= 0.65) — AST and trace evidence agree.
- **STATIC_ONLY** (c >= 0.5) — AST-only.
- **RUNTIME_ONLY** (c >= 0.4) — trace-only.
- **HUMAN_REVIEWED** (c >= 0.9) — manually curated.

## 6. GNN export excerpt

Snippet from `output/flask_app/gnn_package/model.gnn.md`:

```text
## StateSpaceBlock
s_f0[3,1,type=int]        # observation: request.method, db_connected, response_code
u_f0[3,1,type=int]        # action id: validate_input, query_database, format_response
x_f0[6,1,type=float]      # hidden state: Application + Request/Response + db_connected

## Connections
x_f0 > s_f0               # hidden state emits observation
u_f0 > x_f0               # action updates hidden state
x_f0 > x_f0               # persistence
```

## 7. Failure modes worth knowing

- **No dynamic traces** — `enrich_graph()` is a no-op; every transition stays in `STATIC_ONLY`.
- **Partial coverage** — `_enrich_with_coverage` logs unmatched files; check the enrichment
  summary count in the stage output.
- **Unmatched nodes** — `TranslationEngine.get_coverage_report()` exposes `uncovered_node_ids`
  as an explicit gap list (not an error).
- **Fixpoint non-convergence** — bounded at `max_iterations = 10`; the engine emits
  `"Max iterations reached without convergence"` and proceeds to conflict resolution.
- **Optional stage failure** — `dynamic`, `translate`, `statespace`, and `process` all run with
  `skip_on_error=True`; the bundle still validates with the remaining stages' outputs.

## Next

- [Tutorial 4: writing a custom rule](04_custom_rules.md) — add your own role detector.
- [Tutorial 5: reading GNN matrices](05_gnn_interpretation.md) — the full A/B/C/D decoder.
- [`flask.md`](flask.md) — canonical deep-dive with every number and rule-level tuning.
