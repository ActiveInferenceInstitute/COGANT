# schema

Current GNN schema detection and validation. The package accepts the active
`GNN v2.0.0` artifact contract and rejects unsupported GNN headers instead of
rewriting older formats. `GNN v2.0.0` is COGANT's own schema identifier; it is
independent of the optional upstream `generalized-notation-notation` package
release (currently the 4.1.0 line). See [AGENTS.md](AGENTS.md), [../AGENTS.md](../AGENTS.md).
For Pydantic program-graph schemas see `schemas/`.
