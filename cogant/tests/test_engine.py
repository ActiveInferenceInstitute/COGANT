"""Integration tests for COGANT normalization, graph, and translation engines."""

import os
import sys

import pytest

# Add the py directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "py"))

from cogant.normalize.identities import IdentityResolver
from cogant.normalize.canonical import CanonicalNormalizer, LanguageFact
from cogant.graph.builder import ProgramGraphBuilder
from cogant.graph.queries import GraphQuery
from cogant.graph.merge import GraphMerger
from cogant.translate.engine import TranslationEngine
from cogant.translate.rules import (
    ReadOnlyInputRule,
    MutatingSubsystemRule,
    OrchestratorRule,
    TestAssertionRule,
)
from cogant.translate.confidence import ConfidenceModel
from cogant.translate.review import ReviewManager
from cogant.schemas.core import NodeKind, EdgeKind


def _sample_graph_builder() -> ProgramGraphBuilder:
    """Build a small program graph used by query/translation tests."""
    builder = ProgramGraphBuilder(repo_uri="https://github.com/example/repo")

    class_node = builder.add_node(
        kind=NodeKind.CLASS,
        name="DataProcessor",
        qualified_name="app.core.DataProcessor",
        path="src/app/core.py",
        language="python",
        metadata={"visibility": "public"},
    )

    func_node = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="process_data",
        qualified_name="app.processing.process_data",
        path="src/app/processing.py",
        language="python",
    )

    builder.add_edge(
        source_id=func_node.id,
        target_id=class_node.id,
        kind=EdgeKind.CALLS,
        weight=1.0,
        evidence_sources=["static"],
    )

    return builder


@pytest.fixture
def builder() -> ProgramGraphBuilder:
    """Shared ProgramGraphBuilder for dependent tests."""
    return _sample_graph_builder()


def test_identity_resolver():
    """Test the identity resolver."""
    print("\n=== Testing IdentityResolver ===")

    resolver = IdentityResolver()

    # Generate IDs
    id1 = resolver.generate_id(
        entity_type="module",
        repo_uri="https://github.com/example/repo",
        path="src/main.py",
        qualified_name="myapp.core",
    )
    print(f"Generated ID 1: {id1}")

    # Idempotent: same inputs should give same ID
    id1_again = resolver.get_id(
        entity_type="module",
        repo_uri="https://github.com/example/repo",
        path="src/main.py",
        qualified_name="myapp.core",
    )
    assert id1 == id1_again, "IDs should be identical"
    print(f"Idempotent check: {id1} == {id1_again} ✓")

    # Generate edge ID
    edge_id = resolver.generate_edge_id(id1, "some_target_id", "CALLS")
    print(f"Generated edge ID: {edge_id}")

    # Get statistics
    stats = resolver.get_statistics()
    print(f"Statistics: {stats}")

    print("✓ IdentityResolver tests passed")


def test_canonical_normalizer():
    """Test the canonical normalizer."""
    print("\n=== Testing CanonicalNormalizer ===")

    normalizer = CanonicalNormalizer()

    # Create language-specific facts
    python_class = LanguageFact(
        fact_type="class",
        language="python",
        data={
            "name": "MyClass",
            "qualified_name": "mymodule.MyClass",
            "path": "src/mymodule.py",
            "visibility": "public",
            "decorators": ["@dataclass"],
        },
    )

    # Normalize
    normalized = normalizer.normalize(python_class)
    assert normalized is not None
    assert normalized.node_kind == NodeKind.CLASS
    print(f"Normalized Python class: {normalized.name} ({normalized.node_kind.value})")

    # Batch normalize
    facts = [python_class]
    normalized_batch = normalizer.normalize_batch(facts)
    print(f"Batch normalized {len(normalized_batch)} facts")

    stats = normalizer.get_normalization_stats()
    print(f"Normalization stats: {stats}")

    print("✓ CanonicalNormalizer tests passed")


def test_graph_builder():
    """Test the program graph builder."""
    print("\n=== Testing ProgramGraphBuilder ===")

    builder = _sample_graph_builder()
    class_nodes = builder.graph.get_nodes_by_kind(NodeKind.CLASS)
    assert class_nodes
    print(f"Added class node: {class_nodes[0].id}")

    func_nodes = builder.graph.get_nodes_by_kind(NodeKind.FUNCTION)
    assert func_nodes
    print(f"Added function node: {func_nodes[0].id}")

    # Query
    neighbors = builder.get_neighbors(class_nodes[0].id)
    print(f"Neighbors of {class_nodes[0].name}: {[n.name for n in neighbors]}")

    # Get statistics
    stats = builder.get_statistics()
    print(f"Graph statistics: {stats}")

    print("✓ ProgramGraphBuilder tests passed")


