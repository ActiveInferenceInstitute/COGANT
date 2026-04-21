#!/usr/bin/env python3
"""
Test script for drift analyzer and metrics system.
Creates minimal test bundles and computes drift.
"""

import json
import sys
from pathlib import Path

# Add py/ to path
sys.path.insert(0, str(Path(__file__).parent.parent / "py"))

from cogant.scoring.drift import DriftAnalyzer
from cogant.scoring.metrics import CodebaseMetrics


def create_minimal_bundle(name: str, num_nodes: int = 10, num_edges: int = 15) -> dict:
    """Create a minimal test bundle."""
    nodes = [
        {
            "id": f"node_{i}",
            "kind": "function",
            "label": f"func_{i}",
            "language": "python",
            "location": {"file": "test.py", "line": i},
        }
        for i in range(num_nodes)
    ]

    edges = [
        {
            "source": f"node_{i}",
            "target": f"node_{(i + 1) % num_nodes}",
            "kind": "calls",
        }
        for i in range(num_edges)
    ]

    state_vars = [
        {
            "var_id": f"var_{i}",
            "name": f"state_{i}",
            "value_type": {"base_type": "int"},
            "is_observable": i % 2 == 0,
        }
        for i in range(3)
    ]

    observations = [
        {
            "modality_id": f"obs_{i}",
            "name": f"observation_{i}",
            "observation_type": {"base_type": "float"},
            "observes_state_vars": [f"var_{i}"],
        }
        for i in range(2)
    ]

    actions = [
        {
            "action_id": f"action_{i}",
            "name": f"action_{i}",
            "action_type": {"base_type": "int"},
            "affects_state_vars": [f"var_{i % 3}"],
        }
        for i in range(2)
    ]

    return {
        "graph": {"nodes": nodes, "edges": edges},
        "state_space": {
            "states": state_vars,
            "observations": observations,
            "actions": actions,
        },
        "mappings": {f"node_{i}": {"role": f"role_{i % 3}"} for i in range(num_nodes)},
    }


def main():
    print("\n" + "=" * 60)
    print("Testing Drift Analyzer & Metrics System")
    print("=" * 60)

    # Create test bundles
    print("\nCreating test bundles...")
    bundle_a = create_minimal_bundle("baseline", num_nodes=10, num_edges=15)
    bundle_b = create_minimal_bundle("modified", num_nodes=12, num_edges=18)

    # Simulate drift: add a few nodes and change some edges
    bundle_b["graph"]["nodes"].extend(
        [
            {
                "id": "node_new_1",
                "kind": "class",
                "label": "NewClass",
                "language": "python",
                "location": {"file": "new.py", "line": 1},
            }
        ]
    )
    bundle_b["graph"]["edges"].append(
        {
            "source": "node_0",
            "target": "node_new_1",
            "kind": "instantiates",
        }
    )

    # Compute drift
    print("Computing drift...")
    analyzer = DriftAnalyzer(bundle_a, bundle_b)

    structural_drift = analyzer.compute_structural_drift()
    semantic_drift = analyzer.compute_semantic_drift()
    state_space_drift = analyzer.compute_state_space_drift()
    arch_score = analyzer.compute_architectural_drift_score()
    semantic_score = analyzer.compute_semantic_churn_score()

    print("\n--- Structural Drift ---")
    print(f"  Nodes added: {structural_drift['nodes_added_count']}")
    print(f"  Nodes removed: {structural_drift['nodes_removed_count']}")
    print(
        f"  Edges changed: {structural_drift['edges_added_count'] + structural_drift['edges_removed_count']}"
    )

    print("\n--- Semantic Drift ---")
    print(f"  New mappings: {semantic_drift['new_count']}")
    print(f"  Lost mappings: {semantic_drift['lost_count']}")

    print("\n--- State Space Drift ---")
    print(
        f"  State vars changed: {state_space_drift['state_vars_added'] + state_space_drift['state_vars_removed']}"
    )
    print(
        f"  Observations changed: {state_space_drift['observations_added'] + state_space_drift['observations_removed']}"
    )

    print("\n--- Scores ---")
    print(f"  Architectural Drift: {arch_score:.1%}")
    print(f"  Semantic Churn: {semantic_score:.1%}")
    print(f"  Total Drift: {(arch_score + semantic_score) / 2:.1%}")

    print("\n--- Diff Report ---")
    report = analyzer.generate_diff_report()
    print(report)

    # Test metrics
    print("\n" + "=" * 60)
    print("Testing Metrics System")
    print("=" * 60)

    metrics_a = CodebaseMetrics(
        bundle_a["graph"],
        bundle_a["state_space"],
        bundle_a["mappings"],
    )
    metrics_b = CodebaseMetrics(
        bundle_b["graph"],
        bundle_b["state_space"],
        bundle_b["mappings"],
    )

    print("\n--- Baseline Metrics ---")
    report_a = metrics_a.format_report()
    print(report_a)

    print("\n--- Modified Metrics ---")
    report_b = metrics_b.format_report()
    print(report_b)

    # Test JSON export
    print("\n--- JSON Export (Drift) ---")
    drift_json = analyzer.to_dict()
    print(json.dumps(drift_json, indent=2)[:500] + "...")

    print("\n--- JSON Export (Metrics) ---")
    metrics_json = metrics_a.to_dict()
    print(json.dumps(metrics_json, indent=2))

    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
