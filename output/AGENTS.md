# AGENTS.md — Output Directory

This directory acts as the transient and final sink for compiled documents and figures in the COGANT rendering lifecycle.

## Expected Behavior

*   **Volatility**: The rendering pipeline inherently treats `output/` subdirectories as expendable prior to generation. Automated `clean_output_directories` routines in the build infrastructure will wipe PDF, HTML, and log artifacts within this space.
*   **Source of Truth**: Never store canonical source assets (e.g., manually drafted images, original SVGs, or hand-written configuration) in this folder. All inputs strictly belong in `cogant/`, `manuscript/`, or explicit `src/` domains.
*   **Staging Status**: While the project is in `projects_in_progress/`, it will not receive outputs from `run.sh` or `scripts/03_render_pdf.py`. The generation sequence connects only once promoted to the `projects/cogant/` active hierarchy.
