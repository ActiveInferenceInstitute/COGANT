from pathlib import Path
from cogant.gnn.runner import load_gnn_package

package_dir = Path("output/my_project/gnn_package")
gnn = load_gnn_package(package_dir)

# Enumerate the model's variables
for var in gnn.state_space.variables.values():
    print(f"Hidden state: {var.name} ({var.var_type})")

for obs in gnn.state_space.observations.values():
    print(f"Observation: {obs.name}")

for act in gnn.state_space.actions.values():
    print(f"Action: {act.name}")
