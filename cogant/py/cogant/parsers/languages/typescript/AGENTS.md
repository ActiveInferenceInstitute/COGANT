# TypeScript parser maintenance

Do not silently claim grammar-level fidelity for the compatibility parser.
Keep the fallback deterministic, preserve source spans, and test both the
fallback and grammar-backed paths when optional dependencies are installed.
