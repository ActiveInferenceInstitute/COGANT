## Step 2: Build graph from normalized facts
builder = ProgramGraphBuilder(repo_uri="https://github.com/example/repo")
identity_resolver = builder.identity_resolver

for norm_fact in normalized_facts:
    node_id = identity_resolver.get_id(
        entity_type=norm_fact.node_kind.value,
        repo_uri=builder.repo_uri,
        path=norm_fact.path,
        qualified_name=norm_fact.qualified_name
    )
    node = builder.add_node(
        kind=norm_fact.node_kind,
        name=norm_fact.name,
        qualified_name=norm_fact.qualified_name,
        path=norm_fact.path,
        language=norm_fact.language,
        metadata=norm_fact.metadata
    )
