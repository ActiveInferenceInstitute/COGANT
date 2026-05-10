#!/usr/bin/env python3
"""COGANT Reproducible Benchmark Suite.

Runs the full in-process COGANT pipeline against a fixed corpus of
six fixtures and reports:

* Wall-clock per stage (ingest, static, normalize, graph, translate,
  statespace) and total
* Peak memory delta (RSS via ``resource.getrusage``)
* Graph size (``|V|``, ``|E|``, avg_degree) from
  ``bundle.artifacts["_program_graph"]``
* Rule firings per ``MappingKind`` from
  ``bundle.artifacts["_semantic_mappings"]``
* GNN output size (A/B/C/D matrix dimensions) via
  :class:`cogant.gnn.matrices.GNNMatrices`

Each fixture is run ``--runs`` times (default 3) with a discarded
warm-up sample when ``--runs >= 2``. Per-stage and total timings are
reported as median / p95 / min in milliseconds.

Results are emitted in two formats:

* **JSON**: ``benchmarks/results/suite_YYYYMMDD.json``
* **Markdown**: ``benchmarks/results/suite_YYYYMMDD.md``

Complements :mod:`benchmarks.bench_graph_build` (which times the
pure Python vs Rust graph builder in isolation) and
:mod:`benchmarks.bench_perf_regression` (which enforces a 20%
regression budget against ``perf_baseline.json``). This suite is not
a gate -- it is a reproducible snapshot you can diff between commits.

Usage::

    cd projects_in_progress/cogant/cogant
    uv run python benchmarks/bench_suite.py
    uv run python benchmarks/bench_suite.py --runs 5
    uv run python benchmarks/bench_suite.py --fixture calculator
    uv run python benchmarks/bench_suite.py --output-json /tmp/bench.json
"""

from __future__ import annotations

import argparse
import json
import logging
import platform
import resource
import statistics
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

# Mirror the ``sys.path`` tweak used by ``bench_perf_regression.py`` and
# ``tests/conftest.py`` so the pure-Python package under ``py/`` is
# importable without an editable install.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_PY_ROOT = _REPO_ROOT / "py"
if _PY_ROOT.is_dir() and str(_PY_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_ROOT))

from cogant.api import orchestration  # noqa: E402
from cogant.api.bundle import ArtifactKey, Bundle  # noqa: E402

logger = logging.getLogger(__name__)

# --- Fixture corpus ---------------------------------------------------------

# Canonical fixture corpus. Keys are stable benchmark IDs; values are
# filesystem paths relative to the cogant repo root. The list is
# intentionally mixed: three control-positive micro-fixtures and three
# real-world-shaped fixtures so regressions on one class don't hide
# wins on the other.
_FIXTURE_CORPUS: dict[str, Path] = {
    "calculator": _REPO_ROOT / "examples" / "control_positive" / "calculator",
    "event_pipeline": _REPO_ROOT / "examples" / "control_positive" / "event_pipeline",
    "flask_mini": _REPO_ROOT / "examples" / "control_positive" / "flask_mini",
    "flask_app": _REPO_ROOT / "examples" / "real_world" / "flask_app",
    "requests_lib": _REPO_ROOT / "examples" / "real_world" / "requests_lib",
    "json_stdlib": _REPO_ROOT / "examples" / "real_world" / "json_stdlib",
}


def _discover_fixtures(
    requested: list[str] | None = None,
) -> dict[str, Path]:
    """Filter the fixture corpus to those that exist on disk.

    Args:
        requested: Optional explicit fixture names. When provided,
            only these fixtures are returned (and any missing names
            are logged and skipped).

    Returns:
        Ordered dict of ``name -> path`` for fixtures present on disk.
    """
    if requested:
        selected = {}
        for name in requested:
            if name not in _FIXTURE_CORPUS:
                logger.warning("Unknown fixture %r; skipping", name)
                continue
            path = _FIXTURE_CORPUS[name]
            if not path.exists():
                logger.warning("Fixture %r not on disk: %s", name, path)
                continue
            selected[name] = path
        return selected

    return {name: path for name, path in _FIXTURE_CORPUS.items() if path.exists()}


