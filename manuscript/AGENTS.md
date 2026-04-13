# AGENTS.md — COGANT manuscript

## Purpose

Long-form prose describing COGANT theory and practice in the same structural shape as [`projects/code_project/manuscript/`](../../../projects/code_project/manuscript/). This folder is **not** a substitute for package documentation; it synthesizes narrative for PDF/HTML output via the template rendering stack when the project is active under `projects/`.

## Canonical sources of truth

When the Python API, CLI, export schema, or implementation status changes, update **both**:

1. Package docs under [`../cogant/docs/`](../cogant/docs/): MkDocs home [`../cogant/docs/index.md`](../cogant/docs/index.md), module map [`../cogant/docs/reference/documentation_modules.md`](../cogant/docs/reference/documentation_modules.md), each `docs/<module>/README.md`, and deep pages.
2. The corresponding manuscript fragments (`02_01_*.md`, `06_04_*.md`, `08_02_*.md`, etc.).

Implementation status: [`../cogant/docs/reference/implementation_status.md`](../cogant/docs/reference/implementation_status.md).

When updating quantitative claims, refresh [`../cogant/evaluation/METRICS.yaml`](../cogant/evaluation/METRICS.yaml) (`uv run python ../tools/regenerate_metrics.py` from [`../cogant/`](../cogant/)), then run [`../scripts/z_generate_manuscript_variables.py`](../scripts/z_generate_manuscript_variables.py) from the repo root so `{{PLACEHOLDER}}` tokens in `*.md` resolve consistently. Registry: [`../tools/manuscript_vars.py`](../tools/manuscript_vars.py). After link edits, run [`../cogant/docs/verify_manuscript_links.py`](../cogant/docs/verify_manuscript_links.py) from the package root.

## Files excluded from combined PDF body

Per `infrastructure/rendering/manuscript_discovery.py`, these names are **not** concatenated as sections: `preamble.md`, `AGENTS.md`, `README.md`, `config.yaml`, `config.yaml.example`, `references.bib`.

## Section ordering

- Main narrative: `00_`–`09_` with optional splits `NN_MM_slug.md` (for example `02_01_…`, `06_03_…`) — sorted by **full stem** string order.
- Supplemental appendices: `S01_*.md` … `S06_*.md` (Appendices A–F) after main sections.
- Glossary: `98_*.md` when present.
- Other Markdown (for example `SYNTAX.md`): **other** bucket after supplemental.
- References: `99_*.md` last among Markdown.

Keep numbering aligned with [`../../../infrastructure/rendering/manuscript_discovery.py`](../../../infrastructure/rendering/manuscript_discovery.py).

**Appendix status (as of v{{VERSION}}):**
- S01 (Appendix A — Roundtrip ε): complete
- S02 (Appendix B — Ablation): complete
- S03 (Appendix C — Galois sketch): complete (ε-isomorphism theorem and threshold proposition added)
- S04 (Appendix D — Inference math): complete
- S05 (Appendix E — Extended related work): complete
- S06 (Appendix F — Source references): complete
- `98_notation_supplement.md` (Glossary G — Notation supplement): complete (Groups G.1–G.9: program graph, translation engine, confidence model, A/B/C/D matrices, category theory, equation index, roles/mapping kinds, node/edge enumerations, acronyms)

Do **not** place full duplicate papers in the flat manuscript directory if they are not intended as PDF sections; store archival copies under `_archive/` (subdirectories are not scanned by discovery) or outside `manuscript/`. One-off split scripts that referenced removed monoliths have been removed; do not reintroduce them—edit the numbered fragments directly.

Canonical technical hubs to sync when the implementation changes:

- [`../cogant/docs/index.md`](../cogant/docs/index.md) (published docs entry)
- [`../cogant/docs/reference/documentation_modules.md`](../cogant/docs/reference/documentation_modules.md) (map of `docs/<module>/` areas)
- [`../cogant/docs/reference/implementation_status.md`](../cogant/docs/reference/implementation_status.md)
- [`../cogant/docs/api/README.md`](../cogant/docs/api/README.md)
- [`../cogant/docs/cli/README.md`](../cogant/docs/cli/README.md)
- [`../cogant/docs/export/README.md`](../cogant/docs/export/README.md)
- [`../cogant/docs/plugins/README.md`](../cogant/docs/plugins/README.md)
- [`../cogant/docs/validation/README.md`](../cogant/docs/validation/README.md)
- [`../cogant/docs/architecture/README.md`](../cogant/docs/architecture/README.md)
- [`../cogant/docs/evaluation/README.md`](../cogant/docs/evaluation/README.md) (R&D log, empirical reports)
- [`../cogant/evaluation/README.md`](../cogant/evaluation/README.md) (benchmark corpora, dashboards; not in the wheel)

## Synchronization cadence

Update manuscript fragments **within two weeks** of any public API change, CLI addition,
or rule-set modification. The authoritative check is:

```bash
# From the package root (../cogant/)
uv run python ../tools/audit_manuscript_numbers.py      # catch numeric drift
uv run python docs/verify_manuscript_links.py           # catch broken cross-links
```

**Source of truth on conflicts:** if package docs and manuscript prose disagree,
the package docs are authoritative for API names, types, and behaviour; the manuscript
is authoritative for the narrative framing and pedagogical presentation. When resolving
a conflict, update the manuscript to match the package docs — never the reverse.

**Breaking changes:** when an API is removed or renamed, cite the old form in the
manuscript with a note: "(deprecated since v{{VERSION}}; see `CHANGELOG.md` for the
replacement)". Update the prose to the new form once the new form ships and is tested.

## Citations

Keys live in `references.bib`. Use Pandoc cite syntax documented in [`SYNTAX.md`](SYNTAX.md).

## Figures

If figures are added later, follow the template figure path contract (`output/{project}/figures/` after promotion) and register paths consistent with `infrastructure/rendering` expectations.

## Pipeline caveat

Until this project is promoted under [`../../../projects/`](../../../projects/), discovery-based pipeline scripts will not target it. [`README.md`](README.md) documents manual Markdown validation and post-promotion PDF rendering.
