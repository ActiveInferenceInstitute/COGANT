# API Reference

> Public Python API surface for COGANT. Use this section if you are embedding COGANT in another tool, scripting custom pipelines, or building plugins. For CLI usage see [../cli_reference.md](../cli_reference.md); for narrative tutorials see [../tutorials/](../tutorials/README.md).

## Contents

### Orientation

| Page | Description | Level |
|------|-------------|-------|
| [Overview](overview.md) | Bird's-eye map of the public API surface | Beginner |
| [Installation](installation.md) | Install the package and verify the import works | Beginner |
| [Quick Start](quick_start.md) | Minimal `Session` example end-to-end | Beginner |
| [Complete Example](complete_example.md) | Longer worked example covering scan -> review -> export | Intermediate |
| [API Stability](api_stability.md) | Stability tiers, deprecation policy, semver guarantees | Intermediate |
| [See Also](see_also.md) | Cross-links to related documentation | Beginner |

### Core orchestration

| Page | Description | Level |
|------|-------------|-------|
| [Session API](session_api.md) | Top-level `Session` orchestrator, the recommended entry point | Beginner |
| [PipelineRunner API](pipelinerunner_api.md) | Lower-level pipeline executor for custom stage composition | Intermediate |
| [Bundle API](bundle_api.md) | Read, write, and inspect COGANT result bundles | Intermediate |
| [Export Stage and GNN Package](export_stage_and_gnn_package.md) | Export final mappings as a GNN package | Intermediate |

### Translation, scoring, and review

| Page | Description | Level |
|------|-------------|-------|
| [Fixpoint Translation API](fixpoint_translation_api.md) | Iterative rule-based translation engine | Advanced |
| [Scoring API](scoring_api.md) | Confidence scoring of role assignments | Intermediate |
| [Confidence Model API](confidence_model_api.md) | Underlying confidence model and tier policy | Advanced |
| [Review API](reviewapi.md) | Human-in-the-loop review and curation | Intermediate |

### Analysis stages

| Page | Description | Level |
|------|-------------|-------|
| [Static Analysis (`cogant.static`)](static.md) | AST parse, symbol extraction, type inference, call graph | Intermediate |
| [Dynamic Analysis API](dynamic_analysis_api.md) | Runtime / dynamic analysis hooks | Advanced |
| [Dynamic Enrichment API](dynamic_enrichment_api.md) | Augment a static graph with dynamic facts | Advanced |
| [Translate Package (`cogant.translate`)](translate.md) | Priority-ordered rule set + fixpoint, emits `SemanticMapping` records | Intermediate |
| [State Space (`cogant.statespace`)](statespace.md) | Variables, actions, and transitions compiled from rule output | Intermediate |
| [Markov Blanket (`cogant.markov`)](markov.md) | Partition the graph into μ / s / a / η sets | Intermediate |
| [GNN Package (`cogant.gnn`)](gnn.md) | `GNNPackageBuilder` + `GNNValidator` (0–100 score) | Intermediate |
| [Reverse (`cogant.reverse`)](reverse.md) | GNN → runnable Python synthesis | Advanced |
| [Runtime (`cogant.runtime`)](runtime.md) | Active Inference agent runtime (multi-episode Bayesian learning) | Advanced |
| [Simulate (`cogant.simulate`)](simulate.md) | Forward simulation of compiled state-space models | Advanced |
| [Visualization API](visualization_api.md) | Render program graphs, GNNs, and Markov blanket diagrams | Intermediate |
| [FastAPI Server (`cogant.server`)](server.md) | REST + WebSocket endpoints for a deployable pipeline | Intermediate |

### Extension points

| Page | Description | Level |
|------|-------------|-------|
| [Plugin API](plugin_api.md) | Author parser / translator / validator / exporter plugins | Advanced |

### Operational reference

| Page | Description | Level |
|------|-------------|-------|
| [Error Handling](error_handling.md) | Exception hierarchy and recovery patterns | Intermediate |
| [Performance Tips](performance_tips.md) | Profiling and tuning recommendations | Intermediate |
| [Debugging](debugging.md) | Logging, breakpoints, and diagnostic helpers | Intermediate |

## Recommended Reading Order

1. [Overview](overview.md) — orient yourself in the API surface.
2. [Installation](installation.md) and [Quick Start](quick_start.md) — get the import path working and run a single session.
3. [Session API](session_api.md) — the main supported entry point for nearly all use cases.
4. [Complete Example](complete_example.md) — see how the moving parts fit together.
5. [Bundle API](bundle_api.md) and [Export Stage and GNN Package](export_stage_and_gnn_package.md) — read and write COGANT artifacts programmatically.
6. [Review API](reviewapi.md) and [Scoring API](scoring_api.md) — gate and curate the results.
7. [Plugin API](plugin_api.md) — only when you have a concrete extension to build.
8. [API Stability](api_stability.md) — review before pinning a production dependency.

Agent notes: [AGENTS.md](AGENTS.md) - Hub: [../index.md](../index.md)
