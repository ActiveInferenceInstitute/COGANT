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

