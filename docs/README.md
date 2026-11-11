# COGANT documentation index

> **What this page is:** the repository-level map of COGANT's documentation. The
> canonical technical documentation is the MkDocs site under [`cogant/docs/`](../cogant/docs/index.md);
> this index points into that tree and into the repository-level documents so nothing
> is duplicated.

COGANT keeps its documentation **with the installable package** at
[`cogant/docs/`](../cogant/docs/index.md), published as an MkDocs site. The
repository also carries project-level documents at the root (`README.md`,
`AGENTS.md`, `DESIGN.md`, `ISA.md`, `PROMOTION.md`, `TODO.md`) and the manuscript
sources under [`manuscript/`](../manuscript/README.md). Use this page as the
single entry point to all of them.

## Start here

| I want to… | Read |
| --- | --- |
| Understand what COGANT is | [`cogant/docs/index.md`](../cogant/docs/index.md) · root [`README.md`](../README.md) |
| Install and run the first translation | [`cogant/docs/getting-started/README.md`](../cogant/docs/getting-started/README.md) |
| Follow a guided lesson | [`cogant/docs/tutorials/README.md`](../cogant/docs/tutorials/README.md) |
| Look up a command or flag | [`cogant/docs/cli_reference.md`](../cogant/docs/cli_reference.md) · [`cogant/docs/cli/README.md`](../cogant/docs/cli/README.md) |
| Answer a common question | [`cogant/docs/faq.md`](../cogant/docs/faq.md) |
| Contribute code or docs | [`cogant/CONTRIBUTING.md`](../cogant/CONTRIBUTING.md) · [`cogant/docs/AGENTS.md`](../cogant/docs/AGENTS.md) |

## Documentation modules

The module hub is [`cogant/docs/reference/documentation_modules.md`](../cogant/docs/reference/documentation_modules.md);
each area below is the table of contents for that module.

### Subsystem reference

| Module | Index |
| --- | --- |
| API (sessions, pipeline runner, finite models) | [`cogant/docs/api/README.md`](../cogant/docs/api/README.md) |
| Architecture (layers, pipeline, graph engine) | [`cogant/docs/architecture/README.md`](../cogant/docs/architecture/README.md) |
| CLI | [`cogant/docs/cli/README.md`](../cogant/docs/cli/README.md) |
| Evaluation (R&D log, empirical reports, calibration) | [`cogant/docs/evaluation/README.md`](../cogant/docs/evaluation/README.md) |
| Export (output formats, PyG/DGL interop) | [`cogant/docs/export/README.md`](../cogant/docs/export/README.md) |
| Plugins (extension points, languages, exporters) | [`cogant/docs/plugins/README.md`](../cogant/docs/plugins/README.md) |
| Reference (status, pipeline stages, schemas) | [`cogant/docs/reference/README.md`](../cogant/docs/reference/README.md) |
| Roadmap (releases, backlog, changelog) | [`cogant/docs/roadmap/README.md`](../cogant/docs/roadmap/README.md) |
| Rules (translation-rule framework, mappings) | [`cogant/docs/rules/README.md`](../cogant/docs/rules/README.md) |
| Security (threat model, sandboxing, audits) | [`cogant/docs/security/README.md`](../cogant/docs/security/README.md) |
| Validation (data integrity, validation layers) | [`cogant/docs/validation/README.md`](../cogant/docs/validation/README.md) |

### MkDocs spine (onboarding, tutorials, theory)

| Section | Index |
| --- | --- |
| Getting started | [`cogant/docs/getting-started/README.md`](../cogant/docs/getting-started/README.md) |
| Learning paths | [`cogant/docs/learning-paths/README.md`](../cogant/docs/learning-paths/README.md) |
| Guides | [`cogant/docs/guides/README.md`](../cogant/docs/guides/README.md) |
| Concepts | [`cogant/docs/concepts/README.md`](../cogant/docs/concepts/README.md) |
| Tutorials | [`cogant/docs/tutorials/README.md`](../cogant/docs/tutorials/README.md) |
| Cookbook | [`cogant/docs/cookbook/README.md`](../cogant/docs/cookbook/README.md) |
| Theory (GNN format, roundtrip invariants) | [`cogant/docs/theory/README.md`](../cogant/docs/theory/README.md) |
| Notebooks | [`cogant/docs/notebooks/README.md`](../cogant/docs/notebooks/README.md) |
| R&D notes | [`cogant/docs/rnd/README.md`](../cogant/docs/rnd/README.md) |
| FAQ | [`cogant/docs/faq.md`](../cogant/docs/faq.md) |
| Changelog (synced from `cogant/CHANGELOG.md`) | [`cogant/docs/changelog.md`](../cogant/docs/changelog.md) |
| Docs deployment | [`cogant/docs/CI.md`](../cogant/docs/CI.md) |
| Playground | [`cogant/docs/playground.md`](../cogant/docs/playground.md) |

## Repository-level documents

| Document | Purpose |
| --- | --- |
| [`README.md`](../README.md) | Project overview, batch runner, tests, eval submodules. |
| [`AGENTS.md`](../AGENTS.md) | Agent guidance for the project root (layout, commands, manuscript pipeline). |
| [`cogant/AGENTS.md`](../cogant/AGENTS.md) | Agent guidance for the package root. |
| [`DESIGN.md`](../DESIGN.md) | Design rationale. |
| [`ISA.md`](../ISA.md) | Information-system architecture note. |
| [`PROMOTION.md`](../PROMOTION.md) | Checklist for rendering under the parent template. |
| [`TODO.md`](../TODO.md) | Owner-facing execution backlog. |
| [`CITATION.cff`](../CITATION.cff) | Machine-readable citation metadata. |
| [`manuscript/README.md`](../manuscript/README.md) | Manuscript section index and validation commands. |
| [`cogant/README.md`](../cogant/README.md) | Package overview. |
| [`cogant/CONTRIBUTING.md`](../cogant/CONTRIBUTING.md) | Contribution guidelines and development setup. |
| [`cogant/CHANGELOG.md`](../cogant/CHANGELOG.md) | Release history (source of truth for `cogant/docs/changelog.md`). |
| [`.github/README.md`](../.github/README.md) | CI, workflows, and repository automation. |
| [`.aii/README.md`](../.aii/README.md) | InstituteOS sidecar metadata (federation only). |

Related machine-readable trees outside the docs site:
[`cogant/specs/README.md`](../cogant/specs/README.md) (schemas, IR contracts) and
[`cogant/examples/README.md`](../cogant/examples/README.md) (runnable fixtures).

## How the docs are built

- **Site source:** [`cogant/docs/`](../cogant/docs/index.md); site root
  [`cogant/docs/index.md`](../cogant/docs/index.md) (there is deliberately no
  `cogant/docs/README.md`, which would shadow the MkDocs home page).
- **MkDocs config:** [`cogant/mkdocs.yml`](../cogant/mkdocs.yml). Build the site
  from the package root: `uv run --directory cogant mkdocs build --strict`
  (equivalently `make docs` inside `cogant/`).
- **Link checkers:** [`cogant/docs/verify_doc_links.py`](../cogant/docs/verify_doc_links.py)
  (relative links from the docs tree) and
  [`cogant/docs/verify_manuscript_links.py`](../cogant/docs/verify_manuscript_links.py)
  (manuscript links; needs a sibling `manuscript/`, expected to report "directory
  not found" in a package-only checkout).
- **Conventions for authors and agents:** [`cogant/docs/AGENTS.md`](../cogant/docs/AGENTS.md)
  (one topic per file; extend a module directory instead of recreating monoliths).
