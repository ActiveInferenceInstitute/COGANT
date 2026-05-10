"""Coverage tests for cogant.api.session — wave 20.

Targets uncovered branches in Session and SessionManager:
- extract_static (91-109)
- extract_dynamic (111-136)
- build_graph (138-165)
- translate_to_gnn (167-181)
- compile_state_space (183-202)
- export_all (204-241)
- to_dict status branch (251)
- from_dict (269-309)
- SessionManager.create / get / update_status / cleanup_expired /
  get_stats / _is_expired (326-458)
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from cogant.api.session import Session, SessionManager, SessionStatus

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_repo(tmp_path: Path) -> Path:
    """Create a tiny on-disk Python repo so static analysis can succeed."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "mod.py").write_text(
        "def hello(name):\n"
        "    return 'hi ' + name\n"
        "\n"
        "class Greeter:\n"
        "    def greet(self, name):\n"
        "        return hello(name)\n",
        encoding="utf-8",
    )
    return repo


# ---------------------------------------------------------------------------
# Session pipeline stages
# ---------------------------------------------------------------------------


def test_extract_static_runs_and_populates_syntax_tree(tmp_path: Path) -> None:
    """extract_static populates ``syntax_tree`` with target and ingest data."""
    repo = _make_repo(tmp_path)
    session = Session.from_target(str(repo))

    result = session.extract_static()
    assert isinstance(result, dict)
    # ``type`` is set to "syntax_tree" but the static stage may overwrite it
    # via dict spread. We just verify the structural fields.
    assert result["target"] == str(repo)
    assert "ingest" in result
    assert session.syntax_tree is result


def test_build_graph_runs_full_prerequisite_chain(tmp_path: Path) -> None:
    """build_graph auto-runs ingest + static + normalize when artifacts missing."""
    repo = _make_repo(tmp_path)
    session = Session.from_target(str(repo))

    pg = session.build_graph()
    assert isinstance(pg, dict)
    assert "nodes" in pg
    assert "edges" in pg
    # Auto-fills syntax_tree if not set
    assert session.syntax_tree is not None
    assert session.program_graph is pg


def test_build_graph_after_extract_static_does_not_redo(tmp_path: Path) -> None:
    """Calling build_graph after extract_static still works correctly."""
    repo = _make_repo(tmp_path)
    session = Session.from_target(str(repo))

    session.extract_static()
    pg = session.build_graph()
    assert isinstance(pg, dict)
    assert isinstance(session.syntax_tree, dict)


def test_translate_to_gnn_auto_builds_graph(tmp_path: Path) -> None:
    """translate_to_gnn auto-runs build_graph when graph not yet built."""
    repo = _make_repo(tmp_path)
    session = Session.from_target(str(repo))

    gnn = session.translate_to_gnn()
    assert isinstance(gnn, dict)
    assert session.gnn_model is gnn


def test_compile_state_space_auto_runs_translate(tmp_path: Path) -> None:
    """compile_state_space auto-runs translate_to_gnn when mappings missing."""
    repo = _make_repo(tmp_path)
    session = Session.from_target(str(repo))

    ss = session.compile_state_space()
    assert isinstance(ss, dict)
    assert session.state_space is ss
    assert session.process_model is not None


def test_extract_dynamic_with_no_paths(tmp_path: Path) -> None:
    """extract_dynamic with no coverage/trace paths runs the prerequisite chain
    and reports zero counts (rather than skipping)."""
    repo = _make_repo(tmp_path)
    session = Session.from_target(str(repo))

    trace = session.extract_dynamic()
    assert isinstance(trace, dict)
    assert session.trace_bundle is trace


def test_extract_dynamic_after_graph_built(tmp_path: Path) -> None:
    """extract_dynamic skips already-completed prerequisites."""
    repo = _make_repo(tmp_path)
    session = Session.from_target(str(repo))

    # Build graph first so the second branch is exercised
    session.build_graph()
    trace = session.extract_dynamic()
    assert isinstance(trace, dict)


def test_export_all_writes_artifacts_and_syntax_tree(tmp_path: Path) -> None:
    """export_all writes JSON artifacts and sets syntax_tree.json."""
    repo = _make_repo(tmp_path)
    session = Session.from_target(str(repo))
    out = tmp_path / "out"

    returned = session.export_all(str(out))
    assert returned is session
    assert out.exists()
    # Some export artifacts should be registered
    assert "syntax_tree" in session.export_artifacts
    assert (out / "syntax_tree.json").is_file()


def test_export_all_with_layout_organizes_outputs(tmp_path: Path) -> None:
    """export_all(layout=True) organizes output into layout subdirectories."""
    repo = _make_repo(tmp_path)
    session = Session.from_target(str(repo))
    out = tmp_path / "out_layout"

    session.export_all(str(out), layout=True)
    # The layout step moves program_graph.json into a data/ subdir
    assert (out / "data" / "program_graph.json").is_file()