# --- Memory helpers ---------------------------------------------------------


def _rss_bytes() -> int:
    """Return current process RSS in bytes.

    ``ru_maxrss`` is reported in kilobytes on Linux and in bytes on
    macOS -- we detect the platform and normalize. This measures the
    peak resident set size of the calling process since launch, which
    is a monotone high-water mark: to compute a *delta* we sample it
    before and after the stage and take the difference.
    """
    max_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return int(max_rss)
    # Linux (and most other Unixes) report kilobytes.
    return int(max_rss) * 1024


# --- Per-run measurement ---------------------------------------------------


@dataclass
class StageTiming:
    """Wall-clock time in milliseconds for one pipeline stage."""

    ingest_ms: float = 0.0
    static_ms: float = 0.0
    normalize_ms: float = 0.0
    graph_ms: float = 0.0
    translate_ms: float = 0.0
    statespace_ms: float = 0.0

    def total_ms(self) -> float:
        """Sum of all recorded stage wall-clock milliseconds."""
        return (
            self.ingest_ms
            + self.static_ms
            + self.normalize_ms
            + self.graph_ms
            + self.translate_ms
            + self.statespace_ms
        )


@dataclass
class RunResult:
    """All metrics captured for a single pipeline invocation.

    A ``RunResult`` is produced per iteration of a fixture. The
    :func:`_aggregate` reducer folds a list of ``RunResult`` into the
    final per-fixture report (medians, p95s, rule firings, matrix
    shapes).
    """

    wall_ms: float
    stages: StageTiming
    memory_delta_mb: float
    graph_nodes: int
    graph_edges: int
    graph_avg_degree: float
    mapping_counts: dict[str, int]
    gnn_shapes: dict[str, Any]


def _time_stage(fn: Callable[[], Any]) -> tuple[Any, float]:
    """Time a stage closure and return ``(result, elapsed_ms)``."""
    start = time.perf_counter()
    result = fn()
    return result, (time.perf_counter() - start) * 1000.0


def _graph_stats(bundle: Bundle) -> tuple[int, int, float]:
    """Compute ``(nodes, edges, avg_degree)`` from the bundle program graph.

    Returns zeros when the graph artifact is missing (e.g. an early
    stage failed). ``avg_degree`` is ``2 * |E| / |V|`` (undirected
    convention); we report this because the program graph is
    semantically multi-directional for translation rules even though
    it is stored as a directed multigraph.
    """
    pg = bundle.get_artifact(ArtifactKey.PROGRAM_GRAPH)
    if pg is None:
        return 0, 0, 0.0
    n = int(pg.node_count()) if hasattr(pg, "node_count") else len(pg.nodes)
    e = int(pg.edge_count()) if hasattr(pg, "edge_count") else len(pg.edges)
    avg = (2.0 * e / n) if n > 0 else 0.0
    return n, e, avg


