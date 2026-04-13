# Deploying the Documentation Site

COGANT uses [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) for documentation.

## Local Development

```bash
uv run --with mkdocs-material --with 'mkdocstrings[python]' mkdocs serve
```

Open <http://127.0.0.1:8000> in your browser.

## Building Locally

```bash
uv run --with mkdocs-material --with 'mkdocstrings[python]' mkdocs build
```

The static site is written to `site/` (git-ignored).

`mkdocs build --strict` currently fails on legacy anchor and cross-reference warnings across split docs; use the non-strict command above unless you are fixing those warnings deliberately.

## GitHub Pages deployment

Example workflow at `.github/workflows/docs.yml` (repository root). Uses **uv** to match local development; drop `--strict` until anchor warnings are cleared project-wide (see [Building Locally](#building-locally)).

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
      - name: Build site
        working-directory: cogant
        run: uv run --with mkdocs-material --with 'mkdocstrings[python]' mkdocs build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: cogant/site
      - uses: actions/deploy-pages@v4
```

Set **working-directory** to the directory that contains `mkdocs.yml` (here `cogant/`). Enable GitHub Pages (Source: GitHub Actions) in repository settings.
