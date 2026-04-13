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

## Specs and Examples

Machine-readable schemas, ontological mappings, and formal specifications live under the repository root `specs/` directory (start at `specs/README.md`). Working Python integrations live under the repository root `examples/` directory (start at `examples/README.md`). Those trees are not part of the MkDocs site; open them in the repository checkout or editor.
