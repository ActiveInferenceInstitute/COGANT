# AGENTS.md — COGANT Project Root

This is the staging area for the **COGANT (Codebase-to-GNN Translation Engine)** research project before it is officially promoted to the active `projects/` directory.

## Subdirectories

*   [`cogant/`](cogant/AGENTS.md): The implementation layer. Contains the software documentation, Python package, and Rust workspace.
*   [`manuscript/`](manuscript/AGENTS.md): The narrative layer. Contains the markdown manuscript for PDF generation.
*   [`output/`](output/AGENTS.md): The artifact layer. Holds generated outputs from the rendering pipeline.

## Architectural Notes

**Important**: Because this project resides under `projects_in_progress/`, it is **not** automatically discovered by the `infrastructure.project.discovery.discover_projects()` routing logic. The overarching template pipeline actions (such as `run_tests` and `render_pdf`) will not target COGANT until the entire directory is moved to `projects/cogant/`.

When modifying structural parameters or definitions, mandate parity across the `cogant/` software documentation (e.g., `SPEC.md`, `API_GUIDE.md`) and the theoretical `manuscript/` sections.
