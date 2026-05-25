# ruff: noqa: E501
"""HTMLSiteRenderer: Generate complete static HTML site with all views."""

import json
import logging
from pathlib import Path
from typing import Any

from cogant.viz.cytoscape_view import build_cytoscape_html

logger = logging.getLogger(__name__)


class HTMLSiteRenderer:
    """
    Generate a complete static HTML site for analysis results.

    Creates:
      - index.html (overview and navigation)
      - graph/ (program graph visualizations)
      - models/ (state space and process models)
      - provenance/ (lineage inspector)
      - assets/ (CSS, JavaScript, data files)
    """

    def __init__(self, bundle: dict[str, Any]):
        """
        Initialize renderer.

        Args:
            bundle: Analysis bundle to render.
        """
        self.bundle = bundle
        # ``output_dir`` is set by ``render()`` before any of the
        # private ``_emit_*`` helpers read it. Typing as ``Path`` rather
        # than ``Path | None`` avoids a cascade of operator errors in
        # the ``self.output_dir / "..."`` expressions below without
        # hiding any real null dereference.
        self.output_dir: Path = Path(".")

    def render(self, output_dir: str) -> Path:
        """
        Generate complete HTML site.

        Args:
            output_dir: Directory to write site to.

        Returns:
            Path to index.html
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Rendering HTML site to {output_dir}")

        # Create subdirectories
        (self.output_dir / "graph").mkdir(exist_ok=True)
        (self.output_dir / "models").mkdir(exist_ok=True)
        (self.output_dir / "provenance").mkdir(exist_ok=True)
        (self.output_dir / "assets").mkdir(exist_ok=True)

        # Render pages
        self._render_index()
        self._render_graph()
        self._render_models()
        self._render_provenance()
        self._render_assets()
        self._render_data()

        index_path = self.output_dir / "index.html"
        logger.info(f"HTML site rendered to {index_path}")
        return index_path

    def _render_index(self) -> None:
        """Render main index page."""
        self.bundle.get("artifacts", {})
        errors = len(self.bundle.get("errors", []))
        target_name = self.bundle.get("target", "Unknown")
        stage_results = self.bundle.get("stage_results", {})
        stages_completed = len(stage_results)
        stage_list_html = "".join(
            self._render_stage_item(stage)
            for stage in [
                "ingest",
                "static",
                "normalize",
                "graph",
                "translate",
                "statespace",
                "process",
                "export",
                "validate",
            ]
        )
        errors_style = "" if errors > 0 else "display: none;"
        error_list_html = "".join(
            f"<li>{error}</li>" for error in self.bundle.get("errors", [])[:10]
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>COGANT Analysis Report</title>
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <header class="header">
        <div class="container">
            <h1>COGANT Analysis Report</h1>
            <p>Codebase-to-GNN Translation Engine</p>
        </div>
    </header>

    <nav class="navbar">
        <div class="container">
            <ul>
                <li><a href="index.html" class="active">Overview</a></li>
                <li><a href="graph/program_graph.html">Program Graph</a></li>
                <li><a href="graph/force_graph.html">Force-Directed View</a></li>
                <li><a href="models/state_space.html">State Space</a></li>
                <li><a href="models/process.html">Process</a></li>
                <li><a href="provenance/index.html">Provenance</a></li>
            </ul>
        </div>
    </nav>

    <main class="container">
        <section class="hero">
            <h2>Analysis Summary</h2>
            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{target_name}</div>
                    <div class="stat-label">Target</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{stages_completed} / 9</div>
                    <div class="stat-label">Stages Completed</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{errors}</div>
                    <div class="stat-label">Errors</div>
                </div>
            </div>
        </section>

        <section class="pipeline">
            <h2>Pipeline Status</h2>
            <div class="stage-list">
                {stage_list_html}
            </div>
        </section>

        <section class="errors" style="{errors_style}">
            <h2>Errors</h2>
            <ul>
                {error_list_html}
            </ul>
        </section>

        <footer class="footer">
            <p>Generated by <strong>COGANT v0.1.0</strong></p>
            <p>Codebase-to-GNN Translation Engine</p>
        </footer>
    </main>
</body>
</html>
"""
        with open(self.output_dir / "index.html", "w") as f:
            f.write(html)

    def _render_stage_item(self, stage: str) -> str:
        """Render single pipeline stage."""
        stage_results = self.bundle.get("stage_results", {})
        completed = stage in stage_results
        status = "completed" if completed else "pending"
        icon = "✓" if completed else "○"

        return f"""
        <div class="stage-item {status}">
            <span class="stage-icon">{icon}</span>
            <span class="stage-name">{stage}</span>
        </div>
        """

    def _render_graph(self) -> None:
        """Render program graph pages (classic D3 stub + cytoscape force view)."""
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Program Graph</title>
    <link rel="stylesheet" href="../assets/style.css">
    <script src="https://d3js.org/d3.v7.min.js"></script>
