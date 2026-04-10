# AGENTS.md — Docs Master Index

Technical documentation routing index for humans and AI agents.

## Architectural Enforcement

*   **Modular Architecture**: Following a major refactor in April 2026, the 12 large monolithic Markdown files previously occupying this root directory (e.g. `ARCHITECTURE.md` and `SPEC.md`) were decoupled and modularized into corresponding subdirectories (e.g., `architecture/`, `reference/`).
*   **Locating Content**: Agents searching for API guides must drill into `api/`. Agents looking for architectural narratives must drill into `architecture/`. Dated R&D logs and empirical reports live under `evaluation/`. 
*   **Modification Pattern**: Do not reconstruct monolithic files. Any new topical tutorials or references must either be integrated directly into their existing module directories as cohesive `.md` fragments, or added to a new module directory.

## MkDocs site root

The published home page is [`index.md`](index.md). Do **not** add a second root `README.md` beside `index.md` under `docs/` — MkDocs treats both as competing home pages and `mkdocs build --strict` will warn or fail. From a nested `docs/<module>/README.md`, point the “hub” link at the site home using the relative path `../index.md` (not `../README.md`).

## Module README indexes

The hub listing all module areas is [`reference/documentation_modules.md`](reference/documentation_modules.md). Each `docs/<module>/README.md` is the table of contents for that module. Link labels should be human-readable titles (for example `Overview`), not pasted heading markers (avoid leading `##` in the link text). If `split_docs.py` is used on a new monolith, empty headings (such as JSON `{` / `}` lines) must not become a filename `.md` or orphan TOC rows; merge those lines into a surrounding section or give them an explicit slug.

## Tooling

*   [`fix_links.py`](fix_links.py) — rewrites legacy monolith filenames to `../<module>/README.md`. `DOCS_DIR` is `Path(__file__).resolve().parent`.
*   `split_docs.py` — splits a monolithic guide into section files; empty heading slugs become `_unnamed_section_<n>.md` (never `.md` alone). Lives next to `fix_links.py` in this directory when present in the checkout; it is not part of the MkDocs-published page set.
*   `verify_doc_links.py` — checks relative links from Markdown under `docs/` against the package root (parent of `docs/`). Run after editing cross-links to `py/`, `specs/`, or `examples/` (same directory as `fix_links.py` when checked in).
*   **Changelog** — [`changelog.md`](changelog.md) mirrors the root `CHANGELOG.md` for MkDocs. Edit **`CHANGELOG.md`** at the repository root, then `cp CHANGELOG.md docs/changelog.md`. The **Changelog** section in root **`CONTRIBUTING.md`** describes the workflow.
