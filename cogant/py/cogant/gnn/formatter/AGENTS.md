# Agents — py/cogant/gnn/formatter

## Owner

GNN Lead

## Responsibilities

Split implementation of `GNNMarkdownFormatter`: base class plus mixins (`upstream`, `metadata`, `structural`, `dynamics`, `semantic`) so each file stays maintainable while preserving stable markdown output. Re-exports `UPSTREAM_REQUIRED_SECTIONS` / `UPSTREAM_OPTIONAL_SECTIONS`.

## Coordination

Imported as `cogant.gnn.formatter`; consumed by `gnn/package.py` and export paths. Changes affect GNN markdown checksums and validation.

## Files

- `base.py` — formatter class, `format()`, shared helpers.
- `upstream.py` — upstream-canonical GNN header sections, validated against the pinned `generalized-notation-notation` v5.0.1 release (`validate_gnn_syntax` at `standard` / `strict`, upstream steps 3/5/6): grouped multi-source connections `(A_m0, s_f0)>o_m0`, row-major A/B literals without an extra paren layer, column-stochastic A, and a declared `G` whenever connections route into it. The `GNN v2.0.0` header value is COGANT's own schema identifier.
- `metadata.py`, `structural.py`, `dynamics.py`, `semantic.py` — section families.
- `__init__.py` — `GNNMarkdownFormatter` and upstream section constants.
