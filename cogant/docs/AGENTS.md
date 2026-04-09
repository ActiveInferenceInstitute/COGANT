# AGENTS.md — Docs Master Index

Technical documentation routing index for humans and AI agents.

## Architectural Enforcement

*   **Modular Architecture**: Following a major refactor in April 2026, the 12 large monolithic Markdown files previously occupying this root directory (e.g. `ARCHITECTURE.md` and `SPEC.md`) were decoupled and modularized into corresponding subdirectories (e.g., `architecture/`, `reference/`).
*   **Locating Content**: Agents searching for API guides must drill into `api/`. Agents looking for architectural narratives must drill into `architecture/`. 
*   **Modification Pattern**: Do not reconstruct monolithic files. Any new topical tutorials or references must either be integrated directly into their existing module directories as cohesive `.md` fragments, or added to a new module directory.
