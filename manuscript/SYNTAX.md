# Manuscript Syntax Reference (COGANT)

Formatting conventions for Markdown in this folder. For the full rendering contract when linked into `docxology/template/projects/working/cogant/`, use the parent template renderer docs under `infrastructure/rendering/`.

## Citations

Use Pandoc cite syntax; keys must exist in `references.bib`.

```markdown
[@allamanis2018survey]

[@allamanis2018survey; @wu2020comprehensive]
```

## Cross-references (pandoc-crossref)

Combined HTML and PDF/LaTeX are built with Pandoc. When **`pandoc-crossref`** is on `PATH`, the template renderers add `--filter pandoc-crossref` so native syntax resolves to numbered references before citation processing or final output.

**Install:** e.g. `brew install pandoc-crossref` (macOS). Without the filter, the build still runs; `@sec:` / `@tbl:` / `@fig:` tokens remain literal until the filter is available.

**Section labels:** on headings that you cite elsewhere, use stable ids derived from the file stem, hyphenated:

```markdown
## Formal definitions {#sec:02-01-formal-definitions}
```

Reference in prose: `… see @sec:02-01-formal-definitions …`

**Tables:** put the caption line **after** the pipe table:

```markdown
| a | b |
|---|---|
| 1 | 2 |

: Short caption text. {#tbl:example-id}
```

Reference: `@tbl:example-id`. In body text, cite tables only with `@tbl:…` (and sections with `@sec:…`); do not hard-code "Table 4" or "Tables 4–7" so numbering stays automatic when the build order changes.

## Equations

Use pandoc-crossref display equations only:

```markdown
$$
y = mx + b
$$ {#eq:example-line}
```

Reference equations in prose with `@eq:example-line`. Do not use LaTeX `\label`, `\ref`, `Equation \ref{...}`, or `Eq. \ref{...}` in manuscript source.

## Figures

Follow the parent template rendering contract for image markdown plus `{#fig:…}` when you add figures. COGANT's publication figures are copied into `../output/figures/` by `../tools/manuscript_figures.py`; source manuscript paths should therefore reference them as `../figures/<name>.png` so generated files in `output/manuscript/` resolve correctly. When vendored into the parent template, use explicit relative paths from the rendering contract described in `infrastructure/rendering/AGENTS.md`.

## Section files

[`infrastructure/rendering/manuscript_discovery.py`](https://github.com/docxology/template/blob/main/infrastructure/rendering/manuscript_discovery.py) concatenates:

1. Digit-prefixed `*.md` files (`00_` … `09_`, including splits such as `02_01_…`, `06_04_…`) in **lexicographic stem order**.
2. Supplemental `S*.md` appendices.
3. `98_*.md` glossary files when present.
4. Other `*.md` files not matching the above (for example `SYNTAX.md`) — the **other** bucket.
5. `99_*.md` references when present.

Excluded from the body by the parent template renderer: `preamble.md`, `AGENTS.md`, `README.md`, `config.yaml`, `references.bib`. `SYNTAX.md` and `supplementary.md` are not excluded by name in every renderer version, so example labels in this file must remain safe under the cross-reference audit or the renderer skip list must exclude this file before publication.

## PDF links (readers and contrast)

The combined PDF uses coloured links (`preamble.md`): **internal and citation** links are red; **URL** links are blue so URL and in-text references are not distinguished by colour alone. The template may rewrite `hidelinks` drafts to red links in `infrastructure/rendering/_pdf_combined_renderer.py`; keep this manuscript’s explicit `urlcolor`/`linkcolor` split if you add `\usepackage[...]{hyperref}` in `preamble.md`. For figures, add a sentence of plain-language description in prose (not only the caption) so the takeaway is clear without the visual.

## Cross-references to the package

Prefer **relative** paths from this folder to the docs tree: site home [`../cogant/docs/index.md`](../cogant/docs/index.md), module map [`../cogant/docs/reference/documentation_modules.md`](../cogant/docs/reference/documentation_modules.md), and per-module indexes such as [`../cogant/docs/architecture/README.md`](../cogant/docs/architecture/README.md). Do not link a root `docs/README.md` — it is not part of the MkDocs tree (it would duplicate `index.md`).

## See also

- [`AGENTS.md`](AGENTS.md) — editor protocol for this folder
- [`README.md`](README.md) — orientation and render notes
