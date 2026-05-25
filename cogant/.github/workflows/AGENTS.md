# Agents - cogant/.github/workflows

## Scope

Package-root GitHub Actions workflows. These differ from staging-root workflows
because their working directory is the inner package root that contains
`mkdocs.yml`.

## Rules

- Document any required working directory directly in workflow comments.
- Keep action versions aligned with [`../../../.github/workflows/AGENTS.md`](../../../.github/workflows/AGENTS.md) when the same job exists in both layouts.
- Update [`../../docs/CI.md`](../../docs/CI.md) when job names, gates, or deployment behavior change.
