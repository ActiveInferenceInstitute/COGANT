## PyTorch Geometric export

> **Status:** The attribute layout below matches the intended `torch_geometric.data.Data` contract. A first-party `Session.export_pytorch_geometric()` helper is still **planned**; use typed JSON / bundle exports today, or build `Data` objects yourself from bundle JSON.

### Format

PyG `Data` object with the following attributes:

```python
data = Data(
    x=torch.FloatTensor,        # Node features (N x F)
    edge_index=torch.LongTensor, # Edge indices (2 x E)
    edge_attr=torch.FloatTensor, # Edge features (E x F)
    y=torch.LongTensor,          # Node labels (N,)
    node_kind=torch.LongTensor,  # Node kind (N,)
    node_role=torch.LongTensor,  # Node role (N,)
    node_names=List[str],        # Human names (N,)
    node_ids=List[str],          # UUIDs (N,)
    edge_kind=torch.LongTensor,  # Edge kind (E,)
)
```

### Node Features (x)

Extracted from node metadata:

1. **One-hot encodings**:
   - NodeKind (13 dimensions)
   - SemanticRole (30 dimensions)
   - EdgeKind (incoming/outgoing edges)

2. **Numerical features**:
   - Confidence (1 dimension)
   - In-degree (1 dimension)
   - Out-degree (1 dimension)
   - Type presence (1 dimension, binary)

3. **Textual features** (optional):
   - Name embedding (768 dimensions via pre-trained model)
   - Documentation embedding (768 dimensions, if present)

**Total**: ~50-1600 dimensions depending on configuration

### Edge Features (edge_attr)

1. **One-hot encodings**:
   - EdgeKind (18 dimensions)

2. **Numerical features**:
   - Confidence (1 dimension)
   - Label presence (1 dimension, binary)

**Total**: ~20 dimensions

### Node Labels (y)

For supervised tasks, labels are:
- **Node classification**: SemanticRole (30 classes)
- **Custom**: User-defined classification

### Export Example

```python
# doctest: +SKIP  # example requires runtime context or external resources
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
```

### Training Example

```python
# doctest: +SKIP  # example requires runtime context or external resources
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
```

