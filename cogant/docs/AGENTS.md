# AGENTS.md — Docs Master Index

Technical documentation routing index for humans and AI agents.

## Architectural Enforcement

*   **Modular Architecture**: Following a major refactor in April 2026, the 12 large monolithic Markdown files previously occupying this root directory (e.g. `ARCHITECTURE.md` and `SPEC.md`) were decoupled and modularized into corresponding subdirectories (e.g., `architecture/`, `reference/`).
*   **Locating Content**: Agents searching for API guides must drill into `api/`. Agents looking for architectural narratives must drill into `architecture/`. Dated R&D logs and empirical reports live under `evaluation/`.
*   **Modification Pattern**: Do not reconstruct monolithic files. Any new topical tutorials or references must either be integrated directly into their existing module directories as cohesive `.md` fragments, or added to a new module directory.

## MkDocs site root

The published home page is [`index.md`](index.md). Do **not** add a second root `README.md` beside `index.md` under `docs/` — MkDocs treats both as competing home pages and `mkdocs build --strict` will warn or fail. From a nested `docs/<module>/README.md`, point the “hub” link at the site home using the relative path `../index.md` (not `../README.md`).

## Deliberately-shared documentation patterns

Two documentation patterns intentionally diverge from "every folder has its own AGENTS.md + README.md" — agents auditing folder coverage should treat these as features, not gaps:

- **`cogant/docs/` itself has no `README.md`.** [`index.md`](index.md) is the MkDocs home page, and an extra `docs/README.md` would shadow it (see "MkDocs site root" above). A `README.md` here will fail `mkdocs build --strict`.
- **`cogant/evaluation/eval_repos/` ships a single shared [`AGENTS.md`](https://github.com/docxology/cogant/blob/main/cogant/evaluation/eval_repos/AGENTS.md) + [`README.md`](https://github.com/docxology/cogant/blob/main/cogant/evaluation/eval_repos/README.md) at the parent level only.** The 12 entries below it are git submodules pinned to upstream commits (manifest at `/.gitmodules`, one level above this `cogant/` package); their internal contents are **read-only third-party code** and must not receive COGANT-authored AGENTS files. Per-submodule documentation lives upstream.

## Module README indexes

The hub listing all module areas is [`reference/documentation_modules.md`](reference/documentation_modules.md). Each `docs/<module>/README.md` is the table of contents for that module. Link labels should be human-readable titles (for example `Overview`), not pasted heading markers (avoid leading `##` in the link text). If `split_docs.py` is used on a new monolith, empty headings (such as JSON `{` / `}` lines) must not become a filename `.md` or orphan TOC rows; merge those lines into a surrounding section or give them an explicit slug.

## Tooling

*   [`fix_links.py`](fix_links.py) — rewrites legacy monolith filenames to `../<module>/README.md`. `DOCS_DIR` is `Path(__file__).resolve().parent`. If a module folder lacks `AGENTS.md`, the script writes a small generated module note; replace that generated note with a real module index the first time you edit that directory.
*   `split_docs.py` — splits a monolithic guide into section files; empty heading slugs become `_unnamed_section_<n>.md` (never `.md` alone). Lives next to `fix_links.py` in this directory when present in the checkout; it is not part of the MkDocs-published page set.
*   [`verify_doc_links.py`](verify_doc_links.py) — checks relative links from Markdown under `docs/` against the package root (parent of `docs/`). Run after editing cross-links to `py/`, `specs/`, or `examples/` (same directory as `fix_links.py` when checked in).
*   [`verify_manuscript_links.py`](verify_manuscript_links.py) — resolves `manuscript/` as `parent(package_root)/manuscript` (e.g. template: `…/projects/cogant/manuscript` next to inner `cogant/`). **Standalone** clones that only contain the installable package tree with no sibling `manuscript/` will get “directory not found” — expected, not a tool bug. Links beginning with `../../../` are skipped (parent template checkout). Run from the package root: `uv run python docs/verify_manuscript_links.py`.
*   **Manuscript pandoc-crossref audit (template staging)** — when your checkout includes the Research Template tree `projects/cogant/` (active), run `uv run python tools/audit_manuscript_crossrefs.py` from **that staging root** (sibling `tools/` directory) after editing `{#sec:…}` / `@sec:` identifiers so orphan references fail CI locally before PDF builds.
*   **Changelog** — [`changelog.md`](changelog.md) is copied from **`CHANGELOG.md`** at the **package root** (same directory as `py/`, `docs/`, `mkdocs.yml`). After editing the root file: `cp CHANGELOG.md docs/changelog.md`. [`roadmap/changelog.md`](roadmap/changelog.md) is a **stub** for legacy links only (not a second mirror). MkDocs nav exposes a single **Changelog** page (`changelog.md`).
*   **Invoking fix/verify scripts** — from the package root: `uv run python docs/fix_links.py`, `uv run python docs/verify_doc_links.py`. From a monorepo root one level above, if your tree is `…/cogant/` (inner package): `uv run python cogant/docs/fix_links.py` (adjust the prefix to match your checkout).
