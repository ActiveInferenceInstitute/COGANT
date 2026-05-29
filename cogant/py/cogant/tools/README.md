# Tools — Output Organization and Visualization Rendering

Optional utility scripts for post-processing COGANT pipeline outputs. Organize flat artifact directories into structured layouts and render visualizations from analysis results.

## Functions and Classes

organize_example_outputs module: organize_run_dir (moves artifacts from flat directory into data/, diagrams/, figures/, site/, reports/ subdirectories based on filename patterns), migrate_output_tree (moves output/name to output/examples/suite/name and organizes each). Reads _DEST mapping of filenames to destination folders. Rewrites HTML links in index.html to use ../data/, ../diagrams/, etc. Returns organized directory path.

render_output_figures module: render_program_graph_png (converts program_graph.json to PNG visualization), render_graphviz_dot_to_png (renders .dot files with Graphviz), render_all_mermaid_in_run (finds and renders all .mermaid diagram files in run directory), find_graph_dot (locates graph.dot file in run directory). Main entry point discovers run directories recursively and processes each with _process_run_dir.

## Usage Example

```python
from cogant.tools.organize_example_outputs import organize_run_dir
from pathlib import Path

# After pipeline completion, organize flat output
output_path = Path("output/my_run")
organize_run_dir(output_path, dry_run=False)

# Result: output/my_run/data/, output/my_run/diagrams/, etc.
```

```bash
# Render PNG figures for a run directory
python -m cogant.tools.render_output_figures output/my_run
```

## Layout Conventions

After organization, run directory structure is:

- data/ — JSON exports (program_graph.json, semantic_mappings.json, state_space.json, etc.)
- diagrams/ — Mermaid and Graphviz .dot files
- figures/ — Rendered PNG images (program_graph.png, mermaid diagrams as PNG)
- site/ — Static HTML pages with relative links
- reports/ — Markdown summaries and model documentation

## Dependencies

organize_example_outputs: pathlib, re (regex rewriting), shutil (file operations), logging.

render_output_figures: cogant.viz.png (find_graph_dot, render_program_graph_png, render_graphviz_dot_to_png, render_all_mermaid_in_run), pathlib, logging, argparse.
