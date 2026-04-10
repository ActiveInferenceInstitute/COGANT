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

        Thin wrapper over :func:`cogant.viz.bundle_site.render_bundle_site`
        — all HTML/CSS templates live in the viz layer so this API stays
        an orchestrator over the bundle state. Creates:

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
        # Lazy import so the viz layer is only pulled in when a caller
        # actually asks for a static site — keeps ``from cogant import
        # Bundle`` cheap for data-only consumers.
        from cogant.viz.bundle_site import render_bundle_site

        return render_bundle_site(
            output_dir,
            target=self.target,
            repo_summary=self.repo_summary(),
        )

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