</head>
<body>
    <header class="header">
        <div class="container">
            <h1>Program Graph</h1>
        </div>
    </header>

    <nav class="navbar">
        <div class="container">
            <ul>
                <li><a href="../index.html">Overview</a></li>
                <li><a href="program_graph.html" class="active">Program Graph</a></li>
                <li><a href="force_graph.html">Force-Directed View</a></li>
                <li><a href="../models/state_space.html">State Space</a></li>
            </ul>
        </div>
    </nav>

    <main class="container">
        <section>
            <div id="graph-container" style="width: 100%; height: 600px; background: #f9f9f9; border: 1px solid #ddd; border-radius: 4px;"></div>
            <p style="color: #999; text-align: center; margin-top: 10px;">Interactive program dependency graph (drag to move, scroll to zoom)</p>
            <p style="text-align: center; margin-top: 14px;">
                See also the
                <a href="force_graph.html"><strong>force-directed (cytoscape.js)</strong></a>
                view — nodes coloured by AI role, sized by degree.
            </p>
        </section>

        <section style="margin-top: 40px;">
            <h2>Graph Statistics</h2>
            <dl>
                <dt>Nodes</dt>
                <dd id="node-count">Loading...</dd>
                <dt>Edges</dt>
                <dd id="edge-count">Loading...</dd>
            </dl>
        </section>

        <footer class="footer">
            <p>Generated by COGANT</p>
        </footer>
    </main>

    <script src="../assets/graph-vis.js"></script>
</body>
</html>
"""
        with open(self.output_dir / "graph" / "program_graph.html", "w") as f:
            f.write(html)

        # Also render the cytoscape.js force-directed view. The graph payload
        # is pulled from the bundle so the same renderer can serve both a
        # full pipeline bundle and lightweight test bundles.
        graph_payload = self._extract_graph_payload()
        mappings_payload = self._extract_semantic_mappings()
        force_html = build_cytoscape_html(graph_payload, mappings_payload)
        with open(self.output_dir / "graph" / "force_graph.html", "w") as f:
            f.write(force_html)

    def _extract_graph_payload(self) -> dict[str, Any]:
        """Best-effort extraction of a program-graph dict from the bundle.

        Looks in a handful of well-known locations so that both the typed
        ``PipelineRunner`` bundle and legacy / ad-hoc bundles can render.
        Always returns a dict with ``nodes`` and ``edges`` keys.
        """
        candidates: list[Any] = [
            self.bundle.get("program_graph"),
            self.bundle.get("graph"),
            (self.bundle.get("stage_results", {}) or {}).get("graph"),
            (self.bundle.get("artifacts", {}) or {}).get("program_graph"),
        ]
        for candidate in candidates:
            if isinstance(candidate, dict) and ("nodes" in candidate or "edges" in candidate):
                return {
                    "nodes": candidate.get("nodes", []),
                    "edges": candidate.get("edges", []),
                }
        return {"nodes": [], "edges": []}

    def _extract_statespace_payload(self) -> dict[str, Any]:
        """Best-effort extraction of state-space data for the assets bundle.

        Looks at the typed bundle artifacts and the loosely-typed
        ``stage_results['statespace']`` shape so the renderer works for
        both pipeline runs and direct loads of ``state_space.json``.
        """
        candidates: list[Any] = [
            (self.bundle.get("artifacts", {}) or {}).get("_state_space_model"),
            (self.bundle.get("stage_results", {}) or {}).get("statespace"),
            self.bundle.get("state_space"),
        ]
        for candidate in candidates:
            if isinstance(candidate, dict):
                return {
                    "states": candidate.get("states") or candidate.get("variables") or [],
                    "observations": candidate.get("observations") or [],
                    "actions": candidate.get("actions") or [],
                }
        return {"states": [], "observations": [], "actions": []}

    def _extract_process_payload(self) -> dict[str, Any]:
        """Best-effort extraction of process-model stage data."""
        candidates: list[Any] = [
            (self.bundle.get("artifacts", {}) or {}).get("_process_model"),
            (self.bundle.get("stage_results", {}) or {}).get("process"),
            self.bundle.get("process_model"),
        ]
        for candidate in candidates:
            if isinstance(candidate, dict):
                return {
                    "stages": candidate.get("stages") or candidate.get("steps") or [],
                    "dependencies": candidate.get("dependencies") or [],
                }
        return {"stages": [], "dependencies": []}

    def _extract_provenance_payload(self) -> dict[str, Any]:
        """Build a provenance summary from bundle metadata."""
        return {
            "target": self.bundle.get("target", ""),
            "metadata": self.bundle.get("metadata", {}),
            "stages_completed": sorted((self.bundle.get("stage_results", {}) or {}).keys()),
            "errors": list(self.bundle.get("errors", []) or []),
        }

    def _extract_semantic_mappings(self) -> list[Any]:
        """Best-effort extraction of semantic mappings for role colouring."""
        candidates: list[Any] = [
            self.bundle.get("semantic_mappings"),
            self.bundle.get("mappings"),
            (self.bundle.get("stage_results", {}) or {}).get("translate"),
        ]
        for candidate in candidates:
            if isinstance(candidate, list):
                return candidate
            if isinstance(candidate, dict) and "mappings" in candidate:
                inner = candidate.get("mappings")
                if isinstance(inner, list):
                    return inner
        return []

    def _render_models(self) -> None:
        """Render state space and process model pages."""
        # State space
        html_ss = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>State Space Model</title>
    <link rel="stylesheet" href="../assets/style.css">
</head>
<body>
    <header class="header">
        <div class="container">
            <h1>State Space Model</h1>
        </div>
    </header>

    <main class="container">
        <section>
            <h2>States</h2>
            <ul id="states-list"></ul>
        </section>
        <section>
            <h2>Observations</h2>
            <ul id="observations-list"></ul>
        </section>
        <footer class="footer">
            <p>Generated by COGANT</p>
        </footer>
    </main>

    <script src="../assets/statespace-data.js"></script>
</body>
</html>
"""
        with open(self.output_dir / "models" / "state_space.html", "w") as f:
            f.write(html_ss)

        # Process model
        html_proc = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Process Model</title>
    <link rel="stylesheet" href="../assets/style.css">
