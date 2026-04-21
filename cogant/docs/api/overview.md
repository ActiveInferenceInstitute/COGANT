## Overview

> **What this page is:** A high-level tour of COGANT's stable Python API surface — `Session`, `PipelineRunner`, `Bundle`, and `ReviewAPI`.
>
> **Prerequisites:** [Installation](installation.md) and a brief skim of [Tutorial 1: Quickstart](../tutorials/01_quickstart.md).
>
> **Reading time:** ~8 minutes
>
> **Next steps:** [Quick Start](quick_start.md) · [Session API](session_api.md) · [PipelineRunner API](pipelinerunner_api.md)

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

## Examples

Public classes documented above (`Session`, `PipelineRunner`, `Bundle`, `ReviewAPI`) are exercised by the following:

- **Zoo:** [`examples/zoo/01_simple_state/`](https://github.com/cogant-contributors/cogant/tree/main/cogant/examples/zoo/01_simple_state) — simplest end-to-end target for `Session.from_target` → `extract_static` → `translate_to_gnn` → `export_all`.
- **Zoo:** [`examples/zoo/04_pomdp_minimal/`](https://github.com/cogant-contributors/cogant/tree/main/cogant/examples/zoo/04_pomdp_minimal) — minimal POMDP that exercises all four `Session` analysis stages on a single fixture.
- **Cookbook:** [Recipe 1: Scan your first Python project](../cookbook/01_scan_basic.md) — uses the same `Session`/`PipelineRunner` surface from the CLI.
- **Cookbook:** [Recipe 2: JSON output](../cookbook/02_json_output.md) — `Bundle.save_json` round-trip used by automation.
- **Tutorial:** [Tutorial 1: Quickstart — end-to-end in five minutes](../tutorials/01_quickstart.md) — narrative walkthrough of every method in the index above.
