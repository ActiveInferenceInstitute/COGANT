## Add edges (from analysis results)
for edge_fact in edge_facts:
    builder.add_edge(
        source_id=edge_fact.source_id,
        target_id=edge_fact.target_id,
        kind=edge_fact.kind,
        weight=edge_fact.weight,
        evidence_sources=edge_fact.sources
    )

static_graph = builder.finalize()
