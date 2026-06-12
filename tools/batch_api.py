"""Compatibility wrapper for package-level COGANT analysis command APIs.

``run_all.py`` historically used this script before several CLI commands
shared package-level implementations. The implementations now live in
``cogant.api.analysis_commands`` and the public CLI calls those same APIs.
This wrapper preserves the subprocess contract for existing batch configs.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from cogant.api.analysis_commands import (
    run_graph_analysis,
    run_multi_export,
    run_static_analysis,
    run_visualize,
)
from cogant.viz.inspection_dashboard import write_inspection_artifacts


def _print_path(path: Path) -> None:
    print(str(path.expanduser().resolve()))


def _cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ga = sub.add_parser("graph-analysis")
    p_ga.add_argument("--run-dir", type=Path, required=True)
    p_ga.add_argument("--target", type=Path, required=True)

    p_sa = sub.add_parser("static-analysis")
    p_sa.add_argument("--run-dir", type=Path, required=True)
    p_sa.add_argument("--target", type=Path, required=True)

    p_me = sub.add_parser("multi-export")
    p_me.add_argument("--run-dir", type=Path, required=True)
    p_me.add_argument("--bundle", type=Path, required=True)

    p_vz = sub.add_parser("visualize")
    p_vz.add_argument("--run-dir", type=Path, required=True)
    p_vz.add_argument("--target", type=Path, required=True)

    p_insp = sub.add_parser("inspection-artifacts")
    p_insp.add_argument("--run-dir", type=Path, required=True)

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.cmd == "graph-analysis":
        out = args.run_dir / "analysis" / "graph_analysis.json"
        report = run_graph_analysis(args.target, output=out)
        for name in ("metrics", "centrality", "cycles", "hotspots"):
            path = args.run_dir / "analysis" / f"graph_{name}.json"
            path.write_text(json.dumps(report.get(name, {}), indent=2) + "\n", encoding="utf-8")
            _print_path(path)
        _print_path(out)
        return 0
    if args.cmd == "static-analysis":
        out = args.run_dir / "analysis" / "static_report.json"
        run_static_analysis(args.target, output=out)
        _print_path(out)
        return 0
    if args.cmd == "multi-export":
        manifest = run_multi_export(
            args.bundle,
            formats=["json", "jsonlines", "graphml", "parquet", "svg"],
            output_dir=args.run_dir / "exports",
        )
        _print_path(Path(manifest["files"].get("json", args.run_dir / "exports" / "exports_manifest.json")))
        _print_path(args.run_dir / "exports" / "exports_manifest.json")
        return 0
    if args.cmd == "visualize":
        out = args.run_dir / "diagrams" / "dependency_graph.mmd"
        run_visualize(args.target, output=out, fmt="mermaid")
        _print_path(out)
        return 0
    if args.cmd == "inspection-artifacts":
        written = write_inspection_artifacts(args.run_dir)
        for path in written.values():
            _print_path(path)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli())
