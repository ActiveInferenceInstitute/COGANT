# `src/` (template compatibility)

The research template’s default layout places importable code under `projects/<name>/src/`. COGANT’s **released Python package** lives under the nested tree [`../cogant/py/cogant/`](../cogant/py/cogant/) (package name `cogant`, configured from [`../cogant/pyproject.toml`](../cogant/pyproject.toml)).

After promotion to `projects/cogant/`, you may leave this directory as documentation-only, or add a `src/cogant` symlink or shim to align with tools that assume `src/` — see [`../PROMOTION.md`](../PROMOTION.md).
