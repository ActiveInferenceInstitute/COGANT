# PNG Rendering

PNG renderer package for COGANT graph, GNN, state-space, process, Mermaid, and
summary figures.

| Module | Role |
|---|---|
| `orchestrator.py` | Coordinates renderers and writes output bundles. |
| `config.py` / `discovery.py` | Renderer configuration and artifact discovery. |
| `program_graph.py`, `state_space.py`, `markov_blanket.py` | Domain-specific matplotlib renderers. |
| `gnn_markdown.py`, `mermaid.py`, `svg.py`, `dot.py` | Diagram and format-specific renderers. |
| `process_gantt.py`, `summary.py` | Process timeline and summary figures. |

Rendered figures must be valid PNG files and should include enough labels,
legends, and metadata to be interpretable in the manuscript output tree.
