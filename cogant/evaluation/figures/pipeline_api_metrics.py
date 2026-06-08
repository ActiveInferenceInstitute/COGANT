"""Collect fixture metrics via :mod:`cogant.api.orchestration` (same path as :mod:`benchmarks.bench_suite`).

``examples/orchestrate_roundtrip.py`` builds a *richer* demo graph in its own JSON
shape; node/edge/mapping counts from that path can diverge from the default API
bundle. This module is the single source for :data:`metrics.json` graph stats so
manuscript Table 4--7, figures, and benchmark Table 11 stay consistent.
Mapping totals match :mod:`benchmarks.bench_suite` for the same fixture because
:meth:`cogant.translate.engine.TranslationEngine._resolve_conflicts` applies
**sorted** iteration over colliding pair keys.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _count_nodes_by_kind(graph: Any) -> dict[str, int]:
    """Return a histogram of node ``kind.name`` values for ``graph``."""
    out: dict[str, int] = {}
    for _nid, n in graph.nodes.items():
        k = n.kind.name if hasattr(n.kind, "name") else str(n.kind)
        out[k] = out.get(k, 0) + 1
    return out


def _count_edges_by_kind(graph: Any) -> dict[str, int]:
    """Return a histogram of edge ``kind.name`` values for ``graph``."""
    out: dict[str, int] = {}
    for _eid, e in graph.edges.items():
        k = e.kind.name if hasattr(e.kind, "name") else str(e.kind)
        out[k] = out.get(k, 0) + 1
    return out


def _transitions_count(state_file: dict[str, Any]) -> int:
    """Extract the transition count from a serialized state-space file.

    Tolerates supported schema variants (``transitions: {transition_count: int}``,
    ``transitions: {structure: [..]}``) and a flat ``transitions: [..]`` list.
    """
    t = state_file.get("transitions", {})
    if t is None:
        return 0
    if isinstance(t, dict):
        if "transition_count" in t:
            return int(t["transition_count"])
        st = t.get("structure")
        if isinstance(st, list):
            return len(st)
        if isinstance(st, dict) and "count" in st:
            return int(st["count"])
    if isinstance(t, list):
        return len(t)
    return 0


def run_orchestration_pipeline_metrics(
    repo: Path, output_dir: Path
) -> tuple[dict[str, Any], float, bool]:
    """Run ingest..validate through the public API; write export under *output_dir*.

    Returns:
        (metrics_dict, wall_clock_seconds, success_flag)
    """
    import time

    from cogant.api import orchestration
    from cogant.api.bundle import ArtifactKey, Bundle

    target = str(repo.resolve())
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()

    bundle = Bundle(target=target)
    orchestration.run_ingest(target, bundle)
    orchestration.run_static(bundle)
    orchestration.run_normalize(bundle)
    orchestration.run_graph(bundle, target)
    orchestration.run_translate(bundle)
    orchestration.run_statespace(bundle, target)
    # Match benchmarks/bench_suite.py: graph + mapping sizes are read before process/export.
    sm = bundle.artifacts.get(ArtifactKey.SEMANTIC_MAPPINGS) or {}
    mappings_for_metrics = len(sm) if isinstance(sm, dict) else 0
    orchestration.run_process(bundle, target)
    orchestration.run_export(bundle, str(output_dir))
    val = orchestration.run_validate(bundle)
    elapsed = time.perf_counter() - t0

    gnnv_ok = (val.get("gnn_validation") or {}).get("valid")
    ok = gnnv_ok is not False

    metrics: dict[str, Any] = {"ok": ok}
    pg = bundle.artifacts.get(ArtifactKey.PROGRAM_GRAPH)
    if pg is not None:
        metrics["nodes"] = pg.node_count()
        metrics["edges"] = pg.edge_count()
        metrics["nodes_by_kind"] = _count_nodes_by_kind(pg)
        metrics["edges_by_kind"] = _count_edges_by_kind(pg)
    else:
        metrics["nodes"] = 0
        metrics["edges"] = 0
        metrics["nodes_by_kind"] = {}
        metrics["edges_by_kind"] = {}

    metrics["mappings_total"] = mappings_for_metrics

    gnn_dir = output_dir / "gnn_package"
    md = gnn_dir / "model.gnn.md"
    if md.exists():
        text = md.read_text(encoding="utf-8", errors="replace")
        metrics["gnn_md_bytes"] = len(text)
        metrics["gnn_sections"] = sum(1 for line in text.splitlines() if line.startswith("## "))

    gnnv = (val or {}).get("gnn_validation") or {}
    if gnnv:
        metrics["gnn_valid"] = gnnv.get("valid")
        metrics["gnn_score"] = gnnv.get("score")
        metrics["gnn_errors"] = gnnv.get("error_count", 0)
        metrics["gnn_warnings"] = gnnv.get("warning_count", 0)
    else:
        metrics["gnn_valid"] = None
        metrics["gnn_score"] = None
        metrics["gnn_errors"] = 0
        metrics["gnn_warnings"] = 0

    ss_p = gnn_dir / "state_space.json"
    if ss_p.exists():
        try:
            s = json.loads(ss_p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("state_space.json read failed: %s", e)
            s = {}
        metrics["state_variables"] = len(s.get("variables", []) or [])
        metrics["observations"] = len(s.get("observations", []) or [])
        metrics["transitions"] = _transitions_count(s)
    else:
        metrics["state_variables"] = 0
        metrics["observations"] = 0
        metrics["transitions"] = 0

    ac_p = gnn_dir / "actions.json"
    if ac_p.exists():
        try:
            a = json.loads(ac_p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("actions.json read failed: %s", e)
            a = {}
        metrics["actions"] = a.get("count", len(a.get("actions", []) or []))
        pol = a.get("policies", []) or []
        metrics["policies"] = len(pol) if isinstance(pol, list) else 0
    else:
        metrics["actions"] = 0
        metrics["policies"] = 0

    if gnn_dir.exists() and gnn_dir.is_dir():
        metrics["gnn_package_files"] = len([f for f in gnn_dir.iterdir() if f.is_file()])
    else:
        metrics["gnn_package_files"] = 0

    metrics["ok"] = ok
    return metrics, elapsed, ok
