## Overview

The COGANT Python API provides high-level interfaces for codebase analysis and GNN translation. The main classes are:

- **Session**: Manages pipeline state and intermediate results
- **PipelineRunner**: Orchestrates all analysis stages
- **Bundle**: Wraps analysis artifacts with convenient accessors
- **ReviewAPI**: Interactive curation and review interface

### Session method index

Public methods on [`Session`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/api/session.py) (use in order for a manual pipeline):

| Method | Section |
|--------|---------|
| `Session.from_target` (classmethod) | [Creating a Session](#creating-a-session) |
| `extract_static()` | [Extracting Analysis](#extracting-analysis) |
| `extract_dynamic(...)` | [Extracting Analysis](#extracting-analysis) |
| `build_graph()` | [Building Program Graph](#building-program-graph) |
| `translate_to_gnn()` | [Translating to GNN](#translating-to-gnn) |
| `compile_state_space()` | [Compiling State Space](#compiling-state-space) |
| `export_all(output_dir, layout=False)` | [Exporting Results](#exporting-results) |

These headings anchor the table above; for narrative detail see [Quick Start](../getting-started/quickstart.md) and the source in `py/cogant/api/session.py`.

### Creating a Session

Construct with `Session.from_target(path)` after configuration is available.

### Extracting Analysis

`extract_static()` and optional `extract_dynamic(...)` populate repo and trace facts used by later stages.

### Building Program Graph

`build_graph()` materializes the typed program graph IR.

### Translating to GNN

`translate_to_gnn()` runs the semantic rule engine over the graph.

### Compiling State Space

`compile_state_space()` builds state-space variables from semantic mappings.

### Exporting Results

`export_all(output_dir, layout=False)` writes bundles, GNN artifacts, and optional layout outputs.