</head>
<body>
    <header class="header">
        <div class="container">
            <h1>Process/Execution Model</h1>
        </div>
    </header>

    <main class="container">
        <section>
            <h2>Pipeline Stages</h2>
            <div id="gantt-chart"></div>
        </section>
        <footer class="footer">
            <p>Generated by COGANT</p>
        </footer>
    </main>

    <script src="../assets/process-data.js"></script>
</body>
</html>
"""
        with open(self.output_dir / "models" / "process.html", "w") as f:
            f.write(html_proc)

    def _render_provenance(self) -> None:
        """Render provenance inspector."""
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Provenance Inspector</title>
    <link rel="stylesheet" href="../assets/style.css">
</head>
<body>
    <header class="header">
        <div class="container">
            <h1>Provenance Inspector</h1>
        </div>
    </header>

    <main class="container">
        <section>
            <h2>Analysis Lineage</h2>
            <p>Shows the complete lineage of analysis artifacts, including:</p>
            <ul>
                <li>Input data and sources</li>
                <li>Processing stages and transformations</li>
                <li>Output artifacts and their dependencies</li>
                <li>Validation results</li>
            </ul>
        </section>

        <section>
            <h2>Metadata</h2>
            <pre id="metadata" style="background: #f5f5f5; padding: 15px; border-radius: 4px; overflow-x: auto;">
Loading metadata...
            </pre>
        </section>

        <footer class="footer">
            <p>Generated by COGANT</p>
        </footer>
    </main>

    <script src="../assets/provenance-data.js"></script>
</body>
</html>
"""
        with open(self.output_dir / "provenance" / "index.html", "w") as f:
            f.write(html)

    def _render_assets(self) -> None:
        """Render CSS and JavaScript files."""
        # Main CSS
        css = """
/* COGANT - Modern CSS */

:root {
    --primary: #667eea;
    --secondary: #764ba2;
    --success: #43e97b;
    --danger: #f5576c;
    --warning: #ffd89b;
    --info: #4facfe;
    --light: #f9f9f9;
    --dark: #333;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #f5f5f5;
    color: #333;
    line-height: 1.6;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}

.header {
    background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
    color: white;
    padding: 40px 0;
    text-align: center;
}

.header h1 {
    font-size: 2.5rem;
    margin-bottom: 10px;
}

.header p {
    opacity: 0.9;
    font-size: 1.1rem;
}

.navbar {
    background: white;
    border-bottom: 1px solid #ddd;
    position: sticky;
    top: 0;
    z-index: 100;
}

.navbar ul {
    display: flex;
    list-style: none;
}

.navbar li {
    margin: 0;
}

.navbar a {
    display: block;
    padding: 15px 20px;
    color: var(--primary);
    text-decoration: none;
    border-bottom: 3px solid transparent;
    transition: border-color 0.3s, color 0.3s;
}

.navbar a:hover,
.navbar a.active {
    border-bottom-color: var(--primary);
    color: var(--secondary);
}

main {
    background: white;
    margin: 30px auto;
    padding: 40px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

section {
    margin-bottom: 40px;
}

section h2 {
    color: var(--primary);
    border-bottom: 2px solid var(--primary);
    padding-bottom: 10px;
    margin-bottom: 20px;
}

.stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin: 20px 0;
}

.stat {
    background: linear-gradient(135deg, var(--light) 0%, white 100%);
    border: 1px solid #ddd;
    padding: 20px;
    border-radius: 8px;
    text-align: center;
}

.stat-value {
    font-size: 2rem;
    font-weight: bold;
    color: var(--primary);
}

.stat-label {
    color: #666;
    margin-top: 10px;
}

.stage-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.stage-item {
    display: flex;
    align-items: center;
    padding: 15px;
    background: #f9f9f9;
    border-left: 4px solid #ddd;
    border-radius: 4px;
    transition: all 0.3s;
}

.stage-item.completed {
    border-left-color: var(--success);
    background: #f0fdf4;
}

.stage-item.pending {
    border-left-color: #ffd89b;
    background: #fffbf0;
}

.stage-icon {
    font-weight: bold;
    color: #666;
    min-width: 30px;
    text-align: center;
}

.stage-item.completed .stage-icon {
    color: var(--success);
}

.stage-name {
    flex: 1;
    font-weight: 500;
    color: #333;
}

.hero {
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
    padding: 40px;
    border-radius: 8px;
    text-align: center;
    margin-bottom: 40px;
}

.errors {
    background: #fdf2f8;
    border-left: 4px solid var(--danger);
    padding: 20px;
    border-radius: 4px;
}

.errors ul {
    list-style: none;
    padding: 0;
}

.errors li {
    padding: 10px 0;
    border-bottom: 1px solid #eee;
    color: #c7254e;
}

.errors li:last-child {
    border-bottom: none;
}

.footer {
    text-align: center;
    color: #999;
    padding: 40px 0;
    border-top: 1px solid #ddd;
    margin-top: 40px;
}

@media (max-width: 768px) {
    .header h1 {
        font-size: 1.8rem;
    }

    main {
        padding: 20px;
    }

    .navbar ul {
        flex-wrap: wrap;
    }

    .navbar a {
        padding: 10px 15px;
        font-size: 0.9rem;
    }
}
"""
        with open(self.output_dir / "assets" / "style.css", "w") as f:
            f.write(css)

        # ------------------------------------------------------------------
        # Each *-data.js file is a self-contained vanilla-JS module that
        # ships the real bundle-derived data inline (so pages render even
        # when opened from disk without a server) plus the small renderer
        # that turns it into the DOM elements the matching HTML page
        # already declares (#node-count, #states-list, #gantt-chart, …).
        # ------------------------------------------------------------------
        graph_payload = self._extract_graph_payload()
        statespace_payload = self._extract_statespace_payload()
        process_payload = self._extract_process_payload()
        provenance_payload = self._extract_provenance_payload()

        def _data_literal(payload: Any) -> str:
            return json.dumps(payload, indent=2, sort_keys=True, default=str)

        graph_js = f"""// Auto-generated by cogant.viz.html_renderer
// Real program-graph payload extracted from the bundle.
window.GRAPH_DATA = {_data_literal(graph_payload)};

(function renderGraphSummary() {{
    function setText(id, value) {{
        var el = document.getElementById(id);
        if (el) {{ el.textContent = String(value); }}
    }}
    function ready(fn) {{
        if (document.readyState !== 'loading') {{ fn(); }}
        else {{ document.addEventListener('DOMContentLoaded', fn); }}
    }}
    ready(function () {{
        var data = window.GRAPH_DATA || {{ nodes: [], edges: [] }};
        var nodes = data.nodes || [];
        var edges = data.edges || [];
        setText('node-count', nodes.length);
        setText('edge-count', edges.length);
        var container = document.getElementById('graph-container');
        if (container && nodes.length) {{
            var max = 50;
            var rows = nodes.slice(0, max).map(function (n) {{
                var name = (n && (n.name || n.id || '')).toString();
                var kind = (n && (n.kind || n.type || '')).toString();
                return '<tr><td>' + name + '</td><td>' + kind + '</td></tr>';
            }}).join('');
            container.innerHTML =
                '<table style="width:100%;border-collapse:collapse">' +
                '<thead><tr><th style="text-align:left">Node</th>' +
                '<th style="text-align:left">Kind</th></tr></thead>' +
                '<tbody>' + rows + '</tbody></table>' +
                (nodes.length > max
                    ? '<p style="color:#999;text-align:center">Showing ' +
                      max + ' of ' + nodes.length + ' nodes.</p>'
                    : '');
        }}
    }});
}})();
"""
        with open(self.output_dir / "assets" / "graph-vis.js", "w") as f:
            f.write(graph_js)

        ss_js = f"""// Auto-generated by cogant.viz.html_renderer
window.STATE_SPACE_DATA = {_data_literal(statespace_payload)};

(function renderStateSpace() {{
    function ready(fn) {{
        if (document.readyState !== 'loading') {{ fn(); }}
        else {{ document.addEventListener('DOMContentLoaded', fn); }}
    }}
    function fillList(id, items) {{
        var el = document.getElementById(id);
        if (!el) {{ return; }}
        if (!items || !items.length) {{
            el.innerHTML = '<li style="color:#999">(none)</li>';
            return;
        }}
        el.innerHTML = items.map(function (it) {{
            var label = (typeof it === 'string') ? it
                : (it && (it.name || it.id || JSON.stringify(it)));
            return '<li>' + label + '</li>';
        }}).join('');
    }}
    ready(function () {{
        var d = window.STATE_SPACE_DATA || {{}};
        fillList('states-list', d.states || d.variables || []);
        fillList('observations-list', d.observations || []);
    }});
}})();
"""
        with open(self.output_dir / "assets" / "statespace-data.js", "w") as f:
            f.write(ss_js)

        proc_js = f"""// Auto-generated by cogant.viz.html_renderer
window.PROCESS_DATA = {_data_literal(process_payload)};

(function renderProcess() {{
    function ready(fn) {{
        if (document.readyState !== 'loading') {{ fn(); }}
        else {{ document.addEventListener('DOMContentLoaded', fn); }}
    }}
    ready(function () {{
        var el = document.getElementById('gantt-chart');
        if (!el) {{ return; }}
        var d = window.PROCESS_DATA || {{}};
        var stages = d.stages || [];
        if (!stages.length) {{
            el.innerHTML = '<p style="color:#999">No process stages recorded.</p>';
            return;
        }}
        var rows = stages.map(function (s, i) {{
            var name = (typeof s === 'string') ? s
                : (s && (s.name || s.id || ('stage_' + i)));
            var dur = (s && (s.duration_ms || s.duration || ''));
            return '<tr><td>' + (i + 1) + '</td><td>' + name +
                   '</td><td style="text-align:right">' + dur + '</td></tr>';
        }}).join('');
        el.innerHTML =
            '<table style="width:100%;border-collapse:collapse">' +
            '<thead><tr><th>#</th><th style="text-align:left">Stage</th>' +
            '<th style="text-align:right">Duration (ms)</th></tr></thead>' +
            '<tbody>' + rows + '</tbody></table>';
    }});
}})();
"""
        with open(self.output_dir / "assets" / "process-data.js", "w") as f:
            f.write(proc_js)

        prov_js = f"""// Auto-generated by cogant.viz.html_renderer
window.PROVENANCE_DATA = {_data_literal(provenance_payload)};

(function renderProvenance() {{
    function ready(fn) {{
        if (document.readyState !== 'loading') {{ fn(); }}
        else {{ document.addEventListener('DOMContentLoaded', fn); }}
    }}
    ready(function () {{
        var el = document.getElementById('metadata');
        if (!el) {{ return; }}
        try {{
            el.textContent = JSON.stringify(
                window.PROVENANCE_DATA || {{}}, null, 2
            );
        }} catch (e) {{
            el.textContent = String(e);
        }}
    }});
}})();
"""
        with open(self.output_dir / "assets" / "provenance-data.js", "w") as f:
            f.write(prov_js)

    def _render_data(self) -> None:
        """Render embedded data files."""
        # Create a data.json file with all bundle data
        data_file = self.output_dir / "assets" / "data.json"
        with open(data_file, "w") as f:
            json.dump(self.bundle, f, indent=2)

        logger.info(f"Bundle data written to {data_file}")
