"""Reorganize flat COGANT example run directories into a stable layout.

Layout per example (e.g. ``calculator`` under ``examples/control_positive/``)::

    data/       — JSON graph exports and validation
    diagrams/   — Mermaid sources and Graphviz ``.dot``
    figures/    — Raster (``*.png``) and vector (``*.svg``) renders. Filled
                  via the explicit ``_DEST`` map for canonical filenames
                  emitted by ``render_all_pngs`` and a ``*.png``/``*.svg``
                  fallback so future renderers do not regress.
    site/       — Static HTML (index, distribution views)
    reports/    — Markdown summaries; ``model.gnn.md`` is copied here from
                  ``gnn_package/`` and a ``run_summary.md`` is generated per
                  target so the directory always exists.

``site/index.html`` file lists are rewritten to use ``../data/…``, etc.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Filenames -> subdirectory under the example run root.
#
# The PNG entries below mirror the canonical filenames written by
# ``cogant.viz.render_all_pngs``; an additional ``*.png``/``*.svg``
# fallback in ``_dest_for_file`` keeps the layout robust if new renderers
# emit additional rasters.
_DEST: dict[str, str] = {
    "adjacency_matrix.json": "data",
    "semantic_mappings.json": "data",
    "program_graph.json": "data",
    "typed_graph.json": "data",
    "model.gnn.json": "data",
    "cytoscape.json": "data",
    "validation_report.json": "data",
    "state_space.json": "data",
    "process_model.json": "data",
    "gnn_model.json": "data",
    "rule_evidence_trace.json": "data",
    "inference_trace.json": "data",
    "bundle.json": "data",
    "syntax_tree.json": "data",
    "simulation_trace.json": "data",
    "model.gnn.md": "reports",
    "summary.md": "reports",
    "graph.dot": "diagrams",
    "index.html": "site",
    "node_distribution.html": "site",
    "edge_distribution.html": "site",
    "confidence_heatmap.html": "site",
    "inspection_dashboard.html": "site",
    "connections_matrix.png": "figures",
    "graphical_abstract.png": "figures",
    "graphical_abstract.svg": "figures",
    "markov_blanket.png": "figures",
    "model_gnn.png": "figures",
    "model_gnn_mosaic.png": "figures",
    "model_gnn_p2.png": "figures",
    "model_gnn_p3.png": "figures",
    "model_gnn_p4.png": "figures",
    "model_gnn_p5.png": "figures",
    "model_gnn_p6.png": "figures",
    "model_gnn_p7.png": "figures",
    "model_gnn_p8.png": "figures",
    "process_gantt.png": "figures",
    "program_graph.png": "figures",
    "state_space_factor.png": "figures",
    "summary_cover.png": "figures",
}

_MERMAID = ".mermaid"


def _dest_for_file(name: str) -> str | None:
    if name in _DEST:
        return _DEST[name]
    if name.endswith(_MERMAID):
        return "diagrams"
    if name.endswith(".png") or name.endswith(".svg"):
        return "figures"
    return None


def _rewrite_index_html(site_index: Path) -> None:
    text = site_index.read_text(encoding="utf-8")

    def repl(m: re.Match[str]) -> str:
        """Regex callback: rewrite ``href="file.ext"`` for one match."""
        q = m.group(1)
        fname = m.group(2)
        if fname in ("", ".", "..") or "/" in fname or fname.startswith("http"):
            return m.group(0)
        dest = _dest_for_file(fname)
        if dest is None:
            return m.group(0)
        if fname == "index.html":
            return f"href={q}{fname}{q}"
        if dest == "site":
            return f"href={q}{fname}{q}"
        return f"href={q}../{dest}/{fname}{q}"

    new_text = re.sub(r"href=(['\"])([^'\"]+)\1", repl, text)
    if new_text != text:
        site_index.write_text(new_text, encoding="utf-8")
        logger.info("Patched links in %s", site_index)


def organize_run_dir(flat_dir: Path, *, dry_run: bool = False) -> Path | None:
    """Move artifacts from a flat run directory into ``data/``, ``diagrams/``, etc."""
    flat_dir = flat_dir.resolve()
    if not flat_dir.is_dir():
        logger.error("Not a directory: %s", flat_dir)
        return None
    if (flat_dir / "data" / "program_graph.json").exists() and (
        flat_dir / "site" / "index.html"
    ).exists():
        logger.info("Already organized: %s", flat_dir)
        if not dry_run:
            (flat_dir / "figures").mkdir(exist_ok=True)
            _populate_reports(flat_dir)
        return flat_dir

    plan: list[tuple[Path, Path]] = []
    for p in sorted(flat_dir.iterdir()):
        if p.name.startswith(".") or p.is_dir():
            continue
        dest_name = _dest_for_file(p.name)
        if dest_name is None:
            logger.warning("Skipping unknown file: %s", p.name)
            continue
        target = flat_dir / dest_name / p.name
        plan.append((p, target))

    if dry_run:
        for src, dst in plan:
            logger.info("DRY: %s -> %s", src.name, dst)
        return flat_dir

    for _, dst in plan:
        dst.parent.mkdir(parents=True, exist_ok=True)

    for src, dst in plan:
        if dst.exists():
            logger.warning("Overwrite: %s", dst)
            dst.unlink()
        shutil.move(str(src), str(dst))
        logger.info("Moved %s -> %s/", src.name, dst.parent.name)

    site_index = flat_dir / "site" / "index.html"
    if site_index.is_file():
        _rewrite_index_html(site_index)
    (flat_dir / "figures").mkdir(exist_ok=True)
    _populate_reports(flat_dir)
    return flat_dir


def _populate_reports(run_dir: Path) -> None:
    """Ensure ``reports/`` exists with the human-readable GNN spec and a summary.

    ``model.gnn.md`` is *copied* (not moved) from ``gnn_package/`` so the
    package directory remains self-contained for downstream upstream-GNN
    consumers, while ``reports/`` is also a documented entry point.
    """
    reports = run_dir / "reports"
    reports.mkdir(exist_ok=True)

    gnn_md = run_dir / "gnn_package" / "model.gnn.md"
    if gnn_md.is_file():
        try:
            shutil.copy2(str(gnn_md), str(reports / "model.gnn.md"))
        except OSError as exc:
            logger.warning("could not copy %s -> reports/: %s", gnn_md, exc)

    summary_path = reports / "run_summary.md"
    try:
        summary_path.write_text(_render_run_summary(run_dir), encoding="utf-8")
    except OSError as exc:
        logger.warning("could not write %s: %s", summary_path, exc)


def _render_run_summary(run_dir: Path) -> str:
    """Render a short markdown summary of one run directory."""
    bundle_path = run_dir / "data" / "bundle.json"
    bundle: dict[str, object] = {}
    if bundle_path.is_file():
        try:
            parsed = json.loads(bundle_path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                bundle = parsed
        except json.JSONDecodeError:
            bundle = {}

    target = str(bundle.get("target", run_dir.name))
    raw_stages = bundle.get("stage_results")
    stage_results: dict[str, object] = raw_stages if isinstance(raw_stages, dict) else {}
    raw_errors = bundle.get("errors")
    errors: list[object] = raw_errors if isinstance(raw_errors, list) else []
    raw_metadata = bundle.get("metadata")
    metadata: dict[str, object] = raw_metadata if isinstance(raw_metadata, dict) else {}

    lines: list[str] = []
    lines.append(f"# Run summary — {run_dir.name}")
    lines.append("")
    lines.append(f"- target: `{target}`")
    if "wall_time_ms" in metadata:
        lines.append(f"- wall_time_ms: {metadata.get('wall_time_ms')}")
    lines.append(f"- stages_run: {len(stage_results)}")
    lines.append(f"- errors: {len(errors)}")
    lines.append("")

    lines.append("## Stages")
    lines.append("")
    lines.append("| stage | summary |")
    lines.append("|---|---|")
    for name, payload in stage_results.items():
        summary = ""
        if isinstance(payload, dict):
            for key in ("node_count", "edge_count", "mapping_count", "states", "score"):
                if key in payload:
                    val = payload[key]
                    if isinstance(val, list):
                        summary = f"{key}={len(val)}"
                    else:
                        summary = f"{key}={val}"
                    break
        lines.append(f"| {name} | {summary or '-'} |")
    lines.append("")

    lines.append("## Key artifacts")
    lines.append("")
    candidates = [
        ("bundle JSON", run_dir / "data" / "bundle.json"),
        ("static site", run_dir / "site" / "index.html"),
        ("figures dir", run_dir / "figures"),
        ("GNN package", run_dir / "gnn_package" / "manifest.json"),
        ("forward gnn", run_dir / "roundtrip" / "forward" / "model.gnn.md"),
        ("graph metrics", run_dir / "analysis" / "graph_metrics.json"),
    ]
    for label, p in candidates:
        if p.exists():
            try:
                rel = p.relative_to(run_dir)
            except ValueError:
                rel = p
            lines.append(f"- {label}: `{rel}`")
    lines.append("")
    return "\n".join(lines)


def migrate_output_tree(
    output_root: Path,
    *,
    suite: str = "control_positive",
    examples: list[str] | None = None,
    dry_run: bool = False,
) -> int:
    """Move ``output/<name>/`` to ``output/examples/<suite>/<name>/`` and organize."""
    output_root = output_root.resolve()
    ex_root = output_root / "examples" / suite
    names = examples or ["calculator", "event_pipeline", "flask_mini"]
    count = 0
    for name in names:
        flat = output_root / name
        if not flat.is_dir():
            logger.warning("Skip missing: %s", flat)
            continue
        target = ex_root / name
        if dry_run:
            logger.info("DRY: would move %s -> %s", flat, target)
        else:
            ex_root.mkdir(parents=True, exist_ok=True)
            if target.exists():
                logger.warning("Target exists, skipping move: %s", target)
            else:
                shutil.move(str(flat), str(target))
                logger.info("Moved tree %s -> %s", name, target.relative_to(output_root))
        root = target if target.exists() else flat
        has_pg = (root / "program_graph.json").exists() or (
            root / "data" / "program_graph.json"
        ).exists()
        if root.is_dir() and has_pg:
            organize_run_dir(root, dry_run=dry_run)
            count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: organize COGANT example output directories into data/diagrams/site/reports/figures."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(description="Organize COGANT example output directories.")
    p.add_argument(
        "output_root",
        type=Path,
        nargs="?",
        default=Path("output"),
        help="COGANT output root (default: ./output)",
    )
    p.add_argument("--suite", default="control_positive", help="Suite name under examples/")
    p.add_argument(
        "--examples",
        nargs="*",
        default=["calculator", "event_pipeline", "flask_mini"],
        help="Example directory names to migrate",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--organize-only", type=Path, help="Only organize this run dir (no tree move)")
    args = p.parse_args(argv)

    if args.organize_only:
        organize_run_dir(args.organize_only, dry_run=args.dry_run)
        return 0

    n = migrate_output_tree(
        args.output_root,
        suite=args.suite,
        examples=list(args.examples) if args.examples else None,
        dry_run=args.dry_run,
    )
    logger.info("Processed %s example(s).", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