def _mapping_counts(bundle: Bundle) -> dict[str, int]:
    """Count semantic mappings by ``MappingKind`` name.

    Missing artifact -> empty dict. The count is keyed by the enum
    ``.name`` (e.g. ``HIDDEN_STATE``, not ``"hidden_state"``) so the
    output is stable across enum value renames.
    """
    mappings = bundle.get_artifact(ArtifactKey.SEMANTIC_MAPPINGS) or {}
    counts: dict[str, int] = {}
    for m in mappings.values():
        key = m.kind.name if hasattr(m.kind, "name") else str(m.kind)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _gnn_shapes(bundle: Bundle) -> dict[str, Any]:
    """Extract A/B/C/D matrix dimensions from the bundle.

    Uses :class:`cogant.gnn.matrices.GNNMatrices` directly against the
    bundle's program graph, semantic mappings, and compiled state
    space. Returns ``{"available": False, "reason": ...}`` if any
    prerequisite artifact is missing or the matrix computation
    raises. Shapes are reported as a flat dict so they serialize
    cleanly into JSON and are easy to compare across runs.
    """
    pg = bundle.get_artifact(ArtifactKey.PROGRAM_GRAPH)
    mappings = bundle.get_artifact(ArtifactKey.SEMANTIC_MAPPINGS) or {}
    ss = bundle.get_artifact(ArtifactKey.STATE_SPACE_MODEL)
    if pg is None or ss is None:
        return {"available": False, "reason": "missing graph or state space"}
    try:
        from cogant.gnn.matrices import GNNMatrices

        gnn = GNNMatrices(pg, mappings, ss)
        n_states = int(gnn.n_states)
        n_obs = int(gnn.n_obs)
        # Number of actions isn't always exposed as a property; fall
        # back to the private list count if needed.
        n_actions = int(getattr(gnn, "n_actions", 0)) or len(getattr(gnn, "_actions", []))
        return {
            "available": True,
            "n_states": n_states,
            "n_obs": n_obs,
            "n_actions": n_actions,
            # A: [n_obs x n_states]
            "A_rows": n_obs,
            "A_cols": n_states,
            # B: [n_states x n_states x n_actions]
            "B_rows": n_states,
            "B_cols": n_states,
            "B_depth": n_actions,
            # C: [n_obs]
            "C_len": n_obs,
            # D: [n_states]
            "D_len": n_states,
        }
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("GNN shape extraction failed: %s", exc)
        return {"available": False, "reason": f"{type(exc).__name__}: {exc}"}


def _run_once(target: Path) -> RunResult:
    """Drive the pipeline through ``orchestration.run_*`` and measure.

    Stages are invoked directly (rather than via
    :class:`PipelineRunner`) so we get per-stage timing without
    having to parse log output. This mirrors the flow the CLI and
    thin orchestrator examples use.
    """
    bundle = Bundle(target=str(target))
    stages = StageTiming()

    rss_before = _rss_bytes()
    total_start = time.perf_counter()

    ingest_result, stages.ingest_ms = _time_stage(
        lambda: orchestration.run_ingest(str(target), bundle)
    )
    bundle.stage_results["ingest"] = ingest_result

    static_result, stages.static_ms = _time_stage(lambda: orchestration.run_static(bundle))
    bundle.stage_results["static"] = static_result

    normalize_result, stages.normalize_ms = _time_stage(lambda: orchestration.run_normalize(bundle))
    bundle.stage_results["normalize"] = normalize_result

    graph_result, stages.graph_ms = _time_stage(
        lambda: orchestration.run_graph(bundle, str(target))
    )
    bundle.stage_results["graph"] = graph_result

    translate_result, stages.translate_ms = _time_stage(lambda: orchestration.run_translate(bundle))
    bundle.stage_results["translate"] = translate_result

    statespace_result, stages.statespace_ms = _time_stage(
        lambda: orchestration.run_statespace(bundle, str(target))
    )
    bundle.stage_results["statespace"] = statespace_result

    wall_ms = (time.perf_counter() - total_start) * 1000.0
    rss_after = _rss_bytes()
    memory_delta_mb = max(0.0, (rss_after - rss_before) / (1024.0 * 1024.0))

    nodes, edges, avg_degree = _graph_stats(bundle)
    counts = _mapping_counts(bundle)
    gnn_shapes = _gnn_shapes(bundle)

    return RunResult(
        wall_ms=wall_ms,
        stages=stages,
        memory_delta_mb=memory_delta_mb,
        graph_nodes=nodes,
        graph_edges=edges,
        graph_avg_degree=avg_degree,
        mapping_counts=counts,
        gnn_shapes=gnn_shapes,
    )


# --- Aggregation ------------------------------------------------------------


