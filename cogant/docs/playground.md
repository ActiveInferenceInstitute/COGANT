# Playground

The interactive **COGANT Playground** is a single-page editor and graph preview shipped as [`playground.html`](playground.html) next to this file. It is not yet linked from the main nav as a polished product surface; use it for local experiments.

## Local preview

After `mkdocs build` or `mkdocs serve`, open **`playground.html`** from the site root (same path as in the docs source: `docs/playground.html`). CDN behaviour, offline use, and integrity pinning are summarized below.

## CDN assets (supply chain)

[`playground.html`](playground.html) loads **CodeMirror 5** and **Cytoscape.js** from **cdnjs** with **`integrity`** (sha384) and **`crossorigin="anonymous"`** on each `<link>` / `<script>` so tampered responses fail closed. Recompute hashes when you bump library versions (see the comment block in `playground.html` immediately above those tags).

- **Offline / air-gapped:** the page does not render the editor or graph until those URLs resolve; vendor copies locally if you require offline use.
- **Trust boundary:** treat the playground as **developer-local tooling**, not an authenticated surface; do not paste secrets into it.

See also [Dependency Security](security/dependency_security.md) for repo-wide supply-chain posture.

## Related

- [Documentation home](index.md)
- [CLI reference](cli_reference.md)