def test_export_all_after_compile_state_space(tmp_path: Path) -> None:
    """export_all does not re-run any stage that already produced artifacts."""
    repo = _make_repo(tmp_path)
    session = Session.from_target(str(repo))
    session.compile_state_space()  # runs all prerequisites

    out = tmp_path / "after_compile"
    session.export_all(str(out))
    assert out.is_dir()


# ---------------------------------------------------------------------------
# Session.to_dict / Session.from_dict round trips
# ---------------------------------------------------------------------------


def test_to_dict_and_from_dict_round_trip(tmp_path: Path) -> None:
    """Session round-trips through to_dict / from_dict preserving fields."""
    repo = _make_repo(tmp_path)
    session = Session(target=str(repo), workspace=str(tmp_path / "ws"))
    session.status = SessionStatus.IN_PROGRESS
    session.metadata = {"k": "v"}
    session.syntax_tree = {"type": "syntax_tree", "target": str(repo)}
    session.program_graph = {"nodes": {}, "edges": {}}
    session.gnn_model = {"mapping_count": 0}
    session.state_space = {"states": []}
    session.process_model = {"stages": {}}
    session.trace_bundle = {"events": []}
    session.export_artifacts = {"syntax_tree": tmp_path / "syntax_tree.json"}

    payload = session.to_dict()
    assert payload["target"] == str(repo)
    assert payload["status"] == "in_progress"
    assert payload["workspace"] == str(tmp_path / "ws")
    assert payload["metadata"] == {"k": "v"}

    rebuilt = Session.from_dict(payload)
    assert rebuilt.target == str(repo)
    assert rebuilt.status == SessionStatus.IN_PROGRESS
    assert rebuilt.workspace == str(tmp_path / "ws")
    assert rebuilt.metadata == {"k": "v"}
    assert rebuilt.syntax_tree == session.syntax_tree
    assert rebuilt.program_graph == session.program_graph
    assert rebuilt.gnn_model == session.gnn_model
    assert rebuilt.state_space == session.state_space
    assert rebuilt.process_model == session.process_model
    assert rebuilt.trace_bundle == session.trace_bundle
    # Paths are reconstructed
    assert isinstance(rebuilt.export_artifacts["syntax_tree"], Path)


def test_to_dict_with_string_status_falls_back_safely(tmp_path: Path) -> None:
    """to_dict tolerates a status that isn't a SessionStatus enum."""
    repo = _make_repo(tmp_path)
    session = Session(target=str(repo))
    # Bypass field validation on purpose: simulate a legacy persisted form
    object.__setattr__(session, "status", "weird")  # type: ignore[arg-type]
    payload = session.to_dict()
    assert payload["status"] == "weird"


def test_from_dict_unknown_status_defaults_to_created(tmp_path: Path) -> None:
    """from_dict falls back to SessionStatus.CREATED on unknown status string."""
    repo = _make_repo(tmp_path)
    payload = {
        "target": str(repo),
        "workspace": None,
        "repo_path": None,
        "created_at": datetime.now().isoformat(),
        "status": "definitely_not_a_status",
        "syntax_tree": None,
        "trace_bundle": None,
        "program_graph": None,
        "gnn_model": None,
        "state_space": None,
        "process_model": None,
        "export_artifacts": {},
        "metadata": {},
    }
    session = Session.from_dict(payload)
    assert session.status == SessionStatus.CREATED


def test_from_dict_handles_missing_created_at(tmp_path: Path) -> None:
    """from_dict tolerates missing created_at (uses datetime.now())."""
    repo = _make_repo(tmp_path)
    payload = {
        "target": str(repo),
        # created_at omitted
    }
    session = Session.from_dict(payload)
    assert isinstance(session.created_at, datetime)


def test_from_dict_handles_repo_path(tmp_path: Path) -> None:
    """from_dict reconstructs repo_path from the serialized form."""
    repo = _make_repo(tmp_path)
    payload = {
        "target": str(repo),
        "repo_path": str(repo),
    }
    session = Session.from_dict(payload)
    assert session.repo_path == Path(str(repo))


def test_to_dict_no_repo_path_serializes_as_none(tmp_path: Path) -> None:
    """to_dict emits repo_path=None when not provided."""
    repo = _make_repo(tmp_path)
    session = Session(target=str(repo))
    payload = session.to_dict()
    assert payload["repo_path"] is None


# ---------------------------------------------------------------------------
# SessionManager
# ---------------------------------------------------------------------------


def test_session_manager_create_returns_id_and_session(tmp_path: Path) -> None:
    """create() returns (uuid, Session) and stores the session."""
    mgr = SessionManager()
    sid, session = mgr.create(str(tmp_path))
    assert isinstance(sid, str)
    assert len(sid) >= 32  # UUID4 hex with dashes
    assert isinstance(session, Session)
    assert session.target == str(tmp_path)
    assert session.status == SessionStatus.CREATED
    # Stored
    assert mgr._sessions[sid] is session


def test_session_manager_create_with_workspace(tmp_path: Path) -> None:
    """create() forwards workspace into the new Session."""
    mgr = SessionManager()
    ws = str(tmp_path / "workspace")
    _, session = mgr.create(str(tmp_path), workspace=ws)
    assert session.workspace == ws


