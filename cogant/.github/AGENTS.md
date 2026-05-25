# Agents - cogant/.github

## Scope

Package-local GitHub metadata. Keep it in sync with the staging-root GitHub
configuration when a workflow is meant to run in both layouts.

## Coordination

- Active template workflows live at [`../../.github/workflows/`](../../.github/workflows/).
- Package docs for CI live at [`../docs/CI.md`](../docs/CI.md).
- If a workflow assumes the inner package root, say so in a comment near its `run` step.
