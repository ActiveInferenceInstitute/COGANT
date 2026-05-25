# Deploying the Documentation Site

COGANT uses [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) for documentation.

**Repository layout:** `mkdocs.yml` lives next to `docs/` at the **COGANT package root** (the directory you `cd` into for `uv sync` and `pytest`). This tree includes the workflow file `.github/workflows/docs.yml` at that same root. If you embed COGANT inside a monorepo, set `defaults.run.working-directory` (or per-step `working-directory`) to the subdirectory that contains `mkdocs.yml`, and point `upload-pages-artifact` at `<that-subdir>/site`.

## Local Development

```bash
uv run --with mkdocs-material --with 'mkdocstrings[python]' mkdocs serve
```

Open <http://127.0.0.1:8000> in your browser.

## Building Locally

```bash
uv run --with mkdocs-material --with 'mkdocstrings[python]' mkdocs build --strict
```

The static site is written to `site/` (git-ignored).

Strict builds are the release gate; use the non-strict command only while editing a page interactively.

## GitHub Pages deployment

The workflow at `.github/workflows/docs.yml` runs `mkdocs build` from the repository root when that root **is** the package root. It uses **uv**; see [Building Locally](#building-locally). Enable **GitHub Pages** (source: GitHub Actions) and a `github-pages` environment if your org requires it.

Minimal equivalent:

```yaml
name: Deploy docs
on:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv run --with mkdocs-material --with 'mkdocstrings[python]' mkdocs build --strict
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site
      - uses: actions/deploy-pages@v4
```
