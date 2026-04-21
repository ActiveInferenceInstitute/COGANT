## Step 3: Merge with dynamic analysis results (if available)
merger = GraphMerger()
merged_graph, provenance = merger.merge_graphs(static_graph, dynamic_graph)
