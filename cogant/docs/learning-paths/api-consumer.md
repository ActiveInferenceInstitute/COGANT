# API Consumer — Learning Path

You want to drive COGANT from Python code, embed it inside your own pipeline,
or build a service around it. This path takes you from "I've installed the
package" to "I'm calling the runner with a custom config and handling errors
gracefully".

Estimated reading time: ~90 minutes. Estimated hands-on time: ~2 hours.

## Steps

1. **[Quick Start (CLI)](../getting-started/quickstart.md)** — Even if you'll
   never use the CLI in production, run it once. The CLI is a thin wrapper
   over the same API you'll be calling, and seeing the canonical sequence of
   stages helps everything that follows make sense.

2. **[API Reference Overview](../api/overview.md)** — Map of the public Python
   surface: which modules are stable, which are internal, and how the package
   is laid out (`cogant.translate`, `cogant.reverse`, `cogant.runtime`, etc.).

3. **[API Quick Start](../api/quick_start.md)** — The minimum amount of code
   needed to translate a repository into a GNN from inside Python. Copy this
   into a scratch script and run it before continuing.

4. **[PipelineRunner API](../api/pipelinerunner_api.md)** — The recommended
   high-level entry point. Covers how to construct a runner, supply a config,
   stream stage events, and collect results. Most production integrations
   should go through this.

5. **Cookbook recipes** — Pick the recipes that match what you need to do:
    - [Scan a Repo](../cookbook/01_scan_basic.md) — basic invocation
    - [JSON Output](../cookbook/02_json_output.md) — machine-readable results
    - [Custom Threshold](../cookbook/04_custom_threshold.md) — tuning scoring
    - [Multi-Project](../cookbook/05_multi_project.md) — batching across repos
    - [CI Integration](../cookbook/08_ci_integration.md) — wiring into a
      pipeline
    - [Batch Scan](../cookbook/12_batch_scan.md) — many repos, one job
    - [Incremental](../cookbook/13_incremental.md) — re-running only what
      changed

6. **[Error Handling](../api/error_handling.md)** — The exception hierarchy
   COGANT raises, what each error means, and how to recover or surface it
   to your users. Read this **before** you ship — it's the difference between
   a robust integration and one that swallows useful diagnostics.

## Where to go next

- For **performance tuning**, see the [Performance Tips](../api/performance_tips.md)
  page and the [Benchmarks roadmap](../roadmap/benchmarks_and_performance.md).
- For **debugging stuck pipelines**, see [Debugging](../api/debugging.md).
- For a **complete end-to-end example**, see [Complete Example](../api/complete_example.md).
- If you need to **extend the rule set or add a new exporter**, switch to the
  [Plugin Author](plugin-author.md) path.
