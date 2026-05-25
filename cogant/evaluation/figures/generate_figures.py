"""Generate reproducible manuscript figures and metrics table from live pipeline runs.

This script is the single source of truth for the numbers that appear in
``manuscript/06_experimental_setup.md``. It runs the **public API pipeline**
(same stages as ``benchmarks/bench_suite.py`` and ``cogant.api.orchestration``)
against every fixture under ``../cogant/examples/control_positive/`` and
``../cogant/examples/real_world/``, exports to a temp directory, and fills
``metrics.json`` from the resulting ``Bundle`` and ``gnn_package/`` so graph
counts match Table 11. (The ``examples/orchestrate_roundtrip.py`` demo may
emit a larger serialized graph; it is not used here.) Files written:

    evaluation/figures/fig1_graph_sizes.png        -- bar chart of nodes/edges per fixture
    evaluation/figures/fig2_node_kinds.png         -- stacked bar of node kinds per fixture
    evaluation/figures/fig3_state_space.png        -- bar chart of state-space outputs per fixture
    evaluation/figures/fig4_pipeline_latency.png   -- bar chart of wall-clock time per fixture
    evaluation/figures/metrics.json                -- machine-readable metrics (manuscript source of truth)
    evaluation/figures/metrics_table.md            -- markdown table mirroring the manuscript

Run from the ``projects/cogant/`` directory::

    python evaluation/figures/generate_figures.py

The script is deterministic modulo wall-clock time; everything else (node /
edge / mapping counts, GNN section counts, validator scores) is a pure
function of the fixture and the installed COGANT version.
"""

from __future__ import annotations

import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

THIS_FILE = Path(__file__).resolve()
FIGURES_DIR = THIS_FILE.parent
# …/cogant/cogant — directory that contains ``py/``, ``examples/``, ``evaluation/``
COGANT_ROOT = THIS_FILE.parent.parent.parent
PY_ROOT = COGANT_ROOT / "py"
EXAMPLES_ROOT = COGANT_ROOT / "examples"

sys.path.insert(0, str(PY_ROOT))
sys.path.insert(0, str(FIGURES_DIR))

# Quiet the pipeline so the script's own output is the headline.
logging.basicConfig(level=logging.ERROR)
for name in list(logging.Logger.manager.loggerDict):
    logging.getLogger(name).setLevel(logging.ERROR)

from pipeline_api_metrics import run_orchestration_pipeline_metrics  # noqa: E402

import cogant as _cogant_pkg  # noqa: E402

# Color-blind-safe categorical palette used across all manuscript figures.
PALETTE = {
    "blue": "#4C72B0",
    "orange": "#DD8452",
    "green": "#55A868",
    "red": "#C44E52",
    "purple": "#8172B3",
    "gray": "#6B7280",
}

# ---------------------------------------------------------------------------
# Fixture inventory
# ---------------------------------------------------------------------------

FIXTURES: list[tuple[str, Path, str]] = [
    ("calculator", EXAMPLES_ROOT / "control_positive" / "calculator", "control_positive"),
    (
        "event_pipeline",
        EXAMPLES_ROOT / "control_positive" / "event_pipeline",
        "control_positive",
    ),
    ("flask_mini", EXAMPLES_ROOT / "control_positive" / "flask_mini", "control_positive"),
    ("flask_app", EXAMPLES_ROOT / "real_world" / "flask_app", "real_world"),
    ("requests_lib", EXAMPLES_ROOT / "real_world" / "requests_lib", "real_world"),
    ("json_stdlib", EXAMPLES_ROOT / "real_world" / "json_stdlib", "real_world"),
]


# ---------------------------------------------------------------------------
# Pipeline execution helpers
# ---------------------------------------------------------------------------


def _count_source(repo: Path) -> tuple[int, int]:
    """Count ``.py`` files and non-empty lines under ``repo``.

    Skips ``__pycache__`` directories and tolerates per-file read errors.
    """
    files = [f for f in repo.rglob("*.py") if "__pycache__" not in f.parts]
    loc = 0
    for f in files:
        try:
            with open(f, encoding="utf-8", errors="ignore") as fh:
                loc += sum(1 for _ in fh)
        except OSError:
            # Unreadable file (permissions, broken symlink); skip its lines.
            pass
    return len(files), loc


