from cogant import Session
from torch_geometric.data import DataLoader
from torch_geometric.nn import GCNConv
import torch
import torch.nn.functional as F

# Load data (PyG export is roadmap; shown for illustration)
session = Session.from_target("./my_project")
session.extract_static()
session.build_graph()
session.translate_to_gnn()
pyg_data = session.export_pytorch_geometric()  # planned

# Split train/test
train_mask = torch.randperm(pyg_data.num_nodes) < 0.8 * pyg_data.num_nodes
test_mask = ~train_mask
pyg_data.train_mask = train_mask
pyg_data.test_mask = test_mask

# Simple GCN model
class GCN(torch.nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.conv1 = GCNConv(in_channels, 64)
        self.conv2 = GCNConv(64, out_channels)
    
    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index).relu()
        x = F.dropout(x, p=0.5, training=self.training)
        x = self.conv2(x, edge_index)
        return x

# Train
model = GCN(pyg_data.num_features, 30)  # 30 roles
optimizer = torch.optim.Adam(model.parameters())

for epoch in range(100):
    model.train()
    optimizer.zero_grad()
    out = model(pyg_data.x, pyg_data.edge_index)
    loss = F.cross_entropy(
        out[pyg_data.train_mask],
        pyg_data.y[pyg_data.train_mask]
    )
    loss.backward()
    optimizer.step()

# Evaluate
model.eval()
out = model(pyg_data.x, pyg_data.edge_index)
pred = out.argmax(dim=1)
acc = (pred[pyg_data.test_mask] == pyg_data.y[pyg_data.test_mask]).float().mean()
print(f"Test Accuracy: {acc:.4f}")
