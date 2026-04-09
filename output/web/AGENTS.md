# AGENTS.md — Web Output

This directory is an automated output sink for HTML generation.

## Constraints

*   **No Source Tracking**: HTML files inside this folder are solely the result of post-processing.
*   **Wiping**: `clean_output_directories` removes these objects on every full run to ensure no stale content persists. Do not commit manually stylized HTML objects into this path.
