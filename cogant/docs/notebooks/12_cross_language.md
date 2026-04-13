<!-- Auto-generated from 12_cross_language.ipynb -->

# 12 — Cross-language Round-trip

Coming soon. This tutorial demonstrates COGANT's cross-language path:
parse a JavaScript snippet with the bundled tree-sitter `LanguagePlugin`,
wrap the result in a `ProgramGraph`, run the forward pipeline through to
GNN roles, and discuss how to measure round-trip fidelity (ε) across a
language boundary.

> **Background:** The `LanguagePlugin` contract the JS plugin implements is
> documented in [api/plugin_api.md](../api/plugin_api.md). The
> language-agnostic `ProgramGraph` layer the forward pipeline operates on is
> described in [concepts/program_graph.md](../concepts/program_graph.md),
> and the ε isomorphism score used to measure round-trip fidelity is
> defined in [concepts/roundtrip.md](../concepts/roundtrip.md).

See [related docs](../index.md) for now.
