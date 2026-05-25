# Agents - multi_package_workspace/packages

## Scope

Fixture package roots used to test workspace-aware ingestion and import
resolution.

## Rules

- Keep package names stable: tests and examples refer to `app_pkg` and `core_pkg`.
- Avoid packaging metadata here; this is a source-layout fixture, not a distributable project.
- If adding a package, update the parent fixture README and run a translate smoke.
