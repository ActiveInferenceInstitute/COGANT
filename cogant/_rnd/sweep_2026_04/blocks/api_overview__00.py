from cogant import Session, PipelineRunner, Bundle
from cogant.api.pipeline import PipelineConfig

# Method 1: Step-by-step Session
session = Session.from_target("./my_project")
session.extract_static()
session.build_graph()
session.translate_to_gnn()
session.export_all("output/")

# Method 2: Orchestrated Pipeline
runner = PipelineRunner()
config = PipelineConfig(output_dir="output/")
bundle = runner.run("./my_project", config)

# Access results
print(bundle.repo_summary())
graph = bundle.program_graph()
print(f"Nodes: {len(graph.get('nodes', []))}")
print(f"Edges: {len(graph.get('edges', []))}")

# Export to JSON
bundle.save_json("output/bundle.json")