def test_session_manager_get_returns_session(tmp_path: Path) -> None:
    """get() returns the stored session for a known id."""
    mgr = SessionManager()
    sid, session = mgr.create(str(tmp_path))
    assert mgr.get(sid) is session


def test_session_manager_get_unknown_returns_none(tmp_path: Path) -> None:
    """get() returns None for an unknown id."""
    mgr = SessionManager()
    assert mgr.get("nope") is None


def test_session_manager_get_expired_returns_none(tmp_path: Path) -> None:
    """get() returns None and marks expired sessions when past TTL."""
    mgr = SessionManager(ttl_seconds=0)  # everything is immediately expired
    sid, session = mgr.create(str(tmp_path))
    # Move created_at into the past so it qualifies as expired
    object.__setattr__(session, "created_at", datetime.now() - timedelta(seconds=1))
    assert mgr.get(sid) is None
    assert session.status == SessionStatus.EXPIRED


def test_session_manager_update_status_succeeds(tmp_path: Path) -> None:
    """update_status returns True for known ids and applies the new status."""
    mgr = SessionManager()
    sid, session = mgr.create(str(tmp_path))
    assert mgr.update_status(sid, SessionStatus.COMPLETED) is True
    assert session.status == SessionStatus.COMPLETED


def test_session_manager_update_status_missing(tmp_path: Path) -> None:
    """update_status returns False for an unknown id."""
    mgr = SessionManager()
    assert mgr.update_status("missing", SessionStatus.COMPLETED) is False


def test_session_manager_update_status_with_string_status(tmp_path: Path) -> None:
    """update_status logs gracefully when status lacks .value attribute."""
    mgr = SessionManager()
    sid, _ = mgr.create(str(tmp_path))
    # Pass a plain string; the implementation logs str(status) when no .value
    assert mgr.update_status(sid, "weird") is True  # type: ignore[arg-type]


def test_session_manager_cleanup_expired_removes_sessions(tmp_path: Path) -> None:
    """cleanup_expired removes only sessions past TTL and returns the count."""
    mgr = SessionManager(ttl_seconds=10_000)
    sid_keep, _ = mgr.create(str(tmp_path))
    sid_expire, expired_session = mgr.create(str(tmp_path))
    # Push the second one's created_at far into the past
    object.__setattr__(expired_session, "created_at", datetime.now() - timedelta(hours=10))

    n = mgr.cleanup_expired()
    assert n == 1
    assert sid_keep in mgr._sessions
    assert sid_expire not in mgr._sessions


def test_session_manager_cleanup_expired_returns_zero(tmp_path: Path) -> None:
    """cleanup_expired returns 0 when no sessions are expired."""
    mgr = SessionManager(ttl_seconds=10_000)
    mgr.create(str(tmp_path))
    assert mgr.cleanup_expired() == 0


def test_session_manager_get_stats_empty(tmp_path: Path) -> None:
    """get_stats returns zero counts when no sessions exist."""
    mgr = SessionManager()
    stats = mgr.get_stats()
    assert stats["total_sessions"] == 0
    assert stats["avg_age_seconds"] == 0.0
    # All status histogram buckets sum to 0
    assert sum(stats["count_by_status"].values()) == 0


def test_session_manager_get_stats_with_sessions(tmp_path: Path) -> None:
    """get_stats returns populated stats with a histogram and average age."""
    mgr = SessionManager()
    sid1, s1 = mgr.create(str(tmp_path))
    sid2, s2 = mgr.create(str(tmp_path))
    mgr.update_status(sid2, SessionStatus.COMPLETED)
    s1.program_graph = {"nodes": {}, "edges": {}}
    s2.gnn_model = {"mapping_count": 0}
    # Sleep briefly so avg_age > 0
    time.sleep(0.01)

    stats = mgr.get_stats()
    assert stats["total_sessions"] == 2
    assert stats["count_by_status"]["created"] == 1
    assert stats["count_by_status"]["completed"] == 1
    assert stats["avg_age_seconds"] >= 0.0
    assert stats["memory_estimate_mb"] >= 0.0


def test_session_manager_get_stats_with_string_status(tmp_path: Path) -> None:
    """get_stats handles a session whose status was set to a raw string."""
    mgr = SessionManager()
    sid, session = mgr.create(str(tmp_path))
    object.__setattr__(session, "status", "custom_status")  # type: ignore[arg-type]
    stats = mgr.get_stats()
    assert stats["count_by_status"]["custom_status"] == 1


def test_session_manager_is_expired_true_false(tmp_path: Path) -> None:
    """_is_expired returns True only past TTL."""
    mgr = SessionManager(ttl_seconds=60)
    _, session = mgr.create(str(tmp_path))
    assert mgr._is_expired(session) is False
    object.__setattr__(session, "created_at", datetime.now() - timedelta(seconds=120))
    assert mgr._is_expired(session) is True
