from cogant.reverse.parser import parse_gnn
from cogant.reverse.callable import MatrixFunctions
from cogant.runtime.loop import AgentRuntime

gnn = open("output/simple_state/model.gnn.md").read()
mf = MatrixFunctions.from_gnn_text(gnn)

runtime = AgentRuntime(mf)
steps = runtime.run_n_steps(10)
print("final belief:", steps[-1].state_dist)
print("final VFE:", steps[-1].free_energy)
