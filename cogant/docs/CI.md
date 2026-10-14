# Deploying the Documentation Site

COGANT uses [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) for documentation.

The package root is the directory containing `mkdocs.yml`, `docs/`, and `pyproject.toml`.
Run the commands below from that directory. The checked-in deployment workflow is
`.github/workflows/docs.yml` at the repository root.

## Local development

Install the development dependencies, then serve the site:

```bash
uv sync --extra dev
uv run mkdocs serve
```

Open <http://127.0.0.1:8000> in a browser. The generated site is written to the
git-ignored `site/` directory.

## Building locally

```bash
uv run mkdocs build
```

The repository workflow currently uses this non-strict build because the published
site includes documentation-only `AGENTS.md` pages and a generated changelog whose
source is outside the MkDocs docs directory. Run the package's relative-link and
anchor checker separately when editing documentation:

```bash
uv run python docs/verify_doc_links.py
```

## GitHub Pages deployment

On pushes to `main`, after a successful `CI` workflow, or through manual dispatch,
`.github/workflows/docs.yml` installs the dev dependencies, runs `uv run mkdocs build`,
and deploys `site/` with `peaceiris/actions-gh-pages@v4` (which resolves to a
Node 24 release, so no runtime override is needed). The job uses
`actions/checkout@v7`, `actions/setup-python@v7`, and `astral-sh/setup-uv@v10.3.0`.
The workflow defaults to `contents: read`; only the deploy job grants
`contents: write`, because the action publishes the generated site to the
`gh-pages` branch. Deploys are serialized with a job-level
`concurrency: docs-deploy` group so overlapping `push` and post-CI
`workflow_run` runs never race each other.

For the exact triggers, paths, permissions, and deployment settings, treat the
workflow file as authoritative rather than copying an independent workflow snippet.