def _percentile(sorted_samples: list[float], pct: float) -> float:
    """Nearest-rank percentile on an already-sorted list.

    Mirrors the approach used in ``bench_perf_regression.measure``: the
    index is ``ceil(pct * n) - 1`` clamped to ``[0, n - 1]``. For
    small samples (``n == 3``) ``p95`` collapses to the max, which is
    what we want for an "upper bound" reading.
    """
    n = len(sorted_samples)
    if n == 0:
        return 0.0
    idx = min(n - 1, max(0, int(round(pct * n)) - 1))
    return sorted_samples[idx]


def _summarize(values: list[float]) -> dict[str, float]:
    """Median / p95 / min summary for a list of float samples."""
    if not values:
        return {"median": 0.0, "p95": 0.0, "min": 0.0}
    sorted_vals = sorted(values)
    return {
        "median": round(statistics.median(sorted_vals), 2),
        "p95": round(_percentile(sorted_vals, 0.95), 2),
        "min": round(sorted_vals[0], 2),
    }


def _aggregate(runs: list[RunResult]) -> dict[str, Any]:
    """Fold a list of ``RunResult`` into a single report dict.

    Timings collapse to median/p95/min summaries, while structural
    metrics (node/edge counts, mapping counts, matrix shapes) are taken
    from the *first* run on the assumption that the pipeline is
    deterministic. If a later run disagrees we still keep the first-run
    value but stash the discrepancy under ``structural_drift`` for
    debugging.
    """
    if not runs:
        return {"runs": 0}

    first = runs[0]
    wall = [r.wall_ms for r in runs]
    memory = [r.memory_delta_mb for r in runs]

    stage_samples: dict[str, list[float]] = {
        "ingest": [r.stages.ingest_ms for r in runs],
        "static": [r.stages.static_ms for r in runs],
        "normalize": [r.stages.normalize_ms for r in runs],
        "graph": [r.stages.graph_ms for r in runs],
        "translate": [r.stages.translate_ms for r in runs],
        "statespace": [r.stages.statespace_ms for r in runs],
    }

    drift: list[str] = []
    for r in runs[1:]:
        if r.graph_nodes != first.graph_nodes or r.graph_edges != first.graph_edges:
            drift.append(
                f"graph size diverged: first=({first.graph_nodes},{first.graph_edges}) "
                f"later=({r.graph_nodes},{r.graph_edges})"
            )
        if r.mapping_counts != first.mapping_counts:
            drift.append("mapping_counts diverged")

    report: dict[str, Any] = {
        "runs": len(runs),
        "wall_ms": _summarize(wall),
        "stage_ms": {name: _summarize(vals) for name, vals in stage_samples.items()},
        "memory_mb": {
            "peak_delta_median": round(statistics.median(memory), 2) if memory else 0.0,
            "peak_delta_max": round(max(memory), 2) if memory else 0.0,
        },
        "graph": {
            "nodes": first.graph_nodes,
            "edges": first.graph_edges,
            "avg_degree": round(first.graph_avg_degree, 3),
        },
        "mappings": dict(sorted(first.mapping_counts.items())),
        "mappings_total": sum(first.mapping_counts.values()),
        "gnn": first.gnn_shapes,
    }
    if drift:
        report["structural_drift"] = drift
    return report


# --- Driver -----------------------------------------------------------------


def run_fixture(name: str, path: Path, iterations: int) -> dict[str, Any]:
    """Measure a single fixture ``iterations`` times and aggregate.

    When ``iterations >= 2`` we run one extra warm-up iteration whose
    timing is discarded but whose structural metrics are still used as
    a sanity check in :func:`_aggregate`. This gives import caches and
    filesystem state a chance to stabilize before the first recorded
    sample, matching ``bench_perf_regression.measure``.
    """
    if iterations < 1:
        raise ValueError(f"iterations must be >= 1, got {iterations}")

    logger.info("[%s] %s", name, path)

    runs: list[RunResult] = []
    total = iterations + (1 if iterations >= 2 else 0)
    for idx in range(total):
        run = _run_once(path)
        if total > iterations and idx == 0:
            logger.debug("[%s] warmup: %.1fms (discarded)", name, run.wall_ms)
            continue
        runs.append(run)
        logger.info(
            "[%s] run %d/%d: %.1fms  nodes=%d edges=%d mappings=%d",
            name,
            len(runs),
            iterations,
            run.wall_ms,
            run.graph_nodes,
            run.graph_edges,
            sum(run.mapping_counts.values()),
        )

    report = _aggregate(runs)
    report["path"] = str(path)
    return report


