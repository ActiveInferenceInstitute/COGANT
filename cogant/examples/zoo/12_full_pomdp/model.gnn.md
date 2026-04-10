## GNNSection
full_pomdp

## GNNVersionAndFlags
GNN v1

## ModelName
full_pomdp

## ModelAnnotation
Complete POMDP Active Inference agent with 5 hidden states, 1 observation modality (noisy state readout), 3 discrete actions, expected free energy policy, and safety constraints on forbidden states. This model exercises every major GNN semantic role.

## StateSpaceBlock
s_hidden[5,1,type=float]
B_transition[5,5,3,type=float]
D_prior[5,1,type=float]

## ObservationBlock
o_sensor[5,type=int]
A_likelihood[5,5,type=float]

## ControlBlock
u_action[3,type=int]
E_habits[3,1,type=float]

## PreferenceBlock
C_preferences[5,1,type=float]

## ConstraintBlock
forbidden_states=[0]
safety_threshold=0.8

## Connections
(D_prior) > (s_hidden)
(s_hidden, B_transition, u_action) > (s_hidden)
(s_hidden, A_likelihood) > (o_sensor)
(s_hidden, C_preferences) > (u_action)
(E_habits) > (u_action)

## InitialParameterization
D_prior={ (0.2, 0.2, 0.2, 0.2, 0.2) }
C_preferences={ (0.05, 0.05, 0.80, 0.05, 0.05) }
A_likelihood={ [[0.8, 0.05, 0.05, 0.05, 0.05], [0.05, 0.8, 0.05, 0.05, 0.05], [0.05, 0.05, 0.8, 0.05, 0.05], [0.05, 0.05, 0.05, 0.8, 0.05], [0.05, 0.05, 0.05, 0.05, 0.8]] }
B_transition=identity(5,5,3)
E_habits={ (0.333, 0.333, 0.333) }

## Time
Dynamic(steps=8)

## ActInfOntologyAnnotation
s_hidden=HiddenState
D_prior=PriorBelief
B_transition=TransitionMatrix
A_likelihood=LikelihoodMatrix
o_sensor=Observation
u_action=Action
C_preferences=Preference
E_habits=HabitVector
