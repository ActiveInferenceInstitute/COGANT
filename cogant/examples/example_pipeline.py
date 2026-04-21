#!/usr/bin/env python3
"""
COGANT Pipeline Integration Example

This example demonstrates the full COGANT workflow:
1. Create a session for a target
2. Extract static and dynamic analysis
3. Build program graph
4. Translate to GNN
5. Compile state space
6. Export and visualize results
"""

import json
import sys
from pathlib import Path

# Add py directory to path when running as a script without editable install
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "py"))

EXAMPLE_REPO = _REPO_ROOT / "examples" / "python-service"

from cogant import Bundle, PipelineRunner, Session
from cogant.api.pipeline import PipelineConfig
from cogant.api.review import ReviewAPI
from cogant.scoring import DriftAnalyzer
from cogant.viz import GraphVisualizer, HTMLSiteRenderer, SemanticVisualizer


def example_session_api():
    """Example: Using the Session API directly."""
    print("=" * 60)
    print("Example 1: Session API")
    print("=" * 60)

    target = str(EXAMPLE_REPO.resolve()) if EXAMPLE_REPO.is_dir() else str(_REPO_ROOT)
    session = Session.from_target(target)
    print(f"Created session for: {session.target}")

    # Extract static analysis
    print("\nExtracting static analysis...")
    syntax_tree = session.extract_static()
    modules = syntax_tree.get("modules") or []
    print(f"  Parsed Python modules (summary rows): {len(modules)}")

    # Build program graph
    print("\nBuilding program graph...")
    program_graph = session.build_graph()
    nodes = program_graph.get("nodes") or {}
    edges = program_graph.get("edges") or {}
    print(f"  Graph nodes: {len(nodes)}")
    print(f"  Graph edges: {len(edges)}")

    # Translate to GNN
    print("\nTranslating to GNN...")
    gnn_model = session.translate_to_gnn()
    print(f"  GNN mapping count: {gnn_model.get('mapping_count', 0)}")

    # Compile state space
    print("\nCompiling state space...")
    state_space = session.compile_state_space()
    print(f"  States: {len(state_space['states'])}")
    print(f"  Observations: {len(state_space['observations'])}")
    print(f"  Actions: {len(state_space['actions'])}")

    # Export artifacts
    print("\nExporting artifacts...")
    output_dir = "./output/session_example"
    session.export_all(output_dir)
    print(f"  Exported to: {output_dir}")

    return session


def example_pipeline_runner():
    """Example: Using the PipelineRunner for orchestrated execution."""
    print("\n" + "=" * 60)
    print("Example 2: Pipeline Runner")
    print("=" * 60)

    config = PipelineConfig(
        stages=[
            "ingest",
            "static",
            "normalize",
            "graph",
            "translate",
            "statespace",
            "process",
            "export",
            "validate",
        ],
        output_dir="./output/pipeline_example",
        verbose=True,
    )

    runner = PipelineRunner()
    print(f"Running pipeline with {len(config.stages)} stages...")

    run_target = str(EXAMPLE_REPO.resolve()) if EXAMPLE_REPO.is_dir() else str(_REPO_ROOT)
    bundle = runner.run(run_target, config)

    print("\nPipeline Results:")
    print(f"  Target: {bundle.target}")
    print(f"  Completed stages: {len(bundle.stage_results)}")
    print(f"  Errors: {len(bundle.errors)}")

    if bundle.errors:
        print("\n  Errors encountered:")
        for error in bundle.errors[:3]:
            print(f"    - {error}")

    # Show stage results
    print("\n  Stage Results:")
    for stage, result in bundle.stage_results.items():
        result_type = result.get("type", "unknown")
        print(f"    {stage}: {result_type}")

    return bundle


def example_bundle_api(bundle: Bundle):
    """Example: Using the Bundle API to access results."""
    print("\n" + "=" * 60)
    print("Example 3: Bundle API")
    print("=" * 60)

    # Get summary
    print("\nRepository Summary:")
    summary = bundle.repo_summary()
    print(f"  Target: {summary['target']}")
    print(f"  Files: {summary['file_count']}")
    print(f"  Errors: {summary['total_errors']}")

    # Get program graph
    print("\nProgram Graph:")
    graph = bundle.program_graph()
    print(f"  Nodes: {len(graph.get('nodes', []))}")
    print(f"  Edges: {len(graph.get('edges', []))}")

    # Get state space
    print("\nState Space Model:")
    ss = bundle.state_space_model()
    print(f"  States: {len(ss.get('states', []))}")
    print(f"  Observations: {len(ss.get('observations', []))}")
    print(f"  Actions: {len(ss.get('actions', []))}")

    # Get process model
    print("\nProcess Model:")
    proc = bundle.process_model()
    print(f"  Stages: {len(proc.get('stages', []))}")
    print(f"  Dependencies: {len(proc.get('dependencies', []))}")

    # Validation report
    print("\nValidation Report:")
    validation = bundle.validation_report()
    print(f"  Passed: {validation.get('passed', True)}")
    print(f"  Checks: {len(validation.get('checks', {}))}")

    # GNN markdown
    print("\nGNN Markdown (truncated):")
    markdown = bundle.gnn_markdown()
    lines = markdown.split("\n")[:5]
    for line in lines:
        print(f"  {line}")

    # Export to JSON
    print("\nExporting bundle to JSON...")
    output_path = "./output/bundle_example.json"
    bundle.save_json(output_path)
    print(f"  Saved to: {output_path}")

    return bundle


