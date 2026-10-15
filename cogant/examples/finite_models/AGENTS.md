# Finite-model examples

These JSON files are authored generative models, not repositories for the
source-analysis pipeline. Keep each transition kernel total over its declared
state/action axes, and each observation kernel total over its state axis.
Rows with omitted probabilities have unit mass; omitted outcomes have zero mass.

When changing a model, run both `cogant finite compile` and `cogant finite verify`
as shown in README.md, then run the finite-model tests. Keep the plain Python
reference logic in the tests independent of the JSON tables and compiler.
