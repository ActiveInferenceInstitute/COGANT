# Reference

> Canonical, long-form specification of COGANT: schemas, glossary, semantic-role catalogue, translation-rule reference, configuration keys, and implementation status. Reference pages are dense and authoritative; if you want a guided introduction, start in [../tutorials/](../tutorials/README.md) or [../getting-started/](../getting-started/README.md) instead. For task-oriented recipes see [../cookbook/](../cookbook/README.md) and [../cli/](../cli/README.md).

## Contents

### Orientation

| Page | Description | Level |
|------|-------------|-------|
| [Overview](overview.md) | Bird's-eye orientation to the reference section | Beginner |
| [Documentation Modules](documentation_modules.md) | Map of documentation modules to source modules | Reference |
| [Implementation Status](implementation_status.md) | Per-feature implementation status snapshot (authoritative) | Reference |
| [References (bibliography)](references.md) | External references cited in the reference section | Reference |

### Concepts and architecture

| Page | Description | Level |
|------|-------------|-------|
| [Core Concepts](core_concepts.md) | Definitions of the core abstractions | Beginner |
| [Pipeline Stages](pipeline_stages.md) | Default `PipelineRunner` order (`METRICS.yaml` `runner_stages`) vs conceptual IR layers | Intermediate |
| [Data Representations](data_representations.md) | In-memory and on-disk data shapes | Intermediate |
| [Semantic Roles](semantic_roles.md) | The catalogue of Active Inference roles COGANT assigns | Intermediate |
| [Translation Rules](translation_rules.md) | Reference for the translation rule format | Intermediate |
| [Glossary](glossary.md) | Term-by-term glossary of COGANT vocabulary | Beginner |

For the high-level architecture narrative, see [../architecture/overview.md](../architecture/overview.md) — the reference module intentionally does not duplicate it.

### Schemas, configuration, and APIs

| Page | Description | Level |
|------|-------------|-------|
| [Schemas Reference](schemas_reference.md) | Intermediate representations and export schema index | Advanced |
| [Configuration](configuration.md) | Reference for configuration keys and defaults | Intermediate |
| [Calibration Guide](calibration_guide.md) | Methodology and per-threshold sweep registry for resolving `TODO(calibration)` markers in `translate/` and `statespace/` | Advanced |
| [API Overview](api_overview.md) | Compressed Python / CLI API surface reference | Intermediate |
| [Batch Dashboard](batch_dashboard.md) | Cross-target `run_all` sweep dashboard artifacts and API | Intermediate |
| [Examples](examples.md) | Worked examples covering common reference tasks | Beginner |

For the detailed CLI verb reference see [../cli/commands.md](../cli/commands.md) and [../cli/usage_examples.md](../cli/usage_examples.md); for Python API deep-dives see [../api/README.md](../api/README.md). How-to recipes previously fragmented into the reference module now live in [../cookbook/](../cookbook/README.md) and [../getting-started/quickstart.md](../getting-started/quickstart.md).

## Recommended reading order

1. [Overview](overview.md) — establish what the reference covers.
2. [Glossary](glossary.md) — pin down vocabulary before reading the rest.
3. [Core Concepts](core_concepts.md) plus [../architecture/overview.md](../architecture/overview.md) — the conceptual scaffold.
4. [Pipeline Stages](pipeline_stages.md) and [Data Representations](data_representations.md) — what the pipeline does and what flows between stages.
5. [Semantic Roles](semantic_roles.md) and [Translation Rules](translation_rules.md) — the central knobs you tune.
6. [Configuration](configuration.md), [API Overview](api_overview.md), and [Batch Dashboard](batch_dashboard.md) — how to drive COGANT in practice.
7. [Schemas Reference](schemas_reference.md) — the wire-level contract.
8. [Implementation Status](implementation_status.md) — what is actually wired up today.

Agent notes: [AGENTS.md](AGENTS.md) · Hub: [../index.md](../index.md)
