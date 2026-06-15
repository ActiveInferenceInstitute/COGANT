# tools/figures/

Internal helpers for promoting real run outputs into publication figures with
evidence-bearing metadata. These modules back [`../manuscript_figures.py`](../manuscript_figures.py),
which copies curated PNGs from `cogant/output/` into `output/figures/` and writes
`manifest.json` plus per-figure `.figure.json` sidecars consumed by the manuscript
renderer and the strict figure-QA gate.

| Module | Responsibility |
| --- | --- |
| `copier.py` | Copy registered figures and write manifest / sidecar metadata. |
| `renderers.py` | Publication figure renderers and source-artifact preparation. |
| `png.py` | Dependency-light PNG inspection for strict figure QA (nonblank, color diversity, dimensions). |
| `metadata.py` | Figure metadata, sidecar, and strict-publication validation. |
| `common.py` | Small data-conversion helpers. |
| `constants.py` | Shared constants for figure promotion. |

These are an implementation detail of the manuscript pipeline, not a public API.
Run the figure pipeline from the project root with
`uv run python tools/manuscript_figures.py --strict` (fails on any missing or
under-documented publication figure).
