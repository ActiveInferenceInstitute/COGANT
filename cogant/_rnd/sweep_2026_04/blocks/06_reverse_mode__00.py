from pathlib import Path

from cogant.gnn.runner import load_gnn_package  # load bundle + matrices
from cogant.simulate.runner import SimulationRunner

package_dir = Path("output/calculator/gnn_package")
gnn = load_gnn_package(package_dir)

print("Hidden states:", [s.name for s in gnn.state_space.variables.values()])
print("Observations:", [o.name for o in gnn.state_space.observations.values()])
print("Actions:", [a.name for a in gnn.state_space.actions.values()])
