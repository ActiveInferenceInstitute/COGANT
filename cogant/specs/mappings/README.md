# Mappings — Code-to-GNN and Cross-Language Mappings

Specifications for translating code constructs to GNN tensors and alignments.

## Contents
- code-to-gnn.md — Mapping from program graph to GNN-compatible tensors

## Key mappings
- Program graph nodes → Node embeddings
- Program graph edges → Edge indices and weights
- Symbol types → Type embeddings
- Semantic tags → Label vectors

## Cross-language alignment
Rules for treating equivalent constructs across languages as the same entity:
- Python function ≡ Rust fn
- Python class ≡ Rust struct/trait
- Import statements normalized to canonical form
