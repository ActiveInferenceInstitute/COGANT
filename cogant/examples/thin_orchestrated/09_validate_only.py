#!/usr/bin/env python3
"""Thin example: GNN package validation only.

Validates an existing GNN package against the 18 canonical sections,
checks required files, manifest checksums, JSON validity, and provenance
coverage. Reports a score 0-100.

If no GNN package exists at the target output directory, the script
builds one first.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/09_validate_only.py
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


def main() -> int:
    args = parse_args("validate")
    configure_logging()
    banner("Stage 9: GNN package validation")

    target = args.target.expanduser().resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    package_dir = args.output_dir / "gnn_package"

    if not package_dir.exists():
        print("  no existing package found, building one first...")
        _build_package(target, package_dir)

    validator = GNNValidator()
    result = validator.validate_package(str(package_dir))

    status = "PASSED" if result.valid else "FAILED"
    print(f"  package dir   : {package_dir}")
    print(f"  status        : {status}")
    print(f"  score         : {result.score:.1f}%")
    print(f"  errors        : {len(result.errors)}")
    print(f"  warnings      : {len(result.warnings)}")

    if result.errors:
        print("\n  errors (first 10):")
        for err in result.errors[:10]:
            print(f"    - {err}")

    if result.warnings:
        print("\n  warnings (first 10):")
        for warn in result.warnings[:10]:
            print(f"    - {warn}")

    print("\n  canonical 18 sections expected:")
    for sec in validator.CANONICAL_SECTIONS:
        print(f"    - {sec}")

    out = args.output_dir / "validation_report.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, indent=2, default=str)
    print(f"\n  wrote: {out}")

    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
