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

## GitHub Pages Deployment

Add this workflow at `.github/workflows/docs.yml` in the repository root:

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
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install mkdocs-material 'mkdocstrings[python]'
      - run: mkdocs build --strict
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site
      - uses: actions/deploy-pages@v4
```

Then enable GitHub Pages in the repository settings (Source: GitHub Actions).
