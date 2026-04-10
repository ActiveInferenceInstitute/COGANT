# AGENTS.md — Evaluation module

Long-form R&D notes, empirical reports, and dated gate logs. Companion machine artifacts
(datasets, eval repo mirrors, dashboards) live in the **`evaluation/`** directory at the
repository root (outside this `docs/` tree; see package `evaluation/README.md` on disk).

## Maintenance

- Keep filenames stable when other docs and code cite them (`docs/evaluation/<name>.md`).
- Cross-link to theory and API modules with relative paths (`../theory/`, `../api/`).
- After moving or renaming files, run `python docs/verify_doc_links.py` from the package root.
