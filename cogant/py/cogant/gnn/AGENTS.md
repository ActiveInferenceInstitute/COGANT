# Agents — py/cogant/gnn

## Owner
GNN Lead

## Responsibilities
- Build complete, self-contained GNN model packages on disk (13+ files: manifest, model.gnn.md, state_space.json, observations.json, actions.json, transitions.json, preferences.json, factors.json, provenance.json, ontology.json, diagrams/, visualizations/)
- Format and validate GNN packages against 18 canonical sections (Model Metadata, Repository Metadata, Source Coverage, State Space, Observation Modalities, Actions/Policies, Connections, Factors, Transition Structure, Likelihood Structure, Preferences/Constraints, Time Settings, Parameterization, Ontology Mapping, Provenance, Confidence Scores, Rendering Hints, Validation Notes)
- Execute GNN models via Active Inference simulation with Variational Free Energy (VFE) and Expected Free Energy (EFE)
- Score packages 0-100 via validator

## Coordination
- Receives ProgramGraph, StateSpaceModel, ProcessModel, SemanticMappings from translate/, statespace/, process/
- Outputs complete, validated GNN packages suitable for model instantiation
- GNNValidator ensures all 18 canonical sections present and well-formed
- GNNModelRunner executes beliefupdate + policy evaluation + action selection loops

## How to extend
Extend GNNPackageBuilder.build() to add new output file types. Extend GNNValidator.CANONICAL_SECTIONS to enforce new section requirements. Extend GNNModelRunner to add new Active Inference components.

## Files
- package.py — GNNPackageBuilder (builds 13+ files, generates manifest with checksums)
- validator.py — GNNValidator (checks all 18 canonical sections present, validates JSON/MD, scores 0-100)
- runner.py — GNNModelRunner (loads package, runs Active Inference with VFE+EFE, tracks ExecutionTrace)
- formatter.py — GNNMarkdownFormatter (formats canonical GNN markdown)
- json_export.py — GNNJSONExporter (exports to machine-readable JSON)
- __init__.py — Public exports
