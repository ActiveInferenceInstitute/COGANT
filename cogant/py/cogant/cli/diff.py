"""Diff CLI command: Compare two output bundles and generate diff reports."""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_bundle(output_dir: Path) -> dict:
    """Load a bundle from an output directory.

    Args:
        output_dir: Directory containing output artifacts.

    Returns:
        Bundle dict with 'graph', 'state_space', 'mappings' keys.
    """
    bundle = {}

    # Load program graph
    graph_path = output_dir / "program_graph.json"
    if graph_path.exists():
        with open(graph_path) as f:
            bundle["graph"] = json.load(f)
        logger.info(f"Loaded graph from {graph_path}")

    # Load semantic mappings
    mappings_path = output_dir / "semantic_mappings.json"
    if mappings_path.exists():
        with open(mappings_path) as f:
            mappings_data = json.load(f)
            # Handle both dict and list formats
            if isinstance(mappings_data, list):
                bundle["mappings"] = {m.get("id"): m for m in mappings_data}
            else:
                bundle["mappings"] = mappings_data
        logger.info(f"Loaded mappings from {mappings_path}")

    # Load state space (may be in model.gnn.json)
    gnn_path = output_dir / "model.gnn.json"
    if gnn_path.exists():
        with open(gnn_path) as f:
            gnn_data = json.load(f)
            if "state_space" in gnn_data:
                bundle["state_space"] = gnn_data["state_space"]
            logger.info(f"Loaded state space from {gnn_path}")

    return bundle


def diff_command(output_dir_a: str, output_dir_b: str) -> str:
    """Compare two output directories and generate diff report.

    Args:
        output_dir_a: Path to baseline output directory.
        output_dir_b: Path to current output directory.

    Returns:
        Markdown diff report.
    """
    from cogant.scoring.drift import DriftAnalyzer
    from cogant.scoring.metrics import CodebaseMetrics

    # Load bundles
    path_a = Path(output_dir_a).resolve()
    path_b = Path(output_dir_b).resolve()

    logger.info(f"Loading baseline bundle from {path_a}")
    bundle_a = load_bundle(path_a)

    logger.info(f"Loading current bundle from {path_b}")
    bundle_b = load_bundle(path_b)

    # Compute drift
    logger.info("Computing drift...")
    analyzer = DriftAnalyzer(bundle_a, bundle_b)
    drift_report = analyzer.generate_diff_report()

    # Compute metrics for each bundle
    logger.info("Computing metrics...")
    graph_a = bundle_a.get("graph", {})
    ss_a = bundle_a.get("state_space", {})
    mappings_a = bundle_a.get("mappings", {})

    graph_b = bundle_b.get("graph", {})
    ss_b = bundle_b.get("state_space", {})
    mappings_b = bundle_b.get("mappings", {})

    metrics_a = CodebaseMetrics(graph_a, ss_a, mappings_a)
    metrics_b = CodebaseMetrics(graph_b, ss_b, mappings_b)

    # Build comprehensive report
    report_lines = [
        "# Codebase Diff Report",
        "",
        f"**Baseline**: {path_a.name}",
        f"**Current**: {path_b.name}",
        "",
        drift_report,
        "",
        "## Metrics Comparison",
        "",
        "### Baseline Metrics",
        "",
        metrics_a.format_report(),
        "",
        "### Current Metrics",
        "",
        metrics_b.format_report(),
        "",
    ]

    return "\n".join(report_lines)
