## Add edge
edge = builder.add_edge(
    source_id=func_node.id,
    target_id=class_node.id,
    kind=EdgeKind.CALLS,
    weight=1.0,
    evidence_sources=["static"]
)
