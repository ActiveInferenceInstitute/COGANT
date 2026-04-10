"""Session: Manages the full pipeline state and intermediate results."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from cogant.api import orchestration
from cogant.api.bundle import Bundle

logger = logging.getLogger(__name__)


__all__ = ["Session"]


@dataclass
class Session:
    """
    Manages pipeline state and intermediate results for a codebase analysis session.

    Lifecycle:
      1. Session.from_target(path) or Session(repo_path=..., workspace=...)
      2. extract_static() -> static analysis summary
      3. extract_dynamic() -> trace bundle (placeholder unless dynamic hooks enabled)
      4. build_graph() -> ProgramGraph dict
      5. translate_to_gnn() -> GNN-oriented summary
      6. compile_state_space() -> state space summary
      7. export_all(output_dir) -> writes JSON artifacts
    """

    target: str = ""
    """Root path or URL to analyze (set automatically if repo_path is provided)."""

    workspace: str | None = None
    """Optional working directory for future cache/output use."""

    repo_path: Path | None = None
    """If set, initializes target to this path (preferred ergonomic constructor)."""

    created_at: datetime = field(default_factory=datetime.now)

    syntax_tree: dict[str, Any] | None = None
    trace_bundle: dict[str, Any] | None = None
    program_graph: dict[str, Any] | None = None
    gnn_model: dict[str, Any] | None = None
    state_space: dict[str, Any] | None = None
    process_model: dict[str, Any] | None = None

    export_artifacts: dict[str, Path] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    _bundle: Bundle | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Resolve repo_path to an absolute target and validate that a target exists."""
        if self.repo_path is not None:
            object.__setattr__(self, "target", str(Path(self.repo_path).expanduser().resolve()))
        if not self.target:
            raise ValueError("Provide target= or repo_path=")

    def _bundle_internal(self) -> Bundle:
        """Lazily create and return the internal Bundle for this session."""
        if self._bundle is None:
            self._bundle = Bundle(target=self.target, metadata={"workspace": self.workspace})
        return self._bundle

    @classmethod
    def from_target(cls, path_or_url: str) -> Session:
        """Create a session from a filesystem path or URL string."""
        logger.info("Creating session for target: %s", path_or_url)
        return cls(target=path_or_url)

    def extract_static(self) -> dict[str, Any]:
        """Run ingest + static analysis over Python files."""
        logger.info("Extracting static analysis from %s", self.target)
        b = self._bundle_internal()
        ingest_summary = orchestration.run_ingest(self.target, b)
        st = orchestration.run_static(b)
        self.syntax_tree = {
            "type": "syntax_tree",
            "target": self.target,
            "ingest": ingest_summary,
            **st,
        }
        return self.syntax_tree

    def extract_dynamic(
        self,
        coverage_path: str | None = None,
        trace_path: str | None = None,
    ) -> dict[str, Any]:
        """Enrich the program graph with runtime coverage/trace data.

        Ensures the static + graph stages have run so dynamic enrichment
        has a real ``ProgramGraph`` to stitch coverage and trace events
        onto. When no ``coverage_path`` or ``trace_path`` is supplied,
        the enrichment reports zero counts rather than skipping.
        """
        logger.info("Extracting dynamic analysis from %s", self.target)
        b = self._bundle_internal()
        if "repo_snapshot" not in b.artifacts:
            orchestration.run_ingest(self.target, b)
        if "_program_graph" not in b.artifacts:
            if "parsed_modules_detail" not in b.artifacts:
                orchestration.run_static(b)
            if "normalized_facts" not in b.artifacts:
                orchestration.run_normalize(b)
            orchestration.run_graph(b, self.target)
        self.trace_bundle = orchestration.run_dynamic(
            b, coverage_path=coverage_path, trace_path=trace_path
        )
        return self.trace_bundle

    def build_graph(self) -> dict[str, Any]:
        """Normalize facts and build a program graph (runs prerequisites if needed)."""
        logger.info("Building program graph for %s", self.target)
        b = self._bundle_internal()
        if "repo_snapshot" not in b.artifacts:
            orchestration.run_ingest(self.target, b)
        if "parsed_modules_detail" not in b.artifacts:
            orchestration.run_static(b)
        orchestration.run_normalize(b)
        self.program_graph = orchestration.run_graph(b, self.target)
        if self.syntax_tree is None:
            self.syntax_tree = {
                "type": "syntax_tree",
                "target": self.target,
                **b.stage_results.get("static", {}),
            }
        return self.program_graph

    def translate_to_gnn(self) -> dict[str, Any]:
        """Run translation rules over the program graph."""
        logger.info("Translating to GNN representation")
        b = self._bundle_internal()
        if "_program_graph" not in b.artifacts:
            self.build_graph()
        self.gnn_model = orchestration.run_translate(b)
        return self.gnn_model

    def compile_state_space(self) -> dict[str, Any]:
        """Compile a state-space summary from the graph and semantic mappings."""
        logger.info("Compiling state space model")
        b = self._bundle_internal()
        if "_semantic_mappings" not in b.artifacts:
            self.translate_to_gnn()
        self.state_space = orchestration.run_statespace(b, self.target)
        pm = orchestration.run_process(b, self.target)
        self.process_model = pm
        return self.state_space

    def export_all(self, output_dir: str, layout: bool = False) -> Session:
        """Write JSON artifacts for graph, GNN, state space, and process models."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info("Exporting artifacts to %s", output_dir)
        b = self._bundle_internal()
        if "_program_graph" not in b.artifacts:
            self.build_graph()
        if "_semantic_mappings" not in b.artifacts:
            self.translate_to_gnn()
        if "_state_space_model" not in b.artifacts:
            self.compile_state_space()
        orchestration.run_export(b, output_dir)

        for p in b.artifacts.get("export_paths", []):
            path = Path(p)
            key = path.stem
            self.export_artifacts[key] = path

        if self.syntax_tree:
            json_path = output_path / "syntax_tree.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(self.syntax_tree, f, indent=2, default=str)
            self.export_artifacts.setdefault("syntax_tree", json_path)

        if layout:
            from cogant.tools.organize_example_outputs import organize_run_dir

            organize_run_dir(output_path, dry_run=False)

        return self
