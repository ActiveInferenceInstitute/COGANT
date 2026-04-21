## Split
new_ids = manager.split_mapping(
    mapping_id=mapping.id,
    reviewer="bob@example.com",
    split_definitions=[
        {
            "kind": MappingKind.OBSERVATION,
            "node_ids": [...],
            "label": "Primary observation"
        },
        {
            "kind": MappingKind.POLICY,
            "node_ids": [...],
            "label": "Fallback policy"
        }
    ]
)
