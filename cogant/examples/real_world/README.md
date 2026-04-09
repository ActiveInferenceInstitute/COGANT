# real_world — integration fixtures from realistic Python code

The `examples/control_positive/` repos (``calculator``,
``event_pipeline``, ``flask_mini``) are tiny hand-crafted demos. They
let us verify the pipeline against pristine code where every node and
edge is predictable, but they do not exercise the pipeline against the
shapes and scale of real-world Python.

The fixtures in this directory fill that gap:

| Fixture        | Shape                                                        | Provenance                  |
|----------------|--------------------------------------------------------------|-----------------------------|
| `flask_app/`   | Flask + SQLAlchemy style web app (config, models, services) | Hand-written stub            |
| `requests_lib/`| requests-style HTTP client (session, adapters, auth)        | Hand-written stub            |
| `json_stdlib/` | ``json/__init__.py``, ``decoder``, ``encoder``, ``scanner``  | CPython 3.11 ``Lib/json/``   |

For the hand-written fixtures we deliberately avoid importing the real
third-party libraries: that keeps the repo lightweight, fully
hermetic, and insulated from upstream churn. For ``json_stdlib`` we use
the genuine CPython files because they are pure Python, stable across
releases, and a great stress test for the ingest/parse/graph stages.

## Quality bar

The fixtures are exercised by `tests/integration/test_real_world_pipeline.py`,
which checks that:

1. ``RoundtripOrchestrator.run()`` completes without raising.
2. ``program_graph.json`` is emitted with non-empty nodes.
3. ``semantic_mappings.json`` is emitted with at least one mapping.
4. ``model.gnn.md`` contains the canonical sections emitted by the GNN
   formatter.
