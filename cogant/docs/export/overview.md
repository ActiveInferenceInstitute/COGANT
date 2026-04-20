## Overview

COGANT emits artifacts in the formats expected by the GNN ecosystem plus a handful of interop formats for downstream analysis:

- **GNN Markdown (`model.gnn.md`)**: Canonical, human-readable GNN notation organized into 19 sections (Model Metadata, Repository Metadata, Source Coverage, State Space, Observation Modalities, Actions / Policies, Program Graph Connections, Factors, Transition Structure, Likelihood Structure, Preferences / Constraints, Time Settings, Parameterization, Ontology Mapping, Markov Blanket, Provenance, Confidence Scores, Rendering Hints, Validation Notes).
- **GNN JSON (`model.gnn.json`)**: Machine-readable equivalent of the markdown sections.
- **Companion JSON files**: `state_space.json`, `observations.json`, `actions.json`, `transitions.json`, `preferences.json`, `factors.json`, `ontology.json`, `provenance.json`, `connections.json`, `actions_policies.json`, `preferences_constraints.json`.
- **Manifest (`manifest.json`)**: Version, checksums, timestamps for the whole package.
- **GraphML / Parquet**: Interop exports for Gephi/yEd analysis and columnar querying in DuckDB.
- **Execution trace / report**: Produced when the GNN runner is exercised against the compiled model.

### See also

- [JSON export format](json_export_format.md) — typed program-graph JSON vs GNN companions.
- [Artifact ownership](artifact_ownership.md) — which module writes which file.
- [Validation](validation.md) · [See also](see_also.md)
