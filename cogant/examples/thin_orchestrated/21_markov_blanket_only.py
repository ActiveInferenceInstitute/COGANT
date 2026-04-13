#!/usr/bin/env python3
"""Thin example: Markov blanket extraction only.

Builds a rich ``ProgramGraph`` and runs
:class:`cogant.markov.MarkovBlanketExtractor` with each seed strategy
(``auto``, ``module``, ``kind``, ``explicit``). For each extraction it
reports the (μ, s, a, η) partition sizes, boundary ratio, and the
metadata that explains *why* the auto-tier chose what it did. It also
writes the JSON-serializable blanket, the collapsed Mermaid aggregate
view, and the detailed role-colored Mermaid subgraph to the output
directory so downstream visualization surfaces can render them.

Active Inference role legend:

* **internal (μ)** — the system of interest; no direct external coupling
* **sensory (s)** — internal boundary nodes that receive from external
* **active (a)**  — internal boundary nodes that emit to external
* **external (η)** — everything not in μ ∪ s ∪ a

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/21_markov_blanket_only.py
    PYTHONPATH=py python examples/thin_orchestrated/21_markov_blanket_only.py \\
        --target examples/control_positive/calculator
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, build_rich_graph, configure_logging, parse_args  # noqa: E402

from cogant.markov import MarkovBlanketExtractor, serialize_blanket  # noqa: E402
from cogant.markov.network import build_blanket_network  # noqa: E402
from cogant.schemas.core import NodeKind  # noqa: E402
from cogant.viz.boundary import BoundaryMapper  # noqa: E402


ROLE_ORDER = ("internal", "sensory", "active", "external")


def _role_counts(blanket) -> dict[str, int]:
    counts = {r: 0 for r in ROLE_ORDER}
    for role in blanket.roles.values():
        key = role.value if hasattr(role, "value") else str(role)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _print_partition(label: str, blanket) -> None:
    counts = _role_counts(blanket)
    total = sum(counts.values())
    boundary = counts["sensory"] + counts["active"]
    internal_plus_boundary = counts["internal"] + boundary
    ratio = (boundary / internal_plus_boundary) if internal_plus_boundary else 0.0
    print(f"\n  {label}")
    print(
        "    internal={0[internal]:>3}  sensory={0[sensory]:>3}  "
        "active={0[active]:>3}  external={0[external]:>3}  total={1}".format(counts, total)
    )
    print(f"    boundary ratio (s+a)/(μ+s+a) = {ratio:.3f}")
    meta = dict(blanket.metadata or {})
    if "auto_tier" in meta:
        print(f"    auto_tier   : {meta['auto_tier']}")
    if "auto_reason" in meta:
        print(f"    auto_reason : {meta['auto_reason']}")
    if meta.get("strategy"):
        print(f"    strategy    : {meta['strategy']}")


def main() -> int:
    args = parse_args("markov_blanket")
    configure_logging()
    banner("Stage 21: markov blanket extraction")

    target = args.target.expanduser().resolve()
    pg = build_rich_graph(target)
    print(f"  repo uri    : {pg.metadata.repo_uri}")
    print(f"  total nodes : {pg.node_count()}")
    print(f"  total edges : {pg.edge_count()}")

    extractor = MarkovBlanketExtractor(pg)

    # Strategy 1 — auto
    auto_blanket = extractor.extract(strategy="auto")
    _print_partition("auto strategy", auto_blanket)

    # Strategy 2 — kind (classes as seeds)
    kind_blanket = extractor.extract(strategy="kind", kinds=[NodeKind.CLASS])
    _print_partition("kind=CLASS strategy", kind_blanket)

    # Strategy 3 — module (first module name we find)
    modules = pg.get_nodes_by_kind(NodeKind.MODULE)
    if modules:
        target_module = modules[0].name or modules[0].qualified_name
        module_blanket = extractor.extract(
            strategy="module", module_names=[target_module]
        )
        _print_partition(f"module={target_module!r} strategy", module_blanket)
    else:
        module_blanket = None

    # Strategy 4 — explicit (top node ids from the auto seed set, if any)
    auto_internal_ids = list(sorted(auto_blanket.internal_ids))[:3]
    if auto_internal_ids:
        explicit_blanket = extractor.extract(strategy="explicit", seeds=auto_internal_ids)
        _print_partition("explicit (first 3 internal nodes)", explicit_blanket)
    else:
        explicit_blanket = None

    # Persist the auto blanket + both mermaid views + a collapsed JSON
    args.output_dir.mkdir(parents=True, exist_ok=True)
    blanket_path = args.output_dir / "markov_blanket.json"
    with open(blanket_path, "w", encoding="utf-8") as f:
        json.dump(serialize_blanket(auto_blanket, pg), f, indent=2, default=str)

    network = build_blanket_network(pg, auto_blanket)
    network_path = args.output_dir / "markov_blanket_network.json"
    with open(network_path, "w", encoding="utf-8") as f:
        json.dump(network.to_dict(), f, indent=2)

    mapper = BoundaryMapper()
    collapsed_path = args.output_dir / "markov_blanket_collapsed.mmd"
    collapsed_path.write_text(
        mapper.markov_blanket_collapsed_mermaid(
            pg, blanket=auto_blanket, strategy="auto"
        ),
        encoding="utf-8",
    )
    detailed_path = args.output_dir / "markov_blanket_detail.mmd"
    detailed_path.write_text(
        mapper.markov_blanket_detailed_mermaid(
            pg, blanket=auto_blanket, strategy="auto", max_per_role=12
        ),
        encoding="utf-8",
    )

    print("\n  artifacts:")
    for p in (blanket_path, network_path, collapsed_path, detailed_path):
        print(f"    {p}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
