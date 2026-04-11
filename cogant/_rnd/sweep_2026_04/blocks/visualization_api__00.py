from cogant.viz import GraphVisualizer

visualizer = GraphVisualizer()
visualizer.from_program_graph(bundle.program_graph())

# Cluster nodes
visualizer.cluster_by_package()
visualizer.cluster_by_language()
visualizer.cluster_by_service()

# Filter by edge type
visualizer.filter_by_edge_type("calls")

# Render
visualizer.render_html("graph.html")
visualizer.render_svg("graph.svg")

# Export as JSON
d3_data = visualizer.to_d3_json()