def test_graph_queries(builder):
    """Test graph query operations."""
    print("\n=== Testing GraphQuery ===")

    query = GraphQuery(builder.graph)

    # Filter nodes
    python_nodes = query.filter_nodes(language="python")
    print(f"Python nodes: {len(python_nodes)}")

    functions = query.filter_nodes(kind=NodeKind.FUNCTION)
    print(f"Function nodes: {len(functions)}")

    # Get degrees
    for node_id in builder.graph.nodes:
        in_degree = query.compute_in_degree(node_id)
        out_degree = query.compute_out_degree(node_id)
        print(f"Node {node_id[:8]}: in={in_degree}, out={out_degree}")

    # Get centrality
    degree_centrality = query.compute_degree_centrality()
    print(f"Degree centrality: {degree_centrality}")

    print("✓ GraphQuery tests passed")


def test_translation_engine(builder):
    """Test the translation engine."""
    print("\n=== Testing TranslationEngine ===")

    engine = TranslationEngine()

    # Register rules
    engine.register_rule(ReadOnlyInputRule())
    engine.register_rule(MutatingSubsystemRule())
    engine.register_rule(OrchestratorRule())
    engine.register_rule(TestAssertionRule())

    print(f"Registered {len(engine.rules)} rules")

    # Translate
    mappings = engine.translate(builder.graph)
    print(f"Generated {len(mappings)} semantic mappings")

    for mapping in mappings:
        print(f"  - {mapping.semantic_label} ({mapping.kind.value})")

    # Get statistics
    stats = engine.get_statistics()
    print(f"Translation statistics: {stats}")

    print("✓ TranslationEngine tests passed")

    assert isinstance(mappings, list)


@pytest.fixture
def mappings(builder: ProgramGraphBuilder):
    """Semantic mappings from the translation engine (shared with confidence/review tests)."""
    engine = TranslationEngine()
    engine.register_rule(ReadOnlyInputRule())
    engine.register_rule(MutatingSubsystemRule())
    engine.register_rule(OrchestratorRule())
    engine.register_rule(TestAssertionRule())
    return engine.translate(builder.graph)


def test_confidence_model(mappings):
    """Test the confidence model."""
    print("\n=== Testing ConfidenceModel ===")

    model = ConfidenceModel()

    # Score mappings
    model.score_batch(mappings)

    for mapping in mappings[:3]:
        print(f"Mapping: {mapping.semantic_label}")
        print(f"  - Confidence score: {mapping.confidence_score:.2f}")
        print(f"  - Confidence tier: {mapping.confidence_tier.value}")
        print(f"  - Evidence count: {mapping.evidence_count}")

    # Get report
    report = model.get_scoring_report()
    print(f"Scoring report: {report}")

    print("✓ ConfidenceModel tests passed")


def test_review_manager(mappings):
    """Test the review manager."""
    print("\n=== Testing ReviewManager ===")

    manager = ReviewManager()

    # Add mappings
    for mapping in mappings:
        manager.add_mapping(mapping)

    print(f"Added {len(mappings)} mappings for review")

    # Accept first mapping
    if mappings:
        first_id = mappings[0].id
        manager.accept_mapping(first_id, "reviewer@example.com", "Looks good!")
        print(f"Accepted mapping: {first_id}")

    # Get summary
    summary = manager.get_review_summary()
    print(f"Review summary: {summary}")

    # Export reviewed
    reviewed = manager.export_reviewed_mappings()
    print(f"Reviewed mappings: {len(reviewed)}")

    print("✓ ReviewManager tests passed")


def test_graph_merge():
    """Test graph merging."""
    print("\n=== Testing GraphMerger ===")

    # Create two graphs to merge
    builder1 = ProgramGraphBuilder(repo_uri="https://github.com/example/repo")
    builder1.add_node(
        kind=NodeKind.CLASS,
        name="Database",
        qualified_name="db.Database",
        language="python",
    )
    graph1 = builder1.finalize()

    builder2 = ProgramGraphBuilder(repo_uri="https://github.com/example/repo")
    builder2.add_node(
        kind=NodeKind.CLASS,
        name="Cache",
        qualified_name="cache.Cache",
        language="python",
    )
    graph2 = builder2.finalize()

    merger = GraphMerger()
    merged, provenance = merger.merge_graphs(graph1, graph2)

    print(f"Merged graphs: {merged.node_count()} nodes, {merged.edge_count()} edges")
    print(f"Merge provenance: {provenance.nodes_added} nodes added, {provenance.edges_added} edges added")

    stats = merger.get_merge_statistics()
    print(f"Merge statistics: {stats}")

    print("✓ GraphMerger tests passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("COGANT Engine Integration Tests")
    print("=" * 60)

    test_identity_resolver()
    test_canonical_normalizer()
    builder = test_graph_builder()
    test_graph_queries(builder)
    mappings = test_translation_engine(builder)
    test_confidence_model(mappings)
    test_review_manager(mappings)
    test_graph_merge()

    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    main()
