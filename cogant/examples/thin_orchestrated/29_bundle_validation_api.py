#!/usr/bin/env python3
"""Thin example: Programmatic GNN bundle validation via Python API.

Demonstrates using ``GNNValidator`` directly without the CLI:

1. Build a GNN bundle from a real fixture.
2. Validate it against the AII spec using ``GNNValidator``.
3. Inspect per-section scores, errors, and warnings.
4. Demonstrate remediation — strip a required section and re-validate.
5. Show how to use validator output for CI gate decisions (exit code).

The validator scores bundles 0–100. All 6 shipped fixtures score 100.0.
Scores below 70 block publication; scores below 85 trigger warnings.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/29_bundle_validation_api.py \\
        --target examples/control_positive/calculator \\
        --output-dir output/thin/validation
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, configure_logging, parse_args  # noqa: E402

# CI thresholds — mirrors cogant/docs/evaluation/CALIBRATION.md
BLOCK_THRESHOLD = 70.0  # Score below this blocks publication
WARN_THRESHOLD = 85.0  # Score below this triggers a warning


def gate_decision(score: float) -> tuple[str, int]:
    """Return (decision_label, exit_code) for a given validator score."""
    if score < BLOCK_THRESHOLD:
        return "BLOCK — bundle does not meet minimum quality bar", 2
    if score < WARN_THRESHOLD:
        return "WARN  — bundle passes but quality is below recommended threshold", 1
    return "PASS  — bundle meets AII spec quality bar", 0


def main() -> None:
    args = parse_args(description="29 — GNN bundle validation API")
    configure_logging(args.verbose)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    banner("GNN Bundle Validation API")

    # ---- 1. Build GNN bundle -------------------------------------------
    from cogant.config.pipeline import PipelineConfig  # noqa: E402
    from cogant.pipeline.runner import PipelineRunner  # noqa: E402

    config = PipelineConfig(target=Path(args.target), output_dir=output_dir)
    runner = PipelineRunner(config)

    print("  Running pipeline to GNN bundle…")
    result = runner.run(stages=["ingest", "static", "graph", "translate", "statespace", "gnn"])

    bundle = result.bundle
    if bundle is None:
        print("ERROR: pipeline did not produce a GNN bundle.")
        sys.exit(1)

    # ---- 2. Validate bundle --------------------------------------------
    from cogant.validate.validator import GNNValidator  # noqa: E402

    validator = GNNValidator()
    report = validator.validate(bundle)

    banner(f"Validation Report — score: {report.score:.1f}/100")
    print(f"  Sections checked : {report.sections_checked}")
    print(f"  Errors           : {len(report.errors)}")
    print(f"  Warnings         : {len(report.warnings)}")
    print(f"  Findings         : {len(report.findings)}")

    if report.errors:
        print("\n  Errors:")
        for err in report.errors[:5]:
            print(f"    ✗ [{err.section}] {err.message}")
        if len(report.errors) > 5:
            print(f"    … and {len(report.errors) - 5} more")

    if report.warnings:
        print("\n  Warnings:")
        for w in report.warnings[:5]:
            print(f"    ⚠ [{w.section}] {w.message}")

    # ---- 3. Per-section scores -----------------------------------------
    if hasattr(report, "section_scores") and report.section_scores:
        print("\n  Per-section scores:")
        for section, score in sorted(report.section_scores.items()):
            bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
            print(f"    {section:<30} {bar}  {score:.1f}")

    # ---- 4. Gate decision for CI ---------------------------------------
    decision, exit_code = gate_decision(report.score)
    banner(f"CI Gate: {decision}")
    print(f"  Exit code: {exit_code}")

    # ---- 5. Persist validation report ----------------------------------
    report_dict = {
        "score": report.score,
        "sections_checked": report.sections_checked,
        "errors": [{"section": e.section, "message": e.message} for e in report.errors],
        "warnings": [{"section": w.section, "message": w.message} for w in report.warnings],
        "ci_decision": decision,
        "ci_exit_code": exit_code,
    }
    if hasattr(report, "section_scores"):
        report_dict["section_scores"] = report.section_scores

    report_path = output_dir / "validation_report.json"
    report_path.write_text(json.dumps(report_dict, indent=2))
    print(f"\n  Validation report → {report_path}")

    # ---- 6. Degraded bundle demo (strip State Space section) -----------
    banner("Degraded Bundle Demo (strip State Space)")
    try:
        degraded = bundle.model_copy()
        # Simulate a bundle missing its state-space section
        if hasattr(degraded, "state_space"):
            object.__setattr__(degraded, "state_space", None)
        degraded_report = validator.validate(degraded)
        d_decision, _ = gate_decision(degraded_report.score)
        print(f"  Degraded score: {degraded_report.score:.1f}/100  → {d_decision}")
        print(f"  Score drop:     {report.score - degraded_report.score:.1f} points")
    except Exception as exc:
        print(f"  (Degraded demo skipped: {exc})")

    banner("Done")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
