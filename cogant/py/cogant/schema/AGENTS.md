# Agents — py/cogant/schema

## Owner

GNN Lead

## Responsibilities

Current GNN format detection: `CURRENT_GNN_VERSION`, `UNSUPPORTED_GNN_VERSION`, `GNN_V2_REQUIRED_SECTIONS`, and `detect_version`.

## Coordination

Upstream of `gnn/validator` and markdown export; keep section constants aligned with specs and docs.

## Files

- `versions.py` — `CURRENT_GNN_VERSION`, `UNSUPPORTED_GNN_VERSION`, `GNN_V2_REQUIRED_SECTIONS`.
- `detector.py` — `detect_version`.
- `__init__.py` — public exports.
