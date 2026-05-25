# Agents - scripts/code_quality

## Scope

Local code-quality orchestration scripts for maintainers. Scripts here may be
useful during a hardening pass, but they are not part of the public COGANT CLI.

## Rules

- Keep scripts directory-independent by anchoring paths on `__file__`.
- Do not make these scripts mutate repo files unless the command name and help text make that explicit.
- Promote reusable audits to [`../../tools/`](../../tools/) so they can be called from CI and manuscript workflows.
