# Reference

> Canonical, long-form specification of COGANT: schemas, glossary, semantic-role catalogue, translation-rule reference, configuration keys, and the file/module inventory. Reference pages are dense and authoritative; if you want a guided introduction, start in [../tutorials/](../tutorials/) or [../getting-started/](../getting-started/) instead.

## Contents

### Orientation

| Page | Description | Level |
|------|-------------|-------|
| [Overview](overview.md) | Bird's-eye orientation to the reference section | Beginner |
| [Table of Contents](table_of_contents.md) | Detailed table of contents for the reference set | Reference |
| [Documentation Modules](documentation_modules.md) | Map of documentation modules to source modules | Reference |
| [Introduction](introduction.md) | Introductory framing for first-time readers | Beginner |
| [Implementation Status](implementation_status.md) | Per-feature implementation status snapshot | Reference |
| [Next Steps](next_steps.md) | Suggested follow-on reading after the reference | Beginner |
| [References](references.md) | External references cited in the reference section | Reference |

### Concepts and architecture

| Page | Description | Level |
|------|-------------|-------|
| [Core Concepts](core_concepts.md) | Definitions of the core abstractions | Beginner |
| [Architecture Overview](architecture_overview.md) | High-level architecture summary | Intermediate |
| [Pipeline Stages](pipeline_stages.md) | Canonical stage list and contracts | Intermediate |
| [Data Representations](data_representations.md) | In-memory and on-disk data shapes | Intermediate |
| [Semantic Roles](semantic_roles.md) | The catalogue of Active Inference roles COGANT assigns | Intermediate |
| [Translation Rules](translation_rules.md) | Reference for the translation rule format | Intermediate |
| [Glossary](glossary.md) | Term-by-term glossary of COGANT vocabulary | Beginner |

### Schemas and data

| Page | Description | Level |
|------|-------------|-------|
| [Schemas Reference](schemas_reference.md) | Top-level schemas reference | Intermediate |
| [COGANT Schemas Reference](cogant_schemas_reference.md) | Detailed COGANT-specific schemas | Advanced |
| [File and Module Inventory](file_and_module_inventory.md) | Inventory of files and modules in the package | Reference |

### Configuration and CLI

| Page | Description | Level |
|------|-------------|-------|
| [Configuration](configuration.md) | Reference for configuration keys and defaults | Intermediate |
| [Installation](installation.md) | Reference installation procedure | Beginner |
| [CLI Usage](cli_usage.md) | Reference of CLI verbs and flags | Beginner |
| [Python API Usage](python_api_usage.md) | Reference of the Python API surface | Intermediate |
| [API Overview](api_overview.md) | Compressed API surface reference | Intermediate |
| [Examples](examples.md) | Worked examples covering common reference tasks | Beginner |

### Operational recipes

| Page | Description | Level |
|------|-------------|-------|
| [Initialize a Project](initialize_a_project.md) | Project initialization steps | Beginner |
| [Install Dependencies](install_dependencies.md) | Install runtime dependencies | Beginner |
| [Install Package in Development Mode](install_package_in_development_mode.md) | Editable install for contributors | Intermediate |
| [Navigate to Python Package Directory](navigate_to_python_package_directory.md) | Repository layout convention | Beginner |
| [Scan a Repository](scan_a_repository.md) | Run a scan from the reference perspective | Beginner |
| [Run Full Analysis](run_full_analysis.md) | Run the full analysis pipeline | Intermediate |
| [Render Site](render_site.md) | Render the static documentation site | Intermediate |
| [Render Interactive HTML Site](render_interactive_html_site.md) | Render the interactive site | Intermediate |
| [Validate Results](validate_results.md) | Run validators against a result bundle | Intermediate |
| [Compare Two Analyses](compare_two_analyses.md) | Diff two analyses | Intermediate |
| [Method 1: Simple Session](method_1_simple_session.md) | Simple `Session`-based usage pattern | Beginner |
| [Method 2: Orchestrated Pipeline](method_2_orchestrated_pipeline.md) | Orchestrated `PipelineRunner` pattern | Intermediate |
| [Access Results](access_results.md) | Reading and traversing result bundles | Intermediate |

### Implementation snapshots

| Page | Description | Level |
|------|-------------|-------|
| [Project Setup and Component Inventory](project_setup_and_component_inventory.md) | Snapshot of project setup and components | Reference |
| [COGANT Implementation: Complete Project Setup](cogant_implementation_complete_project_setup.md) | Reference snapshot of the implementation setup | Reference |
| [COGANT Implementation Summary](cogant_implementation_summary.md) | Summary of the implementation effort | Reference |
| [COGANT Ingest and Static Analysis Pipeline: Implementation Summary](cogant_ingest_and_static_analysis_pipeline_implementation_summary.md) | Implementation summary for ingest + static pipeline | Reference |
| [Ingest and Static Pipeline Milestone](ingest_and_static_pipeline_milestone.md) | Milestone notes | Reference |

## Recommended Reading Order

1. [Overview](overview.md) — establish what the reference covers.
2. [Glossary](glossary.md) — pin down vocabulary before reading the rest.
3. [Core Concepts](core_concepts.md) and [Architecture Overview](architecture_overview.md) — the conceptual scaffold.
4. [Pipeline Stages](pipeline_stages.md) and [Data Representations](data_representations.md) — what the pipeline does and what flows between stages.
5. [Semantic Roles](semantic_roles.md) and [Translation Rules](translation_rules.md) — the central knobs you tune.
6. [Configuration](configuration.md), [CLI Usage](cli_usage.md), [Python API Usage](python_api_usage.md) — how to drive COGANT in practice.
7. [Schemas Reference](schemas_reference.md) and [COGANT Schemas Reference](cogant_schemas_reference.md) — the wire-level contract.
8. The operational recipes table on demand, when you need to perform a specific task.

Agent notes: [AGENTS.md](AGENTS.md) - Hub: [../index.md](../index.md)
