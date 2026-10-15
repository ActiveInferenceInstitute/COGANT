# Agents — scripts/

## Owner

Runtime Lead (thin orchestrators)

## Responsibilities

Repository-level orchestration scripts that use public COGANT APIs and persist inspectable artifacts.

## Coordination

Business logic stays in `py/cogant/`; scripts coordinate only. Run from the inner package root with `uv run python scripts/<name>.py` as documented per script.

## Files

- `repository_inference.py` — source translation, typed model rollout and independent roundtrip evidence; requires a new output directory.
