# AGENTS.md - CLI Commands

This package owns concrete CLI command callbacks.

Rules:

- Put reusable behavior in `cogant.api`, `cogant.pipeline`, or other domain
  modules rather than burying it in a command callback.
- Keep command names, options, and stage lists synchronized with
  `tools/audit_stage_list.py` and the CLI docs.
- Add tests under `cogant/tests/unit/` for option parsing, defaults, and error
  behavior when changing a command.
- Prefer explicit exit behavior and clear stderr/stdout contracts.
