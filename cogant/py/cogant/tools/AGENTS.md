# Agents — py/cogant/tools

## Owner

Frontend Lead (with Infra Lead coordination)

## Responsibilities

Provide optional post-processing utilities for organizing pipeline outputs and rendering visualizations. Organize flat artifact directories into structured layouts (data/, diagrams/, figures/, site/, reports/). Render PNG visualizations from program graphs and diagram files. Support example and demo workflows.

## Extending

Add new artifact organization patterns to organize_example_outputs._DEST mapping. Create new rendering functions in render_output_figures following the pattern of render_program_graph_png (input file, output path, logging). Ensure both modules handle missing files gracefully and report via logging.

## Coordination

Receives outputs from api/ (pipeline artifacts) and can integrate with viz/ for visualization support. Works standalone; tools/ functions are optional called after export stage completes. Used by PipelineConfig.layout_output post-processing and Session.export_all(layout=True).

## Files

organize_example_outputs.py: organize_run_dir function moves files from flat directory into data/, diagrams/, figures/, site/, reports/ based on _DEST filename mapping. Rewrites index.html href attributes to use ../data/, etc. migrate_output_tree function moves output/name to output/examples/suite/name and organizes each recursively.

render_output_figures.py: render_program_graph_png (PNG from JSON graph), render_graphviz_dot_to_png (PNG from Graphviz dot), render_all_mermaid_in_run (PNG from .mermaid files), find_graph_dot (locates dot files). Main entry point handles CLI invocation with path discovery and batch processing.

__init__.py: Module marker (minimal exports).
