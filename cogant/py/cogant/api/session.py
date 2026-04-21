"""Session: Manages the full pipeline state and intermediate results."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from cogant.api import orchestration
from cogant.api.bundle import Bundle

logger = logging.getLogger(__name__)


class SessionStatus(StrEnum):
    """Enumeration of session lifecycle states."""

    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


__all__ = ["Session", "SessionStatus", "SessionManager"]


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
    status: SessionStatus = field(default=SessionStatus.CREATED)
    """Current session lifecycle state."""

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
        n_modules = len(st.get("modules", [])) if isinstance(st, dict) else 0
        logger.info(
            "Static analysis complete: %d modules extracted from %s",
            n_modules,
            self.target,
        )
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
        n_nodes = (
            len(self.program_graph.get("nodes", {})) if isinstance(self.program_graph, dict) else 0
        )
        n_edges = (
            len(self.program_graph.get("edges", {})) if isinstance(self.program_graph, dict) else 0
        )
        logger.info(
            "Program graph built: %d nodes, %d edges",
            n_nodes,
            n_edges,
        )
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
        n_mappings = (
            self.gnn_model.get("mapping_count") if isinstance(self.gnn_model, dict) else 0
        ) or 0
        logger.info(
            "Translation complete: %d semantic mappings",
            n_mappings,
        )
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
        ss = self.state_space if isinstance(self.state_space, dict) else {}
        n_vars = len(ss.get("states", []) or [])
        n_obs = len(ss.get("observations", []) or [])
        n_actions = len(ss.get("actions", []) or [])
        logger.info(
            "State space compiled: %d vars, %d obs, %d actions",
            n_vars,
            n_obs,
            n_actions,
        )
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
        n_artifacts = len(self.export_artifacts)
        logger.info(
            "Export complete: %d artifacts written to %s",
            n_artifacts,
            output_dir,
        )

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

    def to_dict(self) -> dict[str, Any]:
        """Serialize the session to a JSON-compatible dict.

        Returns:
            Dictionary with all session state. Large nested structures
            (like the internal bundle) are excluded; only the session's
            summary data is included.
        """
        return {
            "target": self.target,
            "workspace": self.workspace,
            "repo_path": str(self.repo_path) if self.repo_path else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "status": self.status.value
            if isinstance(self.status, SessionStatus)
            else str(self.status),
            "syntax_tree": self.syntax_tree,
            "trace_bundle": self.trace_bundle,
            "program_graph": self.program_graph,
            "gnn_model": self.gnn_model,
            "state_space": self.state_space,
            "process_model": self.process_model,
            "export_artifacts": {k: str(v) for k, v in self.export_artifacts.items()},
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        """Reconstruct a session from a serialized dict.

        Args:
            data: Dictionary produced by :func:`to_dict`.

        Returns:
            A new Session instance with the persisted state.
        """
        created_at_str = data.get("created_at")
        created_at = datetime.fromisoformat(created_at_str) if created_at_str else datetime.now()

        repo_path_str = data.get("repo_path")
        repo_path = Path(repo_path_str) if repo_path_str else None

        session = cls(
            target=data.get("target", ""),
            workspace=data.get("workspace"),
            repo_path=repo_path,
        )
        object.__setattr__(session, "created_at", created_at)
        session.syntax_tree = data.get("syntax_tree")
        session.trace_bundle = data.get("trace_bundle")
        session.program_graph = data.get("program_graph")
        session.gnn_model = data.get("gnn_model")
        session.state_space = data.get("state_space")
        session.process_model = data.get("process_model")

        export_artifacts_data = data.get("export_artifacts", {})
        session.export_artifacts = {k: Path(v) for k, v in export_artifacts_data.items()}

        session.metadata = data.get("metadata", {})

        status_str = data.get("status", "created")
        try:
            session.status = SessionStatus(status_str)
        except ValueError:
            session.status = SessionStatus.CREATED

        return session


@dataclass
class SessionManager:
    """Manages a collection of sessions with lifecycle tracking.

    Handles session creation, expiration, and basic statistics collection.

    Attributes:
        ttl_seconds: Time-to-live for sessions in seconds. Sessions older
            than this are considered expired.
    """

    ttl_seconds: int = 3600  # 1 hour default
    _sessions: dict[str, Session] = field(default_factory=dict)

    def create(self, target: str, workspace: str | None = None) -> tuple[str, Session]:
        """Create a new session.

        Args:
            target: Repository path or URL.
            workspace: Optional working directory.

        Returns:
            A tuple of ``(session_id, session)`` where ``session_id`` is a
            UUID string suitable for use as a key.
        """
        import uuid

        session_id = str(uuid.uuid4())
        session = Session(target=target, workspace=workspace)
        session.status = SessionStatus.CREATED
        self._sessions[session_id] = session
        logger.info(
            "Created session %s for target %s (total_sessions=%d)",
            session_id,
            target,
            len(self._sessions),
        )
        return session_id, session

    def get(self, session_id: str) -> Session | None:
        """Retrieve a session by ID.

        Args:
            session_id: Session identifier.

        Returns:
            The session, or ``None`` if not found or expired.
        """
        if session_id not in self._sessions:
            return None

        session = self._sessions[session_id]
        if self._is_expired(session):
            session.status = SessionStatus.EXPIRED
            return None

        return session

    def update_status(self, session_id: str, status: SessionStatus) -> bool:
        """Update a session's status.

        Args:
            session_id: Session identifier.
            status: New status.

        Returns:
            ``True`` if the update succeeded, ``False`` if session not found.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return False

        session.status = status
        logger.info(
            "Session %s status -> %s",
            session_id,
            status.value if hasattr(status, "value") else status,
        )
        return True

    def cleanup_expired(self) -> int:
        """Remove all expired sessions from the manager.

        Returns:
            Number of sessions removed.
        """
        expired_ids = [sid for sid, session in self._sessions.items() if self._is_expired(session)]

        for sid in expired_ids:
            del self._sessions[sid]
            logger.info("Cleaned up expired session %s (ttl=%ds)", sid, self.ttl_seconds)

        return len(expired_ids)

    def get_stats(self) -> dict[str, Any]:
        """Collect statistics about managed sessions.

        Returns:
            Dictionary with keys:
            - ``count_by_status``: Histogram of sessions by status.
            - ``avg_age_seconds``: Average session age in seconds.
            - ``memory_estimate_mb``: Rough memory footprint estimate.
            - ``total_sessions``: Total number of sessions (including expired).
        """
        now = datetime.now()
        status_counts = {status.value: 0 for status in SessionStatus}
        ages: list[float] = []

        for session in self._sessions.values():
            status_str = (
                session.status.value
                if isinstance(session.status, SessionStatus)
                else str(session.status)
            )
            status_counts[status_str] = status_counts.get(status_str, 0) + 1

            age_seconds = (now - session.created_at).total_seconds()
            ages.append(age_seconds)

        avg_age = sum(ages) / len(ages) if ages else 0.0

        # Rough memory estimate: ~1KB per session + graph data
        memory_estimate = len(self._sessions) * 1.0  # Rough KB estimate
        for session in self._sessions.values():
            if session.program_graph:
                memory_estimate += 10.0  # Rough KB per graph
            if session.gnn_model:
                memory_estimate += 5.0  # Rough KB per GNN

        return {
            "count_by_status": status_counts,
            "avg_age_seconds": round(avg_age, 1),
            "memory_estimate_mb": round(memory_estimate / 1024.0, 2),
            "total_sessions": len(self._sessions),
        }

    def _is_expired(self, session: Session) -> bool:
        """Check if a session has exceeded its TTL.

        Args:
            session: Session to check.

        Returns:
            ``True`` if the session is expired.
        """
        age = (datetime.now() - session.created_at).total_seconds()
        return age > self.ttl_seconds
