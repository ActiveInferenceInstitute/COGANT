# PDF Output Directory

This directory contains the finalized PDF manuscript (`cogant_combined.pdf`) generated from the `manuscript/` Markdown sources.

## Rendering Pipeline

During `scripts/03_render_pdf.py` execution, the `infrastructure/rendering/` cluster aggregates `_combined_manuscript.md`, passes it to Pandoc/XeLaTeX, and populates this folder.
