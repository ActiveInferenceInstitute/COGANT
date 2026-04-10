"""Bundle: Wraps all analysis artifacts with convenient accessors."""

import dataclasses
import json
import logging
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _json_default(obj: Any) -> Any:
    """Best-effort JSON fallback for arbitrary Python objects.

    Pipeline stages stash domain objects (``RepoSnapshot``, typed
    dataclasses, Pydantic models, ``Path`` instances, ``Enum`` values,
    ``set``s, …) on the :class:`Bundle`. ``json.dumps`` cannot handle
    any of those natively, so this function is registered as the
    ``default=`` fallback to coerce them into JSON-native values.

    The coercion order is intentional: we prefer a structured export
    (``model_dump``, ``to_dict``, ``__dict__``, ``dataclasses.asdict``)
    over a lossy ``str()`` cast, and only fall through to ``str()``
    for primitive-like wrappers that do not expose any of those hooks.
    """
    # Pydantic v2 models
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        try:
            return obj.model_dump()
        except Exception:
            pass
    # Explicit to_dict() contract (used by many COGANT schemas)
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        try:
            return obj.to_dict()
        except Exception:
            pass
    # Plain dataclasses
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        try:
            return dataclasses.asdict(obj)
        except Exception:
            pass
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (set, frozenset)):
        return sorted(obj, key=str)
    if hasattr(obj, "__dict__"):
        try:
            return {k: v for k, v in vars(obj).items() if not k.startswith("_")}
        except Exception:
            pass
    return str(obj)


class ArtifactKey(StrEnum):
    """Canonical keys for bundle artifacts populated by pipeline stages."""

    REPO_SNAPSHOT = "repo_snapshot"
    PARSED_MODULES = "parsed_modules_detail"
    NORMALIZED_FACTS = "normalized_facts"
    PROGRAM_GRAPH = "_program_graph"
    SEMANTIC_MAPPINGS = "_semantic_mappings"
    TRANSLATION_ENGINE = "_translation_engine"
    STATE_SPACE_MODEL = "_state_space_model"
    PROCESS_MODEL = "_process_model"
    EXPORT_PATHS = "export_paths"


