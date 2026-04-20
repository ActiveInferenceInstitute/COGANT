#!/usr/bin/env python3
"""Thin example: walk the 19 canonical GNN sections.

Loads an existing GNN package (building one if necessary) and walks
through every section the ``GNNValidator`` expects, printing a one-line
summary of the content and status. This is the fastest way to eyeball
whether a translation run produced a well-formed GNN-compatible bundle.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/17_gnn_sections_walk.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, build_rich_graph, configure_logging, parse_args  # noqa: E402

from cogant.gnn.package import GNNPackageBuilder  # noqa: E402
from cogant.gnn.validator import GNNValidator  # noqa: E402
from cogant.process.extractor import ProcessExtractor  # noqa: E402
from cogant.statespace.compiler import StateSpaceCompiler  # noqa: E402
from cogant.translate.engine import TranslationEngine  # noqa: E402
from cogant.translate.rules import (  # noqa: E402
    MutatingSubsystemRule,
    OrchestratorRule,
    ReadOnlyInputRule,
    TestAssertionRule,
)


def _build_package(target: Path, package_dir: Path) -> None:
    pg = build_rich_graph(target)
    engine = TranslationEngine()
    for rule in (
        ReadOnlyInputRule(),
        MutatingSubsystemRule(),
        OrchestratorRule(),
        TestAssertionRule(),
    ):
        engine.register_rule(rule)
    mappings = {m.id: m for m in engine.translate(pg)}
    state_space = StateSpaceCompiler(pg, schema_name=target.name).compile(mappings)
    process_model = ProcessExtractor(pg, schema_name=target.name).extract()
    GNNPackageBuilder(
        graph=pg,
        state_space=state_space,
        process_model=process_model,
        mappings=mappings,
        config={"repo_name": target.name},
    ).build(str(package_dir))


def _load_section(package_dir: Path, slug: str) -> dict | None:
    """Return a section's JSON content if it exists on disk."""
    # Most sections are their own JSON files; some live inside model.gnn.json.
    candidates = [
        package_dir / f"{slug}.json",
    ]
    # Common aliases used by GNNPackageBuilder
    aliases = {
        "observation_modalities": "observations",
        "actions_policies": "actions_policies",
        "transition_structure": "transitions",
        "likelihood_structure": "likelihoods",
        "preferences_constraints": "preferences_constraints",
        "ontology_mapping": "ontology",
    }
    if slug in aliases:
        candidates.insert(0, package_dir / f"{aliases[slug]}.json")
    for p in candidates:
        if p.exists():
            try:
                with open(p, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                continue
    # Fallback: look inside model.gnn.json
    gnn = package_dir / "model.gnn.json"
    if gnn.exists():
        try:
            with open(gnn, encoding="utf-8") as f:
                data = json.load(f)
            return (data or {}).get(slug) or (data or {}).get("sections", {}).get(slug)
        except Exception:
            pass
    return None


def _summarize(content: object) -> str:
    if content is None:
        return "(missing)"
    if isinstance(content, list):
        return f"list[{len(content)}]"
    if isinstance(content, dict):
        keys = list(content.keys())
        preview = ", ".join(keys[:4]) + ("..." if len(keys) > 4 else "")
        return f"dict[{len(keys)}] {{{preview}}}"
    return f"{type(content).__name__}"


def main() -> int:
    args = parse_args("gnn_sections_walk")
    configure_logging()
    banner("Higher-order: walk the 19 canonical GNN sections")

    target = args.target.expanduser().resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    package_dir = args.output_dir / "gnn_package"
    if not package_dir.exists():
        print("  no GNN package present, building one first...")
        _build_package(target, package_dir)

    validator = GNNValidator()
    result = validator.validate_package(str(package_dir))
    print(f"  package dir : {package_dir}")
    print(f"  validator   : {'PASSED' if result.valid else 'FAILED'} ({result.score:.1f}%)\n")

    rows = []
    for slug in validator.CANONICAL_SECTIONS:
        content = _load_section(package_dir, slug)
        summary = _summarize(content)
        status = "OK" if content is not None else "MISSING"
        print(f"    [{status:<7}] {slug:<28} {summary}")
        rows.append({"section": slug, "status": status, "summary": summary})

    on_disk = sorted(p.name for p in package_dir.iterdir() if p.is_file())
    print(f"\n  on-disk files ({len(on_disk)}):")
    for name in on_disk:
        print(f"    - {name}")

    out = args.output_dir / "sections_walk.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(
            {
                "validator_score": result.score,
                "sections": rows,
                "on_disk_files": on_disk,
            },
            f,
            indent=2,
            default=str,
        )
    print(f"\n  wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
