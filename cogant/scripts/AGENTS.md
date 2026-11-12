# Agents — scripts/

## Owner

Runtime Lead (thin orchestrators)

## Responsibilities

Repository-level orchestration scripts that use public COGANT APIs and persist inspectable artifacts.

## Coordination

Business logic stays in `py/cogant/`; scripts coordinate only. Run from the inner package root with `uv run python scripts/<name>.py` as documented per script.

## Files

- `repository_inference.py` — source translation, typed model rollout and independent roundtrip evidence; requires a new output directory.
- `gnn_conformance_probe.py` — emits a package from `examples/control_positive/calculator`, validates it at the pinned upstream parser's `standard` and `strict` levels, and runs upstream steps 3, 5 and 6; invoked by `run_gate.py gnn` and the `gnn-conformance` CI job.
