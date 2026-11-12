# scripts

Thin orchestration scripts (not importable as `cogant.*`).

- `repository_inference.py` — source export, typed model rollout and separate roundtrip evidence
- `gnn_conformance_probe.py` — pinned upstream GNN conformance probe used by `run_gate.py gnn` and the `gnn-conformance` CI job
- Run from the inner package root: `uv run python scripts/repository_inference.py --output output/repository_execution`
- The output directory must be new; translation logs, GNN, inference trace, roundtrip artifacts and scope-qualified report are retained.
- Business logic stays in `py/cogant/`; scripts coordinate only
- Agent notes: [AGENTS.md](AGENTS.md) · Package root: [../README.md](../README.md)
