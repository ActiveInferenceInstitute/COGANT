# AGENTS.md - COGANT planning notes

This directory contains current planning and audit notes for broad project work.

## Rules

- Prefer short planning notes tied to active gates.
- Keep raw command output in `_artifacts/`; keep synthesized decisions in the
  top-level plan files.
- Before using a plan as current evidence, re-run the relevant validation
  command from the project root.
- If a plan contradicts active package docs, manuscript prose, or
  `cogant/evaluation/METRICS.yaml`, treat the active source as authoritative
  and update or remove the plan.

## Validation

The project folder-docs gate expects this directory and `_artifacts/` to keep
both `README.md` and `AGENTS.md` files:

```bash
uv run python tools/audit_folder_docs.py
```
