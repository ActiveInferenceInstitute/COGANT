# Agents — py/cogant/viz

## Owner
Visualization and User Interface Lead

## Responsibilities
Generate interactive HTML visualizations of program graphs, semantic models, processes, and validation results. Create self-contained artifacts with embedded charts, Mermaid diagrams, and tabbed interfaces. Support multiple visualization formats and views.

## Key Responsibilities
- Run GraphVisualizer for interactive graph exploration
- Run SemanticVisualizer for state space and model views
- Run GanttRenderer for process timeline visualization
- Run MermaidGenerator for various diagram types
- Run DashboardGenerator for comprehensive interactive dashboards
- Create BoundaryMapper for architectural boundary visualization
- Use StaticPlotter for charts and histograms

## How to Extend
Create new visualizer classes for additional diagram types. Add new view modes to DashboardGenerator. Extend MermaidGenerator with new Mermaid diagram types. Add interactive features to GraphVisualizer (search, filtering, clustering).

## Coordination
- Consumes: ProgramGraph, StateSpaceModel, ProcessModel, ValidationReport
- Produces: Self-contained HTML files consumed by users/browsers
- Works with: export/ for artifact management, validate/ for report integration
