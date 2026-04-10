# Tutorial 2: Small repo walkthrough — `event_pipeline`

> **Goal.** Translate the `event_pipeline` control-positive fixture step by step, watch each pipeline stage, and connect each rule firing to its source code.

The `event_pipeline` fixture under `examples/control_positive/event_pipeline/` is a three-file
event processing microservice with retry logic, a bus, and a handler hierarchy. It is the
smallest fixture that exercises the behavioral and resilience rule families.

> **Companion deep-dive:** the single-class minimum example is documented in
> [`calculator.md`](calculator.md). Read this tutorial for the step-by-step staging flow and
> `calculator.md` for the Markov blanket details.

## 1. Discover the fixture

```bash
ls examples/control_positive/event_pipeline/
# event_bus.py  handlers.py  pipeline.py
```

Run `scan` first to see what the ingest stage picks up before any graph construction:

```bash
uv run cogant scan examples/control_positive/event_pipeline
```

Expected output shape:

```text
scan: examples/control_positive/event_pipeline
  Files discovered:     3
  Python files:         3
  Total lines:          ~180
  Excluded by policy:   0
  Provenance attached:  yes
```

## 2. Build the program graph incrementally

```bash
uv run cogant graph examples/control_positive/event_pipeline \
    --output output/event_pipeline_graph.json
```

This runs only up through the graph stage (skipping translation, state-space, and export). Peek
at the shape of the graph:

```bash
uv run python -c "
import json
g = json.load(open('output/event_pipeline_graph.json'))
stats = g['statistics']
print(f\"nodes: {stats['total_nodes']}\")
print(f\"edges: {stats['total_edges']}\")
for k, v in stats['node_kinds'].items():
    print(f\"  {k}: {v}\")
for k, v in stats['edge_kinds'].items():
    print(f\"  {k}: {v}\")
"
```

You should see something close to:

```text
nodes: 23
edges: 52
  MODULE: 3
  CLASS: 5
  METHOD: 12
  FUNCTION: 3
  CALLS: 28
  CONTAINS: 14
  IMPORTS: 5
  INHERITS: 3
  WRITES: 2
```

## 3. Run full translation and inspect each stage

```bash
uv run cogant translate examples/control_positive/event_pipeline \
    --output output/event_pipeline \
    --layout-output
```

The `bundle.json` exposes a `stages` dict with one entry per stage. Each stage has a `status`,
a `duration_ms`, and stage-specific artifacts. Print the stage summary:

```bash
uv run python -c "
import json
data = json.load(open('output/event_pipeline/bundle.json'))
for name, stage in data['stages'].items():
    print(f\"{name:12s} {stage['status']:8s} {stage['duration_ms']:>6d} ms\")
"
```

Expected shape:

```text
ingest       ok             25 ms
static       ok             80 ms
normalize    ok             18 ms
graph        ok             42 ms
translate    ok            120 ms
statespace   ok             35 ms
process      ok             15 ms
export       ok             60 ms
validate     ok             30 ms
```

## 4. Tie each mapping back to its rule

The `translate` stage records which rule fired on each node:

```bash
uv run python -c "
import json
data = json.load(open('output/event_pipeline/bundle.json'))
mappings = data['stages']['translate']['mappings']
for m in mappings:
    print(f\"{m['rule_id']:28s} {m['kind']:12s} {m['qualified_name']}\")
"
```

Expected role distribution on `event_pipeline` (from
`../evaluation/figures/metrics.json`, 2026-04-09 run):

| Role | Count | Representative nodes |
| --- | ---: | --- |
| HIDDEN_STATE | 1 | `EventPipeline` (mutable buffer + state machine) |
| OBSERVATION | 9 | `get_status`, `read_metrics`, `list_subscribers`, ... |
| ACTION | 6 | `publish`, `handle`, `dispatch`, `retry`, ... |
| POLICY | 4 | `RetryPolicy`, `EventBus`, `BaseHandler` subclasses |
| CONSTRAINT | 0 | — |
| **Total** | **20** | |

Each count lines up with the qualitative assertions in
`tests/unit/test_ai_role_validation.py::test_event_pipeline_qualitative`.

## 5. Markov blanket

```bash
uv run cogant viz output/event_pipeline --diagram blanket \
    --output output/event_pipeline/diagrams/
```

The default `auto` seed strategy scores each module and picks `event_bus` for this fixture. The
resulting blanket (also visible in `bundle.json` under `stages.statespace.blanket`):

| Role | Count | Internal ratio | Boundary ratio |
| --- | ---: | ---: | ---: |
| Internal (mu) | 3 |  |  |
| Sensory (s) | 1 |  |  |
| Active (a) | 1 |  |  |
| External (eta) | 18 | 0.130 | 0.087 |

Low internal ratio reflects that the blanket's seed set (one module) is small relative to the
whole graph — exactly the counter-intuitive but correct behavior explained in
[`calculator.md § Why the module is external`](calculator.md#why-the-module-is-external).

## 6. What you've learned

By this point you have seen:

1. The `scan` stage emits provenance without touching AST semantics.
2. The `graph` stage produces a typed property graph with strictly four node kinds in v0.1.0.
3. The `translate` stage runs the 19-rule fixpoint engine and keeps the decision trace.
4. Each semantic mapping is anchored in at least one rule evidence snippet.
5. The Markov blanket partition is deterministic for a fixed graph and seed set.

## Next

- [Tutorial 3: Flask walkthrough](03_flask_walkthrough.md) — larger real-world app.
- [Tutorial 4: Writing a custom rule](04_custom_rules.md) — how to extend the fixpoint engine.
- [Tutorial 5: Reading GNN matrices](05_gnn_interpretation.md) — turn the state space into A/B/C/D.
