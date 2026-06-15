# AGENTS.md - tools/figures/

Helper package for `tools/manuscript_figures.py`. It promotes real run PNGs into
`output/figures/` and records evidence metadata (source artifact, renderer, hashes,
dimensions, QA fields) in `manifest.json` and per-figure sidecars.

Do not fabricate or hand-edit figure metadata to satisfy a manuscript claim.
Figures and their sidecars must be regenerated from real `cogant/output/` artifacts;
the strict gate (`manuscript_figures.py --strict`) rejects missing figures, degraded
vector conversion, and under-documented sidecars. Keep these modules dependency-light
(standard library plus the project's existing figure dependencies) so the QA gate runs
without optional extras.
