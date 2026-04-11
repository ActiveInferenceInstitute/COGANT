# Manuscript Syntax Reference (COGANT)

Formatting conventions for Markdown in this folder. For the full rendering contract, see the template exemplar [`projects/code_project/manuscript/SYNTAX.md`](../../../projects/code_project/manuscript/SYNTAX.md).

## Citations

Use Pandoc cite syntax; keys must exist in `references.bib`.

```markdown
[@allamanis2018survey]

[@allamanis2018survey; @wu2020comprehensive]
```

## Equations

Use LaTeX `equation` with `\label` / `\ref` as documented in the code_project SYNTAX, or pandoc-crossref attributes where the pipeline enables them.

## Figures

If you add figures, place assets where the future project `output/` layout can resolve them (typically `output/figures/` after promotion to `projects/cogant/`). Use explicit relative paths from the rendering contract described in `infrastructure/rendering/AGENTS.md`.

## Section files

[`infrastructure/rendering/manuscript_discovery.py`](../../../infrastructure/rendering/manuscript_discovery.py) concatenates:

1. Digit-prefixed `*.md` files (`00_` … `09_`, including splits such as `02_01_…`, `06_04_…`) in **lexicographic stem order**.
2. Supplemental `S*.md` appendices.
3. `98_*.md` glossary files when present.
4. Other `*.md` files not matching the above (for example `SYNTAX.md`) — the **other** bucket.
5. `99_*.md` references when present.

Excluded from the body: `preamble.md`, `AGENTS.md`, `README.md`, `config.yaml`, `config.yaml.example`, `references.bib`.

## Cross-references to the package

Prefer **relative** paths from this folder to the docs tree: site home [`../cogant/docs/index.md`](../cogant/docs/index.md), module map [`../cogant/docs/reference/documentation_modules.md`](../cogant/docs/reference/documentation_modules.md), and per-module indexes such as [`../cogant/docs/architecture/README.md`](../cogant/docs/architecture/README.md). Do not link a root `docs/README.md` — it is not part of the MkDocs tree (it would duplicate `index.md`).

## See also

- [`AGENTS.md`](AGENTS.md) — editor protocol for this folder
- [`README.md`](README.md) — orientation and render notes
