from cogant.graph.queries import GraphQuery

query = GraphQuery(graph)

# Find all classes
classes = graph.get_nodes_by_kind(NodeKind.CLASS)

# Get all outgoing edges from a node
edges = graph.get_edges_from(node.id)

# Filter edges by kind
reads = [e for e in edges if e.kind == EdgeKind.READS]
writes = [e for e in edges if e.kind == EdgeKind.WRITES]