def example_visualization(bundle: Bundle):
    """Example: Generating visualizations."""
    print("\n" + "=" * 60)
    print("Example 4: Visualization")
    print("=" * 60)

    # Graph visualization
    print("\nRendering program graph visualization...")
    visualizer = GraphVisualizer()
    graph = bundle.program_graph()
    if graph:
        visualizer.from_program_graph(graph)
        graph_html = "./output/graph_visualization.html"
        visualizer.render_html(graph_html)
        print(f"  Saved to: {graph_html}")

    # Semantic visualization
    print("\nRendering semantic view...")
    sem_viz = SemanticVisualizer()
    ss = bundle.state_space_model()
    if ss:
        sem_viz.from_state_space(ss)
        sem_html = "./output/semantic_visualization.html"
        sem_viz.render_html(sem_html)
        print(f"  Saved to: {sem_html}")

    # HTML site
    print("\nRendering full HTML site...")
    site_output = "./output/html_site"
    index_path = bundle.render_site(site_output)
    print(f"  Index: {index_path}")

    # Alternative: Using HTMLSiteRenderer
    print("\nRendering with HTMLSiteRenderer...")
    bundle_data = json.loads(bundle.to_json())
    renderer = HTMLSiteRenderer(bundle_data)
    site_path = renderer.render("./output/html_site_renderer")
    print(f"  Rendered to: {site_path}")


def example_review_api():
    """Example: Using the ReviewAPI for curation."""
    print("\n" + "=" * 60)
    print("Example 5: Review API")
    print("=" * 60)

    review_api = ReviewAPI()

    # Create sample bundle
    sample_bundle = {
        "target": "example_repo",
        "stage_results": {
            "translate": {
                "node_features": [{}, {}, {}, {}, {}],
                "edge_indices": [],
            }
        },
        "errors": [],
    }

    # Save sample bundle
    bundle_path = "./output/sample_bundle.json"
    with open(bundle_path, "w") as f:
        json.dump(sample_bundle, f)

    print(f"\nLoading bundle from {bundle_path}...")
    review_api.load_bundle(bundle_path)

    # Get review summary
    summary = review_api.get_review_summary()
    print(f"  Total mappings: {summary['total']}")
    print(f"  Pending: {summary['pending']}")
    print(f"  Accepted: {summary['accepted']}")

    # Present mappings
    print("\nAvailable mappings for review:")
    pending = review_api.get_pending_mappings()
    for mapping in pending[:3]:
        print(f"  - {mapping.id}: {mapping.source} → {mapping.target}")

    # Accept a mapping
    if pending:
        mapping_id = pending[0].id
        print(f"\nAccepting mapping: {mapping_id}")
        review_api.accept_mapping(mapping_id, notes="Looks good")

    # Save curated bundle
    curated_path = "./output/curated_bundle.json"
    print(f"\nSaving curated bundle to {curated_path}...")
    review_api.save_curated_bundle(curated_path)

    # Check final summary
    final_summary = review_api.get_review_summary()
    print(f"  Final accepted: {final_summary['accepted']}")


def example_drift_analysis(bundle1: Bundle, bundle2: Bundle):
    """Example: Analyzing architectural drift."""
    print("\n" + "=" * 60)
    print("Example 6: Drift Analysis")
    print("=" * 60)

    analyzer = DriftAnalyzer()

    # Convert bundles to dicts
    data1 = json.loads(bundle1.to_json()) if isinstance(bundle1, Bundle) else bundle1
    data2 = json.loads(bundle2.to_json()) if isinstance(bundle2, Bundle) else bundle2

    print("\nComparing bundles...")
    print(f"  Bundle 1: {data1['target']}")
    print(f"  Bundle 2: {data2['target']}")

    # Analyze drift
    score = analyzer.analyze(data1, data2)

    print("\nDrift Scores:")
    print(f"  Overall: {score.total_score:.2%}")
    print(f"  Architectural: {score.architectural_score:.2%}")
    print(f"  Semantic Churn: {score.semantic_churn_score:.2%}")

    print("\nDetails:")
    for key, value in score.details.items():
        print(f"  {key}: {value}")

    # Print full report
    print("\nFull Report:")
    print(analyzer.report(score))


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("COGANT Pipeline Integration Examples")
    print("=" * 60)

    try:
        # Create output directory
        Path("./output").mkdir(exist_ok=True)

        # Example 1: Session API
        session = example_session_api()

        # Example 2: Pipeline Runner
        bundle = example_pipeline_runner()

        # Example 3: Bundle API
        bundle = example_bundle_api(bundle)

        # Example 4: Visualization
        example_visualization(bundle)

        # Example 5: Review API
        example_review_api()

        # Example 6: Drift Analysis (use same bundle twice for demo)
        example_drift_analysis(bundle, bundle)

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
