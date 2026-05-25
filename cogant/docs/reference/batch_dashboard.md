# Batch dashboard

Module: `cogant.viz.batch_dashboard`
· Script: `scripts/batch_dashboard.py` (COGANT project root) · Wired from:
`run_all.py` (`steps.batch_dashboard`, default **on**).

## Purpose

A normal `cogant translate` invocation produces one
`cogant.viz.dashboard.generator.DashboardGenerator` HTML page for a
single repository. The project-root
`run_all.py` orchestrator, by contrast, runs the pipeline against
several targets in one batch and ends up with one
`<output_root>/<target_id>/` tree per target plus a top-level
`<output_root>/run_manifest.json` describing the sweep.

`BatchDashboardGenerator` walks that manifest, reads each target's
`bundle.json`, and emits a small set of analyzer- and
manuscript-friendly artifacts under `<output_root>/dashboard/`:

| File | Purpose |
| --- | --- |
| `summary.csv` | One row per target: id, kind, score, node/edge/mapping counts, gnn-package file count, wall time, failure count, presence flags. |
| `metrics_per_target.json` | Same data, JSON-structured, plus the manifest's `summary` block. |
| `dashboard.md` | Top-level Markdown report linking every artifact; embeds the Mermaid charts below. |
| `node_count_bar.mmd` | Mermaid `xychart-beta` bar of program-graph nodes per target. |
| `edge_count_bar.mmd` | Mermaid `xychart-beta` bar of program-graph edges per target. |
| `score_distribution.mmd` | Mermaid `pie` of validation-score buckets (`100`, `90-99`, `70-89`, `<70`, `no-score`). |
| `visual_completeness.mmd` | Mermaid `pie` of per-target visual artifact completeness (`complete`, `partial`, `missing`). |
| `parser_status_distribution.mmd` | Mermaid `pie` of parsed, fallback, partial, failed, and unknown parser-status buckets. |
| `role_distribution.mmd` | Mermaid `pie` of semantic role counts aggregated across targets. |
| `confidence_distribution.mmd` | Mermaid `pie` of confidence-tier counts aggregated across targets. |
| `roundtrip_status.mmd` | Mermaid `pie` of strict structural-isomorphism, role-preserved, drift, failed, and missing roundtrip status. |
| `failure_reasons.mmd` | Mermaid `pie` of failed-step labels from the batch manifest. |
| `run_gantt.mmd` | Mermaid `gantt` of recorded command durations grouped by target. |

Pure-stdlib (no `matplotlib`, no `jinja2`); works under the minimal
install profile.

When rendered into manuscript PNGs, the copied batch figures keep the same
machine-readable evidence chain. `metrics_per_target.json` is the source
artifact, and the manuscript sidecar derives target count, aggregate role count,
parser-status variety, roundtrip-status variety, and visual-artifact totals from
that JSON. This keeps the dashboard figure inspectable as a batch evidence
summary instead of a hand-written chart.

## Python API

```python
from pathlib import Path
from cogant.viz import BatchDashboardGenerator

gen = BatchDashboardGenerator(Path("cogant/output"))
written = gen.write_all()  # -> cogant/output/dashboard/
for name, path in written.items():
    print(name, path)
```

The same module also offers a one-call shortcut:

```python
from cogant.viz import write_batch_dashboard
write_batch_dashboard(Path("cogant/output"))
```

For ad-hoc reports (no manifest on disk), pass one explicitly:

```python
gen = BatchDashboardGenerator(out, manifest={"targets": [...], "summary": {}})
md = gen.render_markdown_dashboard(gen.collect_target_metrics())
```

## CLI

```bash
# From the COGANT project root:
uv run --directory cogant python ../scripts/batch_dashboard.py \
    --output-root cogant/output
```

The script accepts paths relative to either the current process directory
or the COGANT project root, so the command above works even though `uv
--directory cogant` runs Python from the inner package root.

Flags:

- `--output-root <dir>` — directory written by `run_all` (default `cogant/output`).
- `--dashboard-dir <dir>` — where to write the artifacts (default `<output-root>/dashboard`).
- `--manifest <file>` — explicit `run_manifest.json` path (mostly for tests).
- `--quiet` — suppress the stderr banner; stdout still lists every written file.

Exit codes: **0** success · **2** missing `--output-root` or malformed manifest.

## Wire-in from `run_all`

`run_all.py` runs the dashboard once at the very end of a batch, after
`<output_root>/run_manifest.json` is written. Each manifest command entry
includes `{cmd, step, exit, wall_time_s}` so `run_gantt.mmd` can render
real timings, and the dashboard directory is recorded under
`manifest["post_steps"]["batch_dashboard"]["dir"]`. To
opt out for a particular batch, set `"steps": { "batch_dashboard":
false }` in `run_all.json`.

A dashboard failure is **advisory** — `run_all` logs it but does not
treat the batch as failed.

## Robustness notes

- Missing or unparseable per-target `bundle.json` files are tolerated:
  the row is still emitted with `score = None` and zero counts.
- Empty `<output_root>/` (no targets discovered) produces a valid but minimal
  Markdown report and Mermaid files (Mermaid charts use a single
  `"(no targets)"` placeholder bar so the syntax remains valid).
- Parser status is best-effort and never blocks dashboard generation:
  explicit parser reports win when present; otherwise graph evidence yields
  `parsed`, parser/static failures yield `failed`, and absent evidence stays
  `unknown`.
- Manifests without per-command `wall_time_s` produce a placeholder
  Gantt chart so downstream Mermaid renders never fail.
- Roundtrip metrics are optional. When `roundtrip/metrics.json` is absent,
  status fields are explicitly `not_present`; graph-edit and generated-code
  fields are not inferred from other artifacts.

## Related

- `cogant.viz.DashboardGenerator` —
  single-target interactive HTML dashboard.
- `cogant.viz.MermaidGenerator` —
  in-bundle Mermaid views (per-target).
- `tools/batch_api.py` — drives the `analyze-graph` /
  `analyze-static` / `multi-export` / `visualize` steps that produce
  some of the auxiliary directories the dashboard reports on.
