# AGENTS.md - COGANT planning notes

This directory contains planning and audit notes for broad project work.

## Rules

- Prefer adding short, dated planning notes over editing old audit records.
- Keep raw command output in `_artifacts/`; keep synthesized decisions in the
  top-level plan files.
- Before using a plan as current evidence, re-run the relevant validation
  command from the project root.
- If a plan contradicts active package docs, manuscript prose, or
  `cogant/evaluation/METRICS.yaml`, treat the active source as authoritative
  and update the plan only as historical context.

## Validation

The project folder-docs gate expects this directory and `_artifacts/` to keep
both `README.md` and `AGENTS.md` files:

```bash
uv run python tools/audit_folder_docs.py
```
