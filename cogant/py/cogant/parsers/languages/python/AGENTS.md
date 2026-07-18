# Python parser maintenance

Keep the standard-library AST path deterministic and independent of optional
tree-sitter packages. Preserve file and source-span provenance, and add
regression fixtures for every new AST node or normalization rule.
