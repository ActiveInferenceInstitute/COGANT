# AGENTS.md — PDF Output

This directory is an automated output sink. 

## Ephemerality

*   **Do not manually store assets here**: PDF files and LaTeX intermediate logs (e.g., `.aux`, `.log`, `.toc`) are transient and will be purged by the `clean_output_directories` stage upon the next rebuild.
*   The actual narrative source is in `manuscript/`.
