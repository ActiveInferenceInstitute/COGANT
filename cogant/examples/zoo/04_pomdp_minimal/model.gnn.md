## GNNSection
pomdp_minimal

## GNNVersionAndFlags
GNN v2.0.0
# COGANT dialect: GNN v2.0.0 is COGANT's own schema identifier
# (cogant.schema.versions.CURRENT_GNN_VERSION), not an upstream
# generalized-notation-notation language version. Every variable used in
# ## Connections is declared in ## StateSpaceBlock below.

## ModelName
pomdp_minimal

## ModelAnnotation
Minimal POMDP agent with discrete states, noisy observations, and greedy action selection. One hidden-state factor (belief over 3 states), one observation modality (noisy state readout), one action factor (2 discrete actions).

## StateSpaceBlock
s_beliefs[3,1,type=float]
B_transition[3,3,1,type=float]
A_observation[3,3,type=float]
D_prior[3,1,type=float]
o_sensor[3,type=int]
u_action[2,type=int]

## Connections
(D_prior) > (s_beliefs)
(s_beliefs, B_transition) > (s_beliefs)
(s_beliefs, A_observation) > (o_sensor)
(s_beliefs) > (u_action)

## InitialParameterization
D_prior={ (0.333, 0.333, 0.333) }
B_transition=identity(3,3,1)
A_observation={ [[0.8, 0.1, 0.1], [0.1, 0.8, 0.1], [0.1, 0.1, 0.8]] }

## Time
Dynamic(steps=5)

## ActInfOntologyAnnotation
s_beliefs=HiddenState
D_prior=PriorBelief
B_transition=TransitionMatrix
A_observation=LikelihoodMatrix
o_sensor=Observation
u_action=Action

## Footer
COGANT zoo reference specimen `pomdp_minimal`: a belief state over three hidden
states, a transition tensor, a likelihood matrix, and a prior, with one
observation modality (`o_sensor`) and one action factor (`u_action`).
