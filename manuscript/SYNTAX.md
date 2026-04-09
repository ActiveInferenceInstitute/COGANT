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

Numeric prefixes `00_`–`08_` are combined in stem-sorted order by `infrastructure/rendering/manuscript_discovery.py`. Files named `SYNTAX.md` sort in the **other** bucket (after main/supplemental sections and before `99_*` if present).

## Cross-references to the package

Prefer **relative** paths from this folder to the package tree, e.g. [`../cogant/docs/ARCHITECTURE.md`](../cogant/docs/ARCHITECTURE.md), so links work in the editor and in Git without hard-coding the monorepo path.

## See also

- [`AGENTS.md`](AGENTS.md) — editor protocol for this folder
- [`README.md`](README.md) — orientation and render notes