def run_suite(fixtures: dict[str, Path], iterations: int) -> dict[str, Any]:
    """Run the suite against every fixture and return a full report dict."""
    cogant_version = "unknown"
    try:
        from cogant import __version__ as cogant_version  # noqa: F401
    except ImportError:
        # Package not importable from this Python; report "unknown" version.
        pass

    suite: dict[str, Any] = {
        "date": date.today().isoformat(),
        "cogant_version": cogant_version,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "iterations": iterations,
        "fixtures": {},
    }

    for name, path in fixtures.items():
        try:
            suite["fixtures"][name] = run_fixture(name, path, iterations)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Fixture %s failed", name)
            suite["fixtures"][name] = {
                "error": f"{type(exc).__name__}: {exc}",
                "path": str(path),
            }

    return suite


# --- Reporting --------------------------------------------------------------


def _fmt_ms(summary: dict[str, float]) -> str:
    """Render a median/p95 summary in a compact, column-friendly form."""
    return f"{summary.get('median', 0):.0f} / {summary.get('p95', 0):.0f}"


def render_markdown(suite: dict[str, Any]) -> str:
    """Render the suite report as a human-readable Markdown document.

    The top-level table gives a one-row-per-fixture summary (wall
    median/p95, graph size, mapping count, memory). Two detail
    sections follow: per-stage timing breakdown and per-fixture
    rule-firing histograms. This format is intentionally the same
    shape ``bench_perf_regression.py`` uses in its CI comment
    template, so both harnesses can share a downstream renderer.
    """
    lines: list[str] = []
    lines.append(f"# COGANT Benchmark Suite -- {suite.get('date', '?')}")
    lines.append("")
    lines.append(f"- cogant version: `{suite.get('cogant_version', '?')}`")
    lines.append(f"- python: `{suite.get('python_version', '?')}`")
    lines.append(f"- platform: `{suite.get('platform', '?')}`")
    lines.append(f"- iterations per fixture: `{suite.get('iterations', '?')}`")
    lines.append("")

    fixtures = suite.get("fixtures", {})
    if not fixtures:
        lines.append("_No fixtures measured._")
        return "\n".join(lines)

    # Summary table.
    lines.append("## Summary")
    lines.append("")
    lines.append("| Fixture | Wall ms (median/p95) | Nodes | Edges | Mappings | Memory MB |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for name, report in fixtures.items():
        if "error" in report:
            lines.append(f"| {name} | ERROR: {report['error']} | - | - | - | - |")
            continue
        graph = report.get("graph", {})
        mem = report.get("memory_mb", {})
        lines.append(
            f"| {name} "
            f"| {_fmt_ms(report.get('wall_ms', {}))} "
            f"| {graph.get('nodes', 0)} "
            f"| {graph.get('edges', 0)} "
            f"| {report.get('mappings_total', 0)} "
            f"| {mem.get('peak_delta_median', 0):.1f} |"
        )
    lines.append("")

    # Per-stage breakdown.
    lines.append("## Stage Breakdown (median ms)")
    lines.append("")
    lines.append("| Fixture | ingest | static | normalize | graph | translate | statespace |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for name, report in fixtures.items():
        if "error" in report:
            continue
        stages = report.get("stage_ms", {})
        lines.append(
            f"| {name} "
            f"| {stages.get('ingest', {}).get('median', 0):.0f} "
            f"| {stages.get('static', {}).get('median', 0):.0f} "
            f"| {stages.get('normalize', {}).get('median', 0):.0f} "
            f"| {stages.get('graph', {}).get('median', 0):.0f} "
            f"| {stages.get('translate', {}).get('median', 0):.0f} "
            f"| {stages.get('statespace', {}).get('median', 0):.0f} |"
        )
    lines.append("")

    # Per-fixture mapping histograms + GNN shapes.
    lines.append("## Rule Firings & GNN Shapes")
    lines.append("")
    for name, report in fixtures.items():
        if "error" in report:
            continue
        lines.append(f"### {name}")
        lines.append("")
        mappings = report.get("mappings", {})
        if mappings:
            lines.append("**Mappings:**")
            lines.append("")
            for kind in sorted(mappings):
                lines.append(f"- `{kind}`: {mappings[kind]}")
            lines.append("")
        else:
            lines.append("_No mappings fired._")
            lines.append("")
        gnn = report.get("gnn", {})
        if gnn.get("available"):
            lines.append(
                f"**GNN shapes:** A=[{gnn.get('A_rows', 0)} x {gnn.get('A_cols', 0)}], "
                f"B=[{gnn.get('B_rows', 0)} x {gnn.get('B_cols', 0)} x {gnn.get('B_depth', 0)}], "
                f"C=[{gnn.get('C_len', 0)}], D=[{gnn.get('D_len', 0)}]"
            )
        else:
            lines.append(f"**GNN shapes:** unavailable ({gnn.get('reason', 'n/a')})")
        lines.append("")

    return "\n".join(lines)


def _default_output_paths() -> tuple[Path, Path]:
    """Compute default ``results/suite_YYYYMMDD.{json,md}`` paths."""
    stamp = date.today().strftime("%Y%m%d")
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    return (
        results_dir / f"suite_{stamp}.json",
        results_dir / f"suite_{stamp}.md",
    )


# --- CLI --------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``bench_suite`` CLI.

    Flags:

    * ``--runs`` -- iterations per fixture (default 3)
    * ``--fixture`` -- repeatable; restricts the run to specific fixture names
    * ``--output-json`` / ``--output-md`` -- override default paths
    * ``--quiet`` -- suppress INFO logging
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Iterations per fixture (default: 3)",
    )
    parser.add_argument(
        "--fixture",
        action="append",
        default=None,
        help="Restrict to a specific fixture name (repeatable)",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Path to JSON report (default: benchmarks/results/suite_YYYYMMDD.json)",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=None,
        help="Path to Markdown report (default: benchmarks/results/suite_YYYYMMDD.md)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print WARNING and above",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    fixtures = _discover_fixtures(args.fixture)
    if not fixtures:
        logger.error("No fixtures resolved; check paths under examples/")
        return 2

    logger.info("Running suite: %s", ", ".join(fixtures.keys()))
    suite = run_suite(fixtures, iterations=args.runs)

    json_path, md_path = _default_output_paths()
    if args.output_json is not None:
        json_path = args.output_json
    if args.output_md is not None:
        md_path = args.output_md

    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(json.dumps(suite, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(suite) + "\n", encoding="utf-8")

    logger.info("Wrote JSON report to %s", json_path)
    logger.info("Wrote Markdown report to %s", md_path)

    # Echo a very short summary to stdout so pipeline output is useful
    # even when --quiet is set.
    print(f"bench_suite: {len(suite['fixtures'])} fixtures, {args.runs} runs each")
    for name, report in suite["fixtures"].items():
        if "error" in report:
            print(f"  {name}: ERROR {report['error']}")
            continue
        wall = report.get("wall_ms", {}).get("median", 0)
        graph = report.get("graph", {})
        print(
            f"  {name}: {wall:.0f}ms median | "
            f"{graph.get('nodes', 0)} nodes, "
            f"{graph.get('edges', 0)} edges, "
            f"{report.get('mappings_total', 0)} mappings"
        )
    print(f"  json: {json_path}")
    print(f"  md:   {md_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
