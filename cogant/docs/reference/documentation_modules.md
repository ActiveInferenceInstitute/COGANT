# COGANT Documentation

This directory contains the modular technical documentation for the Codebase-to-GNN (COGANT) translation engine.

## Documentation Modules

| Module | Description | Location |
|--------|-------------|----------|
| **API** | Python API references, Session, PipelineRunner, Bundle interfaces | [`api/`](../api/README.md) |
| **Architecture** | System layers, pipeline guide, graph engine deep-dives | [`architecture/`](../architecture/README.md) |
| **CLI** | `cogant` command-line reference and usage examples | [`cli/`](../cli/README.md) |
| **Evaluation** | R&D log, empirical reports, calibration notes | [`evaluation/`](../evaluation/README.md) |
| **Export** | Outputs, PyG/DGL interop, tensor payloads | [`export/`](../export/README.md) |
| **Plugins** | Extension points, languages, and custom exporters | [`plugins/`](../plugins/README.md) |
| **Reference** | Implementation status, [`pipeline_stages.md`](pipeline_stages.md) (runner order), schema references | [`reference/`](README.md) |
| **Roadmap** | Releases, backlog, and changelog | [`roadmap/`](../roadmap/README.md) |
| **Rules** | Translation rules framework and mapping definitions | [`rules/`](../rules/README.md) |
| **Security** | Threat modeling, sandboxing, package audits | [`security/`](../security/README.md) |
| **Validation** | Data integrity checks, validation layers | [`validation/`](../validation/README.md) |

## MkDocs spine (onboarding, tutorials, theory)

These areas match the [`mkdocs.yml`](../../mkdocs.yml) navigation: deep dives and learning paths live here; the table above indexes **subsystem** docs (API, architecture, export, …).

| Section | Role | Index |
|--------|------|--------|
| **Home** | Site entry, project pitch | [`index.md`](../index.md) |
| **Getting started** | Install + first run | [`getting-started/README.md`](../getting-started/README.md) |
| **Learning paths** | Role-based reading orders | [`learning-paths/README.md`](../learning-paths/README.md) |
| **Guides** | End-to-end project guide | [`guides/README.md`](../guides/README.md) |
| **Concepts** | GNN, Active Inference, roles, graphs | [`concepts/README.md`](../concepts/README.md) |
| **Tutorials** | Step-by-step lessons + walkthroughs | [`tutorials/README.md`](../tutorials/README.md) |
| **Cookbook** | Task-focused recipes | [`cookbook/README.md`](../cookbook/README.md) |
| **CLI reference** | Single-page command/flag reference | [`cli_reference.md`](../cli_reference.md) |
| **Theory** | GNN format, isomorphism, primers | [`theory/README.md`](../theory/README.md) |
| **Notebooks** | Jupyter narrative companions | [`notebooks/README.md`](../notebooks/README.md) |
| **R&D** | Calibration and mapping notes | [`rnd/README.md`](../rnd/README.md) |
| **FAQ** | Q&A | [`faq.md`](../faq.md) |
| **Changelog** | Release history (synced from root `CHANGELOG.md`) | [`changelog.md`](../changelog.md) |
| **Deployment** | Docs site build / Pages | [`CI.md`](../CI.md) |
| **Playground** | Local HTML experiment surface | [`playground.md`](../playground.md) |

## Specs and Examples

Machine-readable schemas, ontological mappings, and formal specifications live under the repository root `specs/` directory (start at `specs/README.md`). Working Python integrations live under the repository root `examples/` directory (start at `examples/README.md`). Those trees are not part of the MkDocs site; open them in the repository checkout or editor.
