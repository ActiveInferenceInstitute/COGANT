from cogant import PipelineRunner
from cogant.api.pipeline import PipelineConfig

runner = PipelineRunner()
config = PipelineConfig(output_dir="output/")
bundle = runner.run("./my_project", config)

# Export to DGL (planned)
dgl_graph = bundle.export_dgl()  # planned

print(f"Nodes: {dgl_graph.num_nodes()}")
print(f"Edges: {dgl_graph.num_edges()}")
