# Agents — py/cogant/gnn/formatter

## Owner

GNN Lead

## Responsibilities

Split implementation of `GNNMarkdownFormatter`: base class plus mixins (`upstream`, `metadata`, `structural`, `dynamics`, `semantic`) so each file stays maintainable while preserving stable markdown output. Re-exports `UPSTREAM_REQUIRED_SECTIONS` / `UPSTREAM_OPTIONAL_SECTIONS`.

## Coordination

Imported as `cogant.gnn.formatter`; consumed by `gnn/package.py` and export paths. Changes affect GNN markdown checksums and validation.

## Files

- `base.py` — formatter class, `format()`, shared helpers.
- `upstream.py` — upstream GNN v1.1 canonical header sections.
- `metadata.py`, `structural.py`, `dynamics.py`, `semantic.py` — section families.
- `__init__.py` — `GNNMarkdownFormatter` and upstream section constants.
