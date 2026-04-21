#!/usr/bin/env python3
"""
Example: Run orchestrator on flask_mini, modify it, re-run, and compute drift.

Steps:
  1. Copy flask_mini to a temp directory
  2. Run orchestrator on the original
  3. Modify flask_mini slightly (add a method to a class)
  4. Run orchestrator again
  5. Load both output bundles and compute drift
  6. Save diff report
"""

import json
import logging
import shutil
import sys
import tempfile
from pathlib import Path

# Add py/ to path for cogant imports
sys.path.insert(0, str(Path(__file__).parent.parent / "py"))

from cogant.cli.diff import load_bundle
from cogant.scoring.drift import DriftAnalyzer
from cogant.scoring.metrics import CodebaseMetrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_orchestrator(repo_path: Path, output_dir: Path) -> bool:
    """Run the orchestrator on a repository.

    Args:
        repo_path: Path to repository.
        output_dir: Where to save output.

    Returns:
        True if successful.
    """
    try:
        from examples.orchestrate_roundtrip import RoundtripOrchestrator

        orchestrator = RoundtripOrchestrator(repo_path, output_dir)
        return orchestrator.run()
    except Exception as e:
        logger.error(f"Orchestrator failed: {e}")
        return False


def modify_codebase(repo_path: Path) -> None:
    """Add a new method to a class in flask_mini to trigger changes.

    Args:
        repo_path: Path to repository to modify.
    """
    # Find a Python file and add a method
    for py_file in repo_path.rglob("*.py"):
        # Skip __pycache__ and .venv
        if "__pycache__" in str(py_file) or ".venv" in str(py_file):
            continue

        # Look for a class definition
        content = py_file.read_text()
        if "class " in content:
            # Add a new method
            lines = content.split("\n")
            new_lines = []
            added = False

            for i, line in enumerate(lines):
                new_lines.append(line)

                # Find a method and add after it
                if not added and line.strip().startswith("def ") and "self" in line:
                    # Find the end of this method
                    indent = len(line) - len(line.lstrip())
                    for j in range(i + 1, len(lines)):
                        next_line = lines[j]
                        if next_line.strip() and not next_line.startswith(" " * (indent + 1)):
                            # End of method found
                            new_method = (
                                "\n    def new_method_added(self):\n"
                                '        """New method added during drift analysis."""\n'
                                "        return None\n"
                            )
                            new_lines.append(new_method)
                            added = True
                            break

            if added:
                py_file.write_text("\n".join(new_lines))
                logger.info(f"Modified {py_file}: added new_method_added()")
                return

    logger.warning("Could not find a class to modify")


def main():
    """Run the full diff example."""
    # Get flask_mini path
    examples_dir = Path(__file__).parent
    flask_mini = examples_dir / "control_positive" / "flask_mini"

    if not flask_mini.exists():
        logger.error(f"flask_mini not found at {flask_mini}")
        return

    logger.info(f"Starting diff example with {flask_mini}")

    # Create temp directories for baseline and modified versions
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Copy flask_mini to baseline version
        baseline_repo = tmpdir / "flask_mini_baseline"
        shutil.copytree(flask_mini, baseline_repo)
        logger.info(f"Copied flask_mini to {baseline_repo}")

        # Copy flask_mini to modified version
        modified_repo = tmpdir / "flask_mini_modified"
        shutil.copytree(flask_mini, modified_repo)
        logger.info(f"Copied flask_mini to {modified_repo}")

        # Run orchestrator on baseline
        baseline_output = tmpdir / "output_baseline"
        logger.info("Running orchestrator on baseline...")
        if not run_orchestrator(baseline_repo, baseline_output):
            logger.error("Failed to run orchestrator on baseline")
            return

        logger.info(f"Baseline output saved to {baseline_output}")

        # Modify the codebase
        logger.info("Modifying codebase...")
        modify_codebase(modified_repo)

        # Run orchestrator on modified
        modified_output = tmpdir / "output_modified"
        logger.info("Running orchestrator on modified version...")
        if not run_orchestrator(modified_repo, modified_output):
            logger.error("Failed to run orchestrator on modified")
            return

        logger.info(f"Modified output saved to {modified_output}")

        # Load bundles and compute drift
        logger.info("Loading bundles and computing drift...")
        bundle_a = load_bundle(baseline_output)
        bundle_b = load_bundle(modified_output)

        # Compute drift
        analyzer = DriftAnalyzer(bundle_a, bundle_b)
        drift_report = analyzer.generate_diff_report()
        drift_mermaid = analyzer.generate_diff_mermaid()

        # Compute metrics
        metrics_a = CodebaseMetrics(
            bundle_a.get("graph", {}),
            bundle_a.get("state_space", {}),
            bundle_a.get("mappings", {}),
        )
        metrics_b = CodebaseMetrics(
            bundle_b.get("graph", {}),
            bundle_b.get("state_space", {}),
            bundle_b.get("mappings", {}),
        )

        # Save reports
        output_base = examples_dir.parent / "output" / "diff_example"
        output_base.mkdir(parents=True, exist_ok=True)

        # Save markdown diff report
        diff_report_path = output_base / "diff_report.md"
        full_report = "\n".join(
            [
                "# Flask Mini Drift Analysis Example",
                "",
                drift_report,
                "",
                "## Metrics Comparison",
                "",
                "### Baseline",
                "",
                metrics_a.format_report(),
                "",
                "### Modified",
                "",
                metrics_b.format_report(),
                "",
                "## Drift Diagram",
                "",
                "```mermaid",
                drift_mermaid,
                "```",
            ]
        )

        diff_report_path.write_text(full_report)
        logger.info(f"Diff report saved to {diff_report_path}")

        # Save JSON diff
        diff_json_path = output_base / "diff_report.json"
        diff_json = {
            "drift": analyzer.to_dict(),
            "metrics_baseline": metrics_a.to_dict(),
            "metrics_modified": metrics_b.to_dict(),
        }
        diff_json_path.write_text(json.dumps(diff_json, indent=2))
        logger.info(f"Diff JSON saved to {diff_json_path}")

        # Print summary
        logger.info("")
        logger.info("=" * 60)
        logger.info("DRIFT ANALYSIS SUMMARY")
        logger.info("=" * 60)
        logger.info(drift_report)
        logger.info("=" * 60)
        logger.info(f"Reports saved to {output_base}")


if __name__ == "__main__":
    main()