@dataclass
class Bundle:
    """
    Container for all analysis artifacts and results.

    Provides convenient accessors for:
      - Repo summary
      - Program graph
      - State space model
      - Process model
      - GNN representation
      - Validation report
      - HTML site rendering

    Artifact Keys (populated by pipeline stages in ``self.artifacts``):

    ============================  ================================  =================
    ArtifactKey                   Key string                        Producing stage
    ============================  ================================  =================
    ``REPO_SNAPSHOT``             ``"repo_snapshot"``               ``run_ingest``
    ``PARSED_MODULES``            ``"parsed_modules_detail"``       ``run_static``
    ``NORMALIZED_FACTS``          ``"normalized_facts"``            ``run_normalize``
    ``PROGRAM_GRAPH``             ``"_program_graph"``              ``run_graph``
    ``SEMANTIC_MAPPINGS``         ``"_semantic_mappings"``          ``run_translate``
    ``TRANSLATION_ENGINE``        ``"_translation_engine"``         ``run_translate``
    ``STATE_SPACE_MODEL``         ``"_state_space_model"``          ``run_statespace``
    ``PROCESS_MODEL``             ``"_process_model"``              ``run_process``
    ``EXPORT_PATHS``              ``"export_paths"``                ``run_export``
    ============================  ================================  =================

    Prefer ``bundle.get_artifact(ArtifactKey.PROGRAM_GRAPH)`` over direct
    ``bundle.artifacts["_program_graph"]`` access so that missing artifacts
    produce actionable errors instead of silent ``None`` propagation.
    """

    target: str
    """Target that was analyzed."""

    artifacts: dict[str, Any] = field(default_factory=dict)
    """All generated artifacts (graphs, models, exports)."""

    stage_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    """Results from each pipeline stage."""

    errors: list[str] = field(default_factory=list)
    """Errors encountered during analysis."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Bundle metadata: config, timing, version."""

    def get_artifact(self, key: str, required: bool = False) -> Any:
        """Get an artifact by key with optional required check.

        Args:
            key: Artifact key (prefer ArtifactKey.* constants).
            required: If True, raise KeyError when missing.

        Returns:
            The artifact value, or None if missing and not required.

        Raises:
            KeyError: If required=True and the artifact is missing.
        """
        value = self.artifacts.get(key)
        if required and value is None:
            raise KeyError(
                f"Required artifact {key!r} not found in bundle. "
                f"Ensure the producing stage has run. "
                f"Available artifacts: {sorted(self.artifacts.keys())}"
            )
        return value

    def repo_summary(self) -> dict[str, Any]:
        """
        Get repository summary.

        Returns:
            Summary including file count, languages, structure.
        """
        ingest_result = self.stage_results.get("ingest", {})
        return {
            "target": self.target,
            "file_count": ingest_result.get("file_count", 0),
            "language_distribution": ingest_result.get("language_distribution", {}),
            "total_errors": len(self.errors),
        }

    def program_graph(self) -> dict[str, Any]:
        """
        Get program graph.

        Returns:
            Program dependency graph with nodes and edges.
        """
        return self.stage_results.get("graph", {})

    def state_space_model(self) -> dict[str, Any]:
        """
        Get state space model.

        Returns:
            Semantic state space with states, observations, actions.
        """
        return self.stage_results.get("statespace", {})

    def process_model(self) -> dict[str, Any]:
        """
        Get process/execution model.

        Returns:
            Process model with stages, dependencies, timeline.
        """
        return self.stage_results.get("process", {})

    def gnn_markdown(self) -> str:
        """
        Generate markdown representation of GNN model.

        Returns:
            Formatted markdown string.
        """
        gnn = self.stage_results.get("translate", {})
        lines = [
            "# GNN Model",
            "",
            f"**Target:** {self.target}",
            "",
            "## Node Features",
            f"- Count: {len(gnn.get('node_features', []))}",
            "",
            "## Edge Indices",
            f"- Count: {len(gnn.get('edge_indices', []))}",
            "",
        ]
        return "\n".join(lines)

    def validation_report(self) -> dict[str, Any]:
        """
        Get validation report.

        Returns:
            Validation results with passed status and warnings.
        """
        return self.stage_results.get("validate", {})

    def render_site(self, output_dir: str) -> Path:
        """
        Generate a complete static HTML site.

        Creates:
          - index.html (overview)
          - graph/ (interactive visualizations)
          - models/ (state space, process models)
          - provenance/ (lineage inspector)
          - assets/ (CSS, JS, data files)

        Args:
            output_dir: Directory to write HTML site.

        Returns:
            Path to generated index.html
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Rendering HTML site to {output_dir}")

        # Create index.html
        index_html = output_path / "index.html"
        with open(index_html, "w") as f:
            f.write(self._render_index_html())

        # Create subdirectories
        (output_path / "graph").mkdir(exist_ok=True)
        (output_path / "models").mkdir(exist_ok=True)
        (output_path / "provenance").mkdir(exist_ok=True)
        (output_path / "assets").mkdir(exist_ok=True)

        # Create graph visualization
        graph_html = output_path / "graph" / "program_graph.html"
        with open(graph_html, "w") as f:
            f.write(self._render_graph_html())

        # Create state space visualization
        statespace_html = output_path / "models" / "state_space.html"
        with open(statespace_html, "w") as f:
            f.write(self._render_statespace_html())

        # Create CSS
        css_path = output_path / "assets" / "style.css"
        with open(css_path, "w") as f:
            f.write(self._render_css())

        logger.info(f"HTML site rendered to {index_html}")
        return index_html

    def _render_index_html(self) -> str:
        """Render main index.html page."""
        summary = self.repo_summary()
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>COGANT Analysis: {self.target}</title>
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
                <dd>{summary['target']}</dd>
                <dt>Files</dt>
                <dd>{summary['file_count']}</dd>
                <dt>Errors</dt>
                <dd>{summary['total_errors']}</dd>
            </dl>
        </section>

        <section class="languages">
            <h2>Language Distribution</h2>
            <ul>
                {''.join(f'<li>{lang}: {count}</li>' for lang, count in summary['language_distribution'].items())}
            </ul>
        </section>

        <footer>
            <p>Generated by COGANT v0.1.0</p>
        </footer>
    </main>
</body>
</html>
"""

    def _render_graph_html(self) -> str:
        """Render program graph visualization."""
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

    def _render_statespace_html(self) -> str:
        """Render state space visualization."""
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

    def _render_css(self) -> str:
        """Render CSS stylesheet."""
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

    def to_json(self) -> str:
        """Export bundle as JSON string.

        Bundle state may contain rich Python objects (e.g.
        :class:`RepoSnapshot`, dataclasses, Pydantic models) placed
        there by individual pipeline stages. We serialize them best-effort
        by coercing any non-JSON-native value through ``_json_default``,
        which tries ``model_dump()``, ``to_dict()``, ``__dict__``, and
        ``dataclasses.asdict`` in turn before falling back to ``str()``.
        The result is always valid JSON, so ``save_json`` is safe to
        call immediately after any pipeline run.
        """
        data = {
            "target": self.target,
            "artifacts": self.artifacts,
            "stage_results": self.stage_results,
            "errors": self.errors,
            "metadata": self.metadata,
        }
        return json.dumps(data, indent=2, default=_json_default)

    def save_json(self, path: str) -> None:
        """Save bundle to JSON file."""
        with open(path, "w") as f:
            f.write(self.to_json())
        logger.info(f"Bundle saved to {path}")
