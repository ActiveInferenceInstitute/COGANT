# AGENTS.md — repository documentation index

This top-level `docs/` folder holds exactly one page, [`README.md`](README.md),
the repository-level map of COGANT's documentation. It is **not** the MkDocs
site source; the published site lives under [`../cogant/docs/`](../cogant/docs/index.md).

## Purpose

[`README.md`](README.md) is the single root-level entry point for a reader who has
only this checkout: it links each documentation area (module hubs under
`cogant/docs/`, root-level documents, the manuscript, and the sidecar) instead of
duplicating their content. Each `cogant/docs/<module>/README.md` remains the table
of contents for that module.

## What belongs here

- The repository-level index ([`README.md`](README.md)) only.
- Relative links into `cogant/docs/`, the repository root, [`../manuscript/`](../manuscript/README.md),
  and [`../.aii/`](../.aii/README.md).

Do not add a second copy of package documentation, and do not move pages out of
`cogant/docs/` into this folder — the MkDocs build reads `cogant/docs/` only.

## Keeping it current

- When a top-level module directory is added to or removed from `cogant/docs/`,
  update the matching row in the `Subsystem reference` or `MkDocs spine` table of
  [`README.md`](README.md).
- Add a link, never an inline copy, for a new documentation area.
- Every relative link must resolve. From the COGANT project root run:

  ```bash
  uv run python tools/audit_folder_docs.py
  ```

Then confirm the index still reaches the module hubs by building the site from
the package root: `uv run --directory cogant mkdocs build --strict`.
