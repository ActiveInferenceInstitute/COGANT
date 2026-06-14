"""Static HTML site scaffold for :class:`cogant.api.Bundle`.

This module contains the HTML/CSS templates that power
:meth:`cogant.api.bundle.Bundle.render_site`. Keeping the templates in
``cogant.viz`` (rather than inline on the ``Bundle`` dataclass) lets the
API layer stay a thin orchestrator that only handles stage-result
plumbing, and lets the presentation layer be tested and tweaked
independently.

The public surface is intentionally small:

* :func:`render_bundle_site` — top-level entry point; creates the
  directory tree and writes the four HTML/CSS files.
* :func:`render_index_html` / :func:`render_graph_html` /
  :func:`render_statespace_html` / :func:`render_css` — individual
  templates. Exposed so callers (tests, alternative renderers) can grab
  a single fragment without touching the filesystem.

The templates match the inline strings that previously lived on
``Bundle._render_*`` so switching to this module is a pure refactor. A richer renderer already exists in
:mod:`cogant.viz.html_renderer`; this module is the minimal fallback
used by ``Bundle.render_site`` and ``cogant render``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from cogant import __version__

logger = logging.getLogger(__name__)

__all__ = [
    "render_bundle_site",
    "render_index_html",
    "render_graph_html",
    "render_statespace_html",
    "render_css",
]


def render_bundle_site(
    output_dir: str | Path,
    *,
    target: str,
    repo_summary: dict[str, Any],
) -> Path:
    """Write the full bundle HTML site to ``output_dir``.

    Creates ``index.html``, ``graph/program_graph.html``,
    ``models/state_space.html``, ``assets/style.css``, and empty
    ``provenance/`` / ``assets/`` directories. Re-runnable; existing
    files are overwritten.

    Args:
        output_dir: Directory to write the site into. Parent directories
            are created if missing.
        target: The target that was analyzed (path or URL). Used as the
            page title on ``index.html``.
        repo_summary: Dict produced by
            :meth:`cogant.api.bundle.Bundle.repo_summary` — must contain
            ``target``, ``file_count``, ``total_errors``, and
            ``language_distribution``.

    Returns:
        Path to the generated ``index.html``.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info("Rendering HTML site to %s", output_path)

    index_html = output_path / "index.html"
    index_html.write_text(
        render_index_html(target=target, repo_summary=repo_summary),
        encoding="utf-8",
    )

    # Create subdirectories — ``provenance/`` stays empty on purpose so
    # the navigation link renders without 404ing the filesystem view.
    (output_path / "graph").mkdir(exist_ok=True)
    (output_path / "models").mkdir(exist_ok=True)
    (output_path / "provenance").mkdir(exist_ok=True)
    (output_path / "assets").mkdir(exist_ok=True)

    graph_html = output_path / "graph" / "program_graph.html"
    graph_html.write_text(render_graph_html(), encoding="utf-8")

    statespace_html = output_path / "models" / "state_space.html"
    statespace_html.write_text(render_statespace_html(), encoding="utf-8")

    css_path = output_path / "assets" / "style.css"
    css_path.write_text(render_css(), encoding="utf-8")

    logger.info("HTML site rendered to %s", index_html)
    return index_html


