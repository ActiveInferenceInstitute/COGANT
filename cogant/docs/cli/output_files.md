## Output Files

After running `translate`, the output directory contains:

```
output/
├── bundle.json              # Complete analysis bundle
├── syntax_tree.json         # Static analysis AST
├── program_graph.json       # Program dependency graph
├── gnn_model.json          # GNN representation
├── state_space.json        # Semantic state space
├── process_model.json      # Execution model
└── validation.json         # Validation report
```

After running `render`, the HTML site contains:

```
html_site/
├── index.html              # Overview
├── graph/
│   └── program_graph.html  # Interactive graph
├── models/
│   ├── state_space.html    # State space view
│   └── process.html        # Process model
├── provenance/
│   └── index.html          # Lineage inspector
└── assets/
    ├── style.css           # Styling
    ├── graph-vis.js        # D3.js visualizations
    └── data.json           # Embedded bundle data
```

