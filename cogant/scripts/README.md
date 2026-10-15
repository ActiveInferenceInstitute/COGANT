# scripts

Thin orchestration scripts (not importable as `cogant.*`).

- `repository_inference.py` — source export, typed model rollout and separate roundtrip evidence
- Run from the inner package root: `uv run python scripts/repository_inference.py --output output/repository_execution`
- The output directory must be new; translation logs, GNN, inference trace, roundtrip artifacts and scope-qualified report are retained.
- Business logic stays in `py/cogant/`; scripts coordinate only
- Agent notes: [AGENTS.md](AGENTS.md) · Package root: [../README.md](../README.md)
