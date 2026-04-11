from pathlib import Path
from cogant.gnn.runner import load_gnn_package
from cogant.simulate.runner import SimulationRunner

# Load a forward-produced GNN package
gnn = load_gnn_package(Path("output/calculator/gnn_package"))

# The matrices define the synthesized package's behavior
print("Hidden states:", [s.name for s in gnn.state_space.variables.values()])
# ['display', 'accumulator', 'history_len']

print("Observations:", [o.name for o in gnn.state_space.observations.values()])
# ['get_display', 'get_history', 'assert_display']

print("Actions:", [a.name for a in gnn.state_space.actions.values()])
# ['_execute_operation']
