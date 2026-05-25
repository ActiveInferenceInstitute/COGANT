# COGANT Real-World Forward-Pipeline Evaluation

**Date:** 2026-04-09
**Tool:** `cogant translate --no-dynamic` (full 10-stage forward pipeline minus
dynamic coverage enrichment), followed by `cogant export-gnn … --format markdown`
**COGANT version:** historical April 2026 workspace snapshot at `projects_in_progress/cogant/`; this report predates the v0.6 roundtrip taxonomy and is preserved as a forward-pipeline scaling study.
**Host:** macOS, `/usr/bin/time -l` for wall-clock and peak RSS
**Harness:** `/tmp/cogant_eval/run_eval.sh` + `/tmp/cogant_eval/collect.py`
**Raw metrics:** `../../evaluation/real_world_eval_summary.json`

## What "forward pipeline" means here

`cogant scan --format json` runs static extraction only and returns empty
`nodes`/`edges` (by design — it's a sanity check, not a pipeline). The task's
intent is the full graph → GNN forward path, which is `cogant translate`. That
command runs the 10 documented stages: **ingest → static → normalize → graph
→ dynamic → translate → statespace → process → export → validate**. All 8 repos
below were run with `--no-dynamic` (dynamic enrichment is a separate path that
needs a pre-existing coverage database) and then re-exported with
`cogant export-gnn <bundle> --format markdown` to exercise the second code
path the task names.

Each run writes a full `gnn_package/` directory; matrix counts below are
extracted from `gnn_package/model.gnn.md` by counting declarations in the
`## StateSpaceBlock` section, and section-completeness is measured from the
top-level `## <Name>` offsets in the same file.

## Summary table

| Repo | PyFiles | Nodes | Edges | Time(s) | PeakRSS(MB) | Sections | A | B | C | D | Result |
|---|---:|---:|---:|---:|---:|:-:|---:|---:|---:|---:|:-:|
| flask | 83 | 978 | 1136 | 2.9 | 148 | 4/4 | 28 | 28 | 144 | 28 | pass |
| requests | 36 | 706 | 885 | 4.8 | 168 | 4/4 | 29 | 29 | 138 | 29 | pass |
| httpx | 60 | 1192 | 1525 | 4.1 | 236 | 4/4 | 60 | 60 | 259 | 60 | pass |
| fastapi | 1121 | 6050 | 5213 | 19.1 | 447 | 4/4 | 84 | 84 | 1700 | 84 | pass |
| pydantic | 402 | 8425 | 9318 | 49.4 | 1308 | 4/4 | 225 | 225 | 959 | 225 | pass |
| click | 63 | 1129 | 1426 | 4.0 | 221 | 4/4 | 52 | 52 | 249 | 52 | pass |
| rich | 213 | 2047 | 2542 | 8.5 | 522 | 4/4 | 123 | 123 | 418 | 123 | pass |
| dulwich | 233 | 8601 | 15441 | 380.0 | 8511 | 4/4 | 448 | 448 | 1687 | 448 | pass |

**Aggregate result: 8/8 pass.** All runs completed with exit 0, all 10 pipeline
stages returned `status: success`, `validate.passed == True`, and the internal
GNN validator reported a 100.0% quality score on every bundle. Every repo's
`## StateSpaceBlock`, `## Connections`, `## InitialParameterization`, and
`## ActInfOntologyAnnotation` sections are non-empty, and every repo produces
at least one non-empty A, B, C, and D matrix block.

## Per-repo notes

### flask (pallets/flask) — 83 py files, 18 362 LoC
Fastest repo in the set at 2.9 s / 148 MB. 978 graph nodes, 1 136 edges. 28
observation modalities (A), 28 hidden-state factors (B/D), 144 preference
components (C). No warnings beyond the cosmetic "matplotlib required for PNG
export" (which fires on every run because `cogant[viz]` isn't installed in
this environment — Mermaid/HTML artifacts are still written).

