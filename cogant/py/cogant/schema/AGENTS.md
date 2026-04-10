# Agents — py/cogant/schema

## Owner

GNN Lead

## Responsibilities

GNN format versioning: `SchemaVersion`, required section lists for v1.0/v1.1, `detect_version`, and `migrate_gnn` between schema revisions.

## Coordination

Upstream of `gnn/validator` and markdown export; keep section constants aligned with specs and docs.

## Files

- `versions.py` — `SchemaVersion`, `GNN_V1_0_REQUIRED_SECTIONS`, `GNN_V1_1_REQUIRED_SECTIONS`.
- `detector.py` — `detect_version`.
- `migrations.py` — `migrate_gnn`.
- `__init__.py` — public exports.
