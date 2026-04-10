## GNNSection
hierarchical

## GNNVersionAndFlags
GNN v1

## ModelName
hierarchical

## ModelAnnotation
Two-level hierarchical Active Inference model. A high-level planner (3 goal states) governs a low-level executor (4 motor states). The planner's MAP estimate conditions the executor's transition dynamics.

## StateSpaceBlock
s_planner[3,1,type=float]
s_executor[4,1,type=float]
D_planner_prior[3,1,type=float]
D_executor_prior[4,1,type=float]
B_planner[3,3,1,type=float]
B_executor[4,4,3,type=float]

## Connections
(D_planner_prior) > (s_planner)
(D_executor_prior) > (s_executor)
(s_planner, B_planner) > (s_planner)
(s_executor, B_executor, s_planner) > (s_executor)

## InitialParameterization
D_planner_prior={ (0.333, 0.333, 0.333) }
D_executor_prior={ (0.25, 0.25, 0.25, 0.25) }
B_planner=identity(3,3,1)
B_executor=identity(4,4,3)

## Time
Dynamic(steps=10)

## ActInfOntologyAnnotation
s_planner=HiddenState
s_executor=HiddenState
D_planner_prior=PriorBelief
D_executor_prior=PriorBelief
B_planner=TransitionMatrix
B_executor=TransitionMatrix
