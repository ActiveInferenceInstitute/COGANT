#!/usr/bin/env python3
"""Thin example: graph stage only.

Builds a typed ``ProgramGraph`` with both nodes and edges
(containment, imports, inheritance, dataflow) and prints kind-grouped
counts.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/04_graph_only.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, build_rich_graph, configure_logging, parse_args  # noqa: E402

from cogant.api.orchestration import program_graph_to_dict  # noqa: E402


def main() -> int:
    args = parse_args("graph")
    configure_logging()
    banner("Stage 4: graph")

    target = args.target.expanduser().resolve()
    pg = build_rich_graph(target)

    print(f"  repo uri    : {pg.metadata.repo_uri}")
    print(f"  languages   : {sorted(pg.metadata.languages)}")
    print(f"  total nodes : {pg.node_count()}")
    print(f"  total edges : {pg.edge_count()}")

    node_kinds = Counter(
        n.kind.value if hasattr(n.kind, "value") else str(n.kind) for n in pg.nodes.values()
    )
    edge_kinds = Counter(
        e.kind.value if hasattr(e.kind, "value") else str(e.kind) for e in pg.edges.values()
    )

    print("\n  nodes by kind:")
    for kind, count in sorted(node_kinds.items(), key=lambda kv: -kv[1]):
        print(f"    {kind:<24} {count}")

    print("\n  edges by kind:")
    for kind, count in sorted(edge_kinds.items(), key=lambda kv: -kv[1]):
        print(f"    {kind:<24} {count}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out = args.output_dir / "program_graph.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(program_graph_to_dict(pg), f, indent=2, default=str)
    print(f"\n  wrote: {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
