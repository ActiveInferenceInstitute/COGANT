# Workflow Engine Example

Workflow execution engine demonstrating complex control flow and state management.

CLI reference: [docs/cli_reference.md](../../docs/cli_reference.md).

## Structure

```
workflow-engine/
├── src/
│   ├── engine.py        # Workflow engine core
│   ├── scheduler.py     # Task scheduler
│   ├── state.py         # State management
│   └── tasks.py         # Task definitions and handlers
└── tests/
    └── test_engine.py
```

## Analysis

From the repository root:

```bash
cogant translate examples/workflow-engine --output output/workflow-engine
```

Interactive HTML (`cogant render`) expects a **bundle-shaped JSON** (see [docs/cli_reference.md](../../docs/cli_reference.md)). Save one via `Bundle.save_json(...)` after a pipeline run, or use [example_pipeline.py](../example_pipeline.py).

Expected output: complex control flow, state transitions, variable tracking

## Demonstrates
- Complex control flow patterns
- State machine modeling
- Plugin architecture
- Recursion and mutual calls
- Temporal reasoning (with state space)
