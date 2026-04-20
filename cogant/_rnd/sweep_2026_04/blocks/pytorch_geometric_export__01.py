from cogant import Session
import torch

session = Session.from_target("./my_project")
session.extract_static()
session.build_graph()
session.translate_to_gnn()

# Export to PyTorch Geometric (roadmap; JSON export available now)
pyg_data = session.export_pytorch_geometric()  # planned

print(f"Nodes: {pyg_data.num_nodes}")
print(f"Edges: {pyg_data.num_edges}")
print(f"Features: {pyg_data.x.shape}")

# Save for later use
torch.save(pyg_data, "graph_data.pt")