### requests (psf/requests) — 36 py files, 11 177 LoC
Second fastest by file count but slightly slower wall-clock than flask
(4.8 s / 168 MB) because of more per-module import work. 706 nodes / 885 edges.
Clean run, validate passed, 4/4 sections present.

### httpx (encode/httpx) — 60 py files, 17 753 LoC
4.1 s / 236 MB. 1 192 nodes / 1 525 edges. Higher A/B/C/D counts than flask
despite similar LoC (60/60/259/60 vs flask's 28/28/144/28) — the extra async
client code surfaces more hidden-state factors. Clean.

### fastapi (tiangolo/fastapi) — 1 121 py files, 107 493 LoC
The file count here is inflated by a huge `tests/` and `docs_src/` tree; the
pipeline chews through it in 19.1 s / 447 MB. 6 050 nodes / 5 213 edges (edge
density is lower than small repos because a lot of the files are leaf example
scripts with few cross-imports). C-matrix count is 1 700, the largest in the
set after pydantic — a lot of distinct preference components were extracted
from the Pydantic-driven response model code. Clean exit, 4/4 sections.

### pydantic (pydantic/pydantic) — 402 py files, 163 665 LoC
49.4 s / 1.31 GB. 8 425 nodes / 9 318 edges. Biggest matrix dimensionality in
the set for A/B/D (225 each) — many state factors. Clean run but this is where
RSS first crosses 1 GB; the translate stage is the dominant cost (semantic
mapping and embedding computation).

### click (pallets/click) — 63 py files, 22 615 LoC
4.0 s / 221 MB. 1 129 / 1 426. A prior eval on a different date (in the
pre-existing `../../evaluation/real_world_eval_results.json`) reported the same node/edge
numbers for click — matches, confirming determinism of the pipeline over time.

### rich (Textualize/rich) — 213 py files, 51 766 LoC
8.5 s / 522 MB. 2 047 / 2 542. 123 A/B/D factors, 418 preference components.
Clean. No anomalies.

### dulwich (jelmer/dulwich) — 233 py files, 169 956 LoC
**This is the stress case.** 380 s wall clock and 8.5 GB peak RSS. Still
passes — 8 601 nodes / 15 441 edges (nearly 2× the edge:node ratio of every
other repo, reflecting dulwich's heavily-connected object-store code), and all
4 GNN sections populated with 448 A/B/D factors. But a 22× wall-clock blow-up
over the median and an 8.5 GB memory footprint is a serious scaling cliff that
deserves attention (see "Honest assessment" below).

The generated `model.gnn.md` for dulwich is **485 310 lines** — an order of
magnitude larger than any other repo in the set (next largest: pydantic at
61 079 lines). This is the artifact size explosion that's driving both
the wall-clock and the RSS.

## Failure analysis

There were no hard failures in this run. The only observable issues are
**scaling symptoms**, not correctness bugs:

1. **dulwich RSS: 8.5 GB.** This is ~6.5× pydantic's peak and ~57× flask's.
   Given that dulwich only has ~1.6× pydantic's LoC, the scaling is clearly
   super-linear. The most likely culprit is the edge:node ratio (1.80 for
   dulwich vs ~1.1 for the other repos) interacting with an O(edges) or
   O(edges × factors) data structure somewhere in `translate` / `statespace`.
2. **dulwich wall-clock: 380 s** (next-largest: pydantic 49 s). Same story —
   super-linear scaling in edge count.
3. **dulwich GNN markdown: 485 310 lines.** The model.gnn.md file is itself a
   performance problem: it's large enough that downstream tools (diff, render,
   editor loading) will struggle. Worth investigating whether the `## State
   Space`, `## Program Graph Connections`, and `## Likelihood Structure`
   sections are writing one row per graph edge in a way that explodes.
4. **Cosmetic: `matplotlib required for PNG export`** warning on every repo.
   The pipeline still writes Mermaid/SVG/HTML for all diagrams; only the
   rasterised PNG fallback is skipped. Install `cogant[viz]` to silence.
5. **`cogant scan` reports `nodes: []`/`edges: []`.** This is by-design
   documented behaviour (scan = static extraction only, no graph build), but
   it is a foot-gun for anyone reading the task wording literally. The
   quick-sanity-check command and the "forward pipeline" command are not the
   same command.

No `bundle.errors` entries were populated on any run, and the built-in GNN
validator returned `score: 100.0%` on every bundle.

## Honest assessment of real-world readiness

**The good news.** The evaluated COGANT snapshot survives the full 10-stage forward pipeline
on every repo in a fairly demanding set: a micro-framework (flask), two HTTP
clients (requests, httpx), a validator with heavy metaprogramming (pydantic),
a web framework (fastapi), a CLI toolkit (click), a terminal rendering library
(rich), and a pure-Python git implementation (dulwich). Seven of the eight
repos finish in under a minute with RSS under 1.3 GB, which is well inside
"usable on a developer laptop" territory. The GNN validator reports 100% on
every bundle, the statespace stage produces coherent A/B/C/D factor counts
that scale with the repo's structural complexity, and the `export-gnn`
roundtrip re-emits markdown cleanly from every bundle.

**The bad news.** Dulwich is a canary for a scaling cliff. Going from pydantic
(163K LoC, 49 s, 1.3 GB) to dulwich (170K LoC, 380 s, 8.5 GB) is a 7.7×
wall-clock and 6.5× memory blow-up for roughly equal code size. The
distinguishing feature of dulwich is its edge density (1.80 edges/node vs
~1.10 for every other repo in this set), which strongly suggests the blow-up
lives in a stage whose cost is driven by edges rather than nodes — most
likely the translation / statespace / export steps that materialise per-edge
GNN markdown rows (dulwich's GNN markdown is 485K lines, 8× bigger than the
next largest).

**Bottom line.** For **typical Python libraries up to ~100K LoC with normal
coupling**, COGANT's forward pipeline is ready to be pointed at real code
without babysitting: fast, deterministic, 100% validator pass, populated
matrices. For **heavily-connected codebases** (git internals, protocol
stacks, large monorepos), expect to hit a memory cliff around 8–10 GB and
multi-minute wall clocks, and plan to either (a) scope the analysis to a
subdirectory, (b) profile the translate/statespace/export stages to find the
edge-driven hot spot, or (c) introduce a pagination / streaming option for
the GNN markdown emitter so the 485K-line single-file output stops being a
liability. None of these are correctness problems, but the dulwich profile
should not ship in a v1.0 release without either a fix or a loud "repos with
edge:node > 1.5 may require N GB of RAM" warning in the docs.

## Reproduction

```bash
# From cogant/ (inside projects_in_progress/cogant/)
cd cogant
for repo in flask requests httpx fastapi pydantic click rich dulwich; do
  /usr/bin/time -l \
    uv run cogant translate ../../../evaluation/eval_repos/$repo \
      --no-dynamic -o /tmp/cogant_eval/${repo}_out
  uv run cogant export-gnn /tmp/cogant_eval/${repo}_out/bundle.json \
    --format markdown -o /tmp/cogant_eval/${repo}_gnn_md
done
python3 /tmp/cogant_eval/collect.py
```

Artifacts:

- Per-repo bundle directories: `/tmp/cogant_eval/<repo>_out/`
- Per-repo re-exported markdown: `/tmp/cogant_eval/<repo>_gnn_md/bundle.md`
- Per-repo raw `/usr/bin/time -l` output: `/tmp/cogant_eval/<repo>.time`
- Collected metrics JSON: `../../evaluation/real_world_eval_summary.json`
- Harness script: `/tmp/cogant_eval/run_eval.sh`
- Collector script: `/tmp/cogant_eval/collect.py`
