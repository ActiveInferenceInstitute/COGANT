#!/usr/bin/env python3
"""Thin example: GNN package export only.

Builds a complete GNN (Generalized Notation Notation) package from a
program graph + state-space model + process model + semantic mappings.

The package contains the canonical 18-section ``model.gnn.md`` file plus
machine-readable JSON for every section, ontology mapping, provenance,
diagrams, and visualizations.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/08_gnn_export_only.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, build_rich_graph, configure_logging, parse_args  # noqa: E402

from cogant.gnn.package import GNNPackageBuilder  # noqa: E402
from cogant.process.extractor import ProcessExtractor  # noqa: E402
from cogant.statespace.compiler import StateSpaceCompiler  # noqa: E402
from cogant.translate.engine import TranslationEngine  # noqa: E402
from cogant.translate.rules import (  # noqa: E402
    MutatingSubsystemRule,
    OrchestratorRule,
    ReadOnlyInputRule,
    TestAssertionRule,
)


def main() -> int:
    args = parse_args("gnn_export")
    configure_logging()
    banner("Stage 8: GNN package export")

    target = args.target.expanduser().resolve()
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

    args.output_dir.mkdir(parents=True, exist_ok=True)
    package_dir = args.output_dir / "gnn_package"

    builder = GNNPackageBuilder(
        graph=pg,
        state_space=state_space,
        process_model=process_model,
        mappings=mappings,
        config={"repo_name": target.name},
    )
    manifest = builder.build(str(package_dir))

    print(f"  package version : {manifest.get('package_version', 'unknown')}")
    print(f"  package dir     : {package_dir}")
    print(f"  files written   : {len(manifest.get('checksums', {}))}")

    print("\n  required files present:")
    for required in builder.REQUIRED_FILES:
        present = (package_dir / required).exists()
        marker = "[ok]" if present else "[MISSING]"
        print(f"    {marker} {required}")

    md_path = package_dir / "model.gnn.md"
    if md_path.exists():
        text = md_path.read_text(encoding="utf-8")
        section_count = text.count("\n# ") + (1 if text.startswith("# ") else 0)
        print(f"\n  model.gnn.md sections : {section_count}")
        print(f"  model.gnn.md size     : {len(text)} bytes")

    manifest_path = args.output_dir / "build_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)
    print(f"\n  wrote: {manifest_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