def render_index_html(*, target: str, repo_summary: dict[str, Any]) -> str:
    """Render the top-level ``index.html`` page.

    Args:
        target: Display string for the page title.
        repo_summary: ``repo_summary()`` output with ``target``,
            ``file_count``, ``total_errors``, ``language_distribution``.

    Returns:
        Complete HTML document as a string.
    """
    languages_html = "".join(
        f"<li>{lang}: {count}</li>" for lang, count in repo_summary["language_distribution"].items()
    )
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>COGANT Analysis: {target}</title>
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <header>
        <h1>COGANT Analysis Report</h1>
        <p>Codebase-to-GNN Translation Engine</p>
    </header>

    <nav>
        <ul>
            <li><a href="index.html">Overview</a></li>
            <li><a href="graph/program_graph.html">Program Graph</a></li>
            <li><a href="models/state_space.html">State Space</a></li>
            <li><a href="provenance/">Provenance</a></li>
        </ul>
    </nav>

    <main>
        <section class="overview">
            <h2>Analysis Summary</h2>
            <dl>
                <dt>Target</dt>
                <dd>{repo_summary["target"]}</dd>
                <dt>Files</dt>
                <dd>{repo_summary["file_count"]}</dd>
                <dt>Errors</dt>
                <dd>{repo_summary["total_errors"]}</dd>
            </dl>
        </section>

        <section class="languages">
            <h2>Language Distribution</h2>
            <ul>
                {languages_html}
            </ul>
        </section>

        <footer>
            <p>Generated by COGANT v{__version__}</p>
        </footer>
    </main>
</body>
</html>
"""


def render_graph_html() -> str:
    """Render the program-graph visualization shell.

    The heavy visualisation is done client-side via D3; this function
    only emits the static shell document and placeholder container.
    """
    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Program Graph Visualization</title>
    <link rel="stylesheet" href="../assets/style.css">
    <script src="https://d3js.org/d3.v7.min.js"></script>
</head>
<body>
    <header>
        <h1>Program Graph</h1>
        <a href="../index.html">Back to Overview</a>
    </header>
    <main>
        <div id="graph-container"></div>
        <script>
            // D3.js visualization placeholder
            console.log("Program graph visualization");
        </script>
    </main>
</body>
</html>
"""


def render_statespace_html() -> str:
    """Render the state-space model page shell."""
    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>State Space Model</title>
    <link rel="stylesheet" href="../assets/style.css">
</head>
<body>
    <header>
        <h1>State Space Model</h1>
        <a href="../index.html">Back to Overview</a>
    </header>
    <main>
        <div id="statespace-container">
            <h2>States</h2>
            <ul id="states-list"></ul>

            <h2>Observations</h2>
            <ul id="observations-list"></ul>

            <h2>Actions</h2>
            <ul id="actions-list"></ul>

            <h2>Policies</h2>
            <ul id="policies-list"></ul>
        </div>
    </main>
</body>
</html>
"""


def render_css() -> str:
    """Return the shared stylesheet as a string."""
    return """
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    margin: 0;
    padding: 0;
    background-color: #f5f5f5;
    color: #333;
}

header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 2rem;
    text-align: center;
}

header h1 {
    margin: 0;
    font-size: 2.5rem;
}

header p {
    margin: 0.5rem 0 0 0;
    font-size: 1rem;
    opacity: 0.9;
}

nav {
    background: white;
    border-bottom: 1px solid #ddd;
    padding: 0;
}

nav ul {
    display: flex;
    list-style: none;
    margin: 0;
    padding: 0;
}

nav li {
    margin: 0;
}

nav a {
    display: block;
    padding: 1rem;
    color: #667eea;
    text-decoration: none;
    border-bottom: 2px solid transparent;
    transition: border-color 0.2s;
}

nav a:hover {
    border-bottom-color: #667eea;
}

main {
    max-width: 1200px;
    margin: 2rem auto;
    padding: 0 1rem;
}

section {
    background: white;
    padding: 2rem;
    margin-bottom: 2rem;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

h2 {
    margin-top: 0;
    color: #667eea;
}

dl {
    display: grid;
    grid-template-columns: 150px 1fr;
    gap: 1rem;
}

dt {
    font-weight: bold;
    color: #666;
}

dd {
    margin: 0;
    color: #333;
}

footer {
    text-align: center;
    color: #999;
    padding: 2rem;
    font-size: 0.9rem;
}

#graph-container {
    width: 100%;
    height: 600px;
    border: 1px solid #ddd;
    border-radius: 4px;
    background: #fafafa;
}
"""