def _run_pipeline(repo: Path) -> tuple[dict[str, Any], float, bool]:
    """Run the API orchestration pipeline once; return (metrics, elapsed, ok)."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        return run_orchestration_pipeline_metrics(repo, out)


def run_all() -> dict[str, dict[str, Any]]:
    """Run every fixture and collect metrics.

    Fixtures whose ``repo`` path does not exist are skipped with a notice;
    a single fixture failure is captured in the returned dict under the
    ``error`` key so the rest of the suite still produces partial output.
    """
    results: dict[str, dict[str, Any]] = {}
    for name, repo, group in FIXTURES:
        if not repo.exists():
            print(f"[SKIP] {name}: {repo} does not exist")
            continue
        print(f"[RUN ] {name} ({group})", flush=True)
        nfiles, loc = _count_source(repo)
        try:
            metrics, elapsed, ok = _run_pipeline(repo)
        except (OSError, RuntimeError, ValueError, ImportError) as exc:
            print(f"[FAIL] {name}: {type(exc).__name__}: {exc}")
            results[name] = {
                "files": nfiles,
                "loc": loc,
                "elapsed_s": 0.0,
                "group": group,
                "error": f"{type(exc).__name__}: {exc}",
                "ok": False,
            }
            continue
        metrics.update(
            {
                "files": nfiles,
                "loc": loc,
                "elapsed_s": round(elapsed, 2),
                "group": group,
            }
        )
        results[name] = metrics
    return results


# ---------------------------------------------------------------------------
# Figure generation
# ---------------------------------------------------------------------------


def _order(results: dict[str, dict[str, Any]]) -> list[str]:
    """Return fixture names in the order of the FIXTURES table."""
    return [name for name, _, _ in FIXTURES if name in results]


def figure_graph_sizes(results: dict[str, dict[str, Any]]) -> Path:
    """Render Figure 1: per-fixture node and edge counts as paired horizontal bars."""
    names = _order(results)
    nodes = [results[n].get("nodes", 0) for n in names]
    edges = [results[n].get("edges", 0) for n in names]

    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    y = np.arange(len(names))
    height = 0.36
    ax.barh(y - height / 2, nodes, height, label="Nodes", color=PALETTE["blue"])
    ax.barh(y + height / 2, edges, height, label="Edges", color=PALETTE["orange"])
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel("Count")
    ax.set_title(f"Program graph size by fixture (COGANT v{_cogant_pkg.__version__})")
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    ax.legend(loc="lower right")
    xmax = max([*nodes, *edges, 1])
    ax.set_xlim(0, xmax * 1.16)
    for yi, (n, e) in enumerate(zip(nodes, edges, strict=True)):
        ax.text(n + xmax * 0.018, yi - height / 2, str(n), va="center", fontsize=8)
        ax.text(e + xmax * 0.018, yi + height / 2, str(e), va="center", fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    out = FIGURES_DIR / "fig1_graph_sizes.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def figure_node_kinds(results: dict[str, dict[str, Any]]) -> Path:
    """Render Figure 2: horizontal stacked bar of node kinds per fixture."""
    names = _order(results)
    kinds = ["MODULE", "CLASS", "METHOD", "FUNCTION"]
    counts: dict[str, list[int]] = {k: [] for k in kinds}
    for name in names:
        by_kind = results[name].get("nodes_by_kind", {}) or {}
        for k in kinds:
            counts[k].append(by_kind.get(k, 0))

    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    y = np.arange(len(names))
    left = np.zeros(len(names))
    colors = {
        "MODULE": PALETTE["blue"],
        "CLASS": PALETTE["orange"],
        "METHOD": PALETTE["green"],
        "FUNCTION": PALETTE["red"],
    }
    for k in kinds:
        vals = np.array(counts[k], dtype=float)
        ax.barh(y, vals, left=left, label=k, color=colors[k])
        for yi, value, start in zip(y, vals, left, strict=True):
            if value >= 5:
                ax.text(
                    start + value / 2,
                    yi,
                    f"{int(value)}",
                    va="center",
                    ha="center",
                    fontsize=8,
                    color="white",
                    fontweight="bold",
                )
        left += vals
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel("Node count")
    ax.set_title("Node kind distribution by fixture")
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    ax.legend(loc="lower right", ncol=2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    out = FIGURES_DIR / "fig2_node_kinds.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def figure_state_space(results: dict[str, dict[str, Any]]) -> Path:
    """Render Figure 3: grouped horizontal bars for state-space output counts."""
    names = _order(results)
    fields = ["state_variables", "observations", "actions", "transitions"]
    labels = ["State vars", "Observations", "Actions", "Transitions"]

    fig, ax = plt.subplots(figsize=(10, 5.6))
    y = np.arange(len(names))
    height = 0.18
    colors = [PALETTE["blue"], PALETTE["orange"], PALETTE["green"], PALETTE["purple"]]
    xmax = max([results[n].get(f, 0) for n in names for f in fields] + [1])
    for i, (f, lbl) in enumerate(zip(fields, labels, strict=True)):
        vals = [results[n].get(f, 0) for n in names]
        offset = (i - 1.5) * height
        ax.barh(y + offset, vals, height, label=lbl, color=colors[i])
        for yi, value in zip(y, vals, strict=True):
            if value:
                ax.text(value + xmax * 0.018, yi + offset, str(value), va="center", fontsize=8)
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel("Count")
    ax.set_title("State-space compilation outputs per fixture")
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    ax.set_xlim(0, xmax * 1.18)
    ax.legend(loc="lower right", ncol=2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    out = FIGURES_DIR / "fig3_state_space.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def figure_pipeline_latency(results: dict[str, dict[str, Any]]) -> Path:
    """Render Figure 4: per-fixture wall-clock latency as directly labelled bars."""
    names = _order(results)
    elapsed = [results[n].get("elapsed_s", 0) for n in names]
    colors = [
        PALETTE["blue"] if results[n].get("group") == "control_positive" else PALETTE["orange"]
        for n in names
    ]

    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    y = np.arange(len(names))
    ax.barh(y, elapsed, color=colors)
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel("Wall-clock seconds")
    ax.set_title("End-to-end pipeline latency (Python fallback, no Rust)")
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    xmax = max(elapsed + [1])
    ax.set_xlim(0, xmax * 1.16)
    for yi, e in zip(y, elapsed, strict=True):
        ax.text(e + xmax * 0.018, yi, f"{e:.2f}s", va="center", fontsize=8)
    # Legend
    from matplotlib.patches import Patch

    legend = [
        Patch(facecolor=PALETTE["blue"], label="control_positive"),
        Patch(facecolor=PALETTE["orange"], label="real_world"),
    ]
    ax.legend(handles=legend, loc="lower right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    out = FIGURES_DIR / "fig4_pipeline_latency.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


# ---------------------------------------------------------------------------
# Markdown table + JSON dump
# ---------------------------------------------------------------------------


def write_metrics_json(results: dict[str, dict[str, Any]]) -> Path:
    """Persist the full metrics dict to ``evaluation/figures/metrics.json``."""
    out = FIGURES_DIR / "metrics.json"
    out.write_text(json.dumps(results, indent=2, sort_keys=True, default=str))
    return out


def write_metrics_table(results: dict[str, dict[str, Any]]) -> Path:
    """Write a Markdown table mirroring the manuscript metrics table."""
    names = _order(results)
    lines = [
        "# Generated metrics (do not edit by hand — re-run generate_figures.py)",
        "",
        "| Fixture | Files | LOC | Nodes | Edges | Mappings | State vars | Obs | Actions | Transitions | GNN sections | GNN score | Elapsed (s) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for n in names:
        r = results[n]
        lines.append(
            "| `{name}` | {files} | {loc} | {nodes} | {edges} | {mappings} | {state_vars} | {obs} | {actions} | {trans} | {gnn_sec} | {gnn_score} | {elapsed} |".format(
                name=n,
                files=r.get("files", "-"),
                loc=r.get("loc", "-"),
                nodes=r.get("nodes", "-"),
                edges=r.get("edges", "-"),
                mappings=r.get("mappings_total", "-"),
                state_vars=r.get("state_variables", "-"),
                obs=r.get("observations", "-"),
                actions=r.get("actions", "-"),
                trans=r.get("transitions", "-"),
                gnn_sec=r.get("gnn_sections", "-"),
                gnn_score=r.get("gnn_score", "-"),
                elapsed=r.get("elapsed_s", "-"),
            )
        )
    out = FIGURES_DIR / "metrics_table.md"
    out.write_text("\n".join(lines) + "\n")
    return out


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    """Entry point: regenerate all figures and metrics from a fresh pipeline run."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Figures directory: {FIGURES_DIR}")
    print(f"[INFO] COGANT package root: {COGANT_ROOT}")
    print(f"[INFO] Fixtures: {len(FIXTURES)}")

    results = run_all()

    # Persist metrics first so even a figure failure leaves a trail.
    metrics_path = write_metrics_json(results)
    print(f"[WRITE] {metrics_path.relative_to(COGANT_ROOT)}")

    table_path = write_metrics_table(results)
    print(f"[WRITE] {table_path.relative_to(COGANT_ROOT)}")

    for fn in (
        figure_graph_sizes,
        figure_node_kinds,
        figure_state_space,
        figure_pipeline_latency,
    ):
        path = fn(results)
        print(f"[WRITE] {path.relative_to(COGANT_ROOT)}")

    print("[DONE] All figures regenerated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
