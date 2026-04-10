## Introduction

**COGANT** (Codebase-to-GNN Translation) is a system for translating arbitrary source code into representations compatible with the Active Inference Institute's **Generalized Notation Notation** (GNN) — a structured, machine-parsable notation for Active Inference state-space and process models (not to be confused with graph neural networks). It bridges program analysis and cognitive modeling by providing:

- **Multi-language support (roadmap)** — Python is the primary focus at v0.1.x; Java, JavaScript, Rust, and C/C++ are design targets as front-ends mature (see [Implementation status](#implementation-status) and the [README](https://github.com/cogant-contributors/cogant/blob/main/cogant/README.md) honest-scope section).
- **Unified semantic representation** (Program Graph IR)
- **Flexible translation** (pluggable rules engine mapping code structure to hidden states, observations, actions, policies)
- **GNN-ready exports** (canonical 18-section Markdown bundle, JSON, GraphML, Parquet)
- **Transparent provenance** (track every inference back to source evidence)
- **Confidence scoring** (explicit uncertainty quantification)

