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

The gate's `docs` arm runs the build that CI deploys, plus the relative-link
check:

```bash
python run_gate.py docs        # from the COGANT project root
```

Equivalently, from the package root: `uv run mkdocs build --strict` followed by
`uv run python docs/verify_doc_links.py`. The strict build tolerates the
documentation-only `AGENTS.md` pages and the generated changelog that are
outside the MkDocs `nav`; it fails on a broken internal link or unknown page
anchor.

## GitHub Pages deployment

On pushes to `main`, after a successful `CI` workflow, or through manual dispatch,
`.github/workflows/docs.yml` runs `python ../run_gate.py --prepare docs` (one
`uv sync`, then the strict build and link check) and deploys `site/` with
`peaceiris/actions-gh-pages` pinned at v4.1.0 (a
Node 24 release, so no runtime override is needed). The job uses
`actions/checkout` pinned at v7.0.1, `actions/setup-python` pinned at v7.1.0, and
`astral-sh/setup-uv` pinned at v10.3.3; every action reference in this
repository's workflows is a full commit SHA.
The workflow defaults to `contents: read`; only the deploy job grants
`contents: write`, because the action publishes the generated site to the
`gh-pages` branch. Deploys are serialized with a job-level
`concurrency: docs-deploy` group so overlapping `push` and post-CI
`workflow_run` runs never race each other.

For the exact triggers, paths, permissions, and deployment settings, treat the
workflow file as authoritative rather than copying an independent workflow snippet.
