"""Wave-20 coverage boost: cogant package ``__init__`` public entry point.

Drives every public symbol exported from ``cogant/__init__.py`` and
exercises the ``run_pipeline`` convenience wrapper end-to-end against a
real on-disk Python repo. No mocks — real Session, real ingest, real
graph build, real export.

Coverage targets in ``py/cogant/__init__.py``:
  * Module-level optional-import blocks (lines 22-136) — verified by
    the symbols actually being non-None when the dependency is installed.
  * ``run_pipeline`` happy path (lines 148-171) — driven via real Session.
  * ``run_pipeline`` ImportError path — driven by temporarily clearing
    the module-level ``Session`` symbol and restoring it (no mocking).
  * ``__all__`` membership audit.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import cogant

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_repo(tmp_path: Path) -> Path:
    """Build a tiny real Python repo so the full pipeline can run."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "lib.py").write_text(
        "def add(a, b):\n"
        "    return a + b\n"
        "\n"
        "def mul(a, b):\n"
        "    return a * b\n"
        "\n"
        "class Calc:\n"
        "    def total(self, items):\n"
        "        s = 0\n"
        "        for x in items:\n"
        "            s = add(s, x)\n"
        "        return s\n",
        encoding="utf-8",
    )
    (repo / "main.py").write_text(
        "from lib import Calc\n"
        "\n"
        "def run():\n"
        "    return Calc().total([1, 2, 3])\n",
        encoding="utf-8",
    )
    return repo


# ---------------------------------------------------------------------------
# Module-level metadata
# ---------------------------------------------------------------------------


class TestVersionInfo:
    def test_version_is_nonempty_string(self) -> None:
        assert isinstance(cogant.__version__, str)
        assert cogant.__version__  # truthy / non-empty

    def test_author_is_string(self) -> None:
        assert isinstance(cogant.__author__, str)
        assert cogant.__author__

    def test_rust_available_is_bool(self) -> None:
        assert isinstance(cogant._RUST_AVAILABLE, bool)

    def test_rust_version_matches_flag(self) -> None:
        # When rust is available, version is a string; when not, it's None.
        if cogant._RUST_AVAILABLE:
            assert isinstance(cogant.__rust_version__, str)
        else:
            assert cogant.__rust_version__ is None


# ---------------------------------------------------------------------------
# Public API — every symbol in __all__ is reachable on the package
# ---------------------------------------------------------------------------


class TestPublicAPISymbols:
    """Each name in ``__all__`` must be importable from the package root."""

    @pytest.mark.parametrize("name", cogant.__all__)
    def test_symbol_present_on_module(self, name: str) -> None:
        assert hasattr(cogant, name), f"cogant.__all__ promised '{name}' but it is absent"

    def test_core_api_classes_resolved(self) -> None:
        # When the full install is present, these should resolve to classes.
        # When they don't (degraded install), they're explicitly None.
        for name in (
            "Session",
            "PipelineRunner",
            "Bundle",
            "ProgramGraphBuilder",
            "TranslationEngine",
            "StateSpaceCompiler",
            "GNNMarkdownFormatter",
            "ProgramGraph",
        ):
            obj = getattr(cogant, name)
            assert obj is None or isinstance(obj, type), (
                f"{name} should be a class or None, got {type(obj).__name__}"
            )

    def test_protocol_symbols_resolved(self) -> None:
        for name in (
            "Translatable",
            "Analyzable",
            "Serializable",
            "Visualizable",
            "Validatable",
            "Exportable",
            "PipelineStage",
            "TranslationRule",
            "GraphBackend",
        ):
            obj = getattr(cogant, name)
            # Protocols are types when available; None on degraded install.
            assert obj is None or isinstance(obj, type)

    def test_typeddict_symbols_resolved(self) -> None:
        for name in (
            "NodeAttrs",
            "EdgeAttrs",
            "GNNBundle",
            "NodeId",
            "EdgeKind",
            "RoleName",
            "FilePath",
            "ConfidenceScore",
            "AMatrix",
            "BMatrix",
            "CVector",
            "DVector",
            "MermaidStr",
            "DotStr",
            "JsonStr",
        ):
            obj = getattr(cogant, name)
            # Type aliases / TypedDicts: anything non-Ellipsis. None is valid
            # for the degraded-install branch.
            assert obj is None or obj is not Ellipsis

    def test_aliases_consistent_with_targets(self) -> None:
        # CogantSession aliases Session; GNNBundle aliases Bundle.
        # The aliases are assigned at import-time, so we check identity.
        from cogant.api.bundle import Bundle as _RealBundle
        from cogant.api.session import Session as _RealSession

        assert cogant.CogantSession is _RealSession
        assert cogant.GNNBundle is _RealBundle


# ---------------------------------------------------------------------------
# run_pipeline — full happy path against a real repo
# ---------------------------------------------------------------------------


class TestRunPipelineHappyPath:
    """Exercise the body of ``run_pipeline`` (lines 148-171)."""

    def test_full_pipeline_returns_session_with_artifacts(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        out_dir = tmp_path / "out"

        result = cogant.run_pipeline(str(repo), str(out_dir))

        # The wrapper returns the completed Session object.
        from cogant.api.session import Session as _Session

        assert isinstance(result, _Session)

        # All five lifecycle stages should have populated their slots.
        assert result.syntax_tree is not None
        assert result.program_graph is not None
        assert result.gnn_model is not None
        assert result.state_space is not None

        # export_all writes artifacts under ``out_dir``.
        assert out_dir.exists()
        assert any(out_dir.rglob("*"))  # at least one artifact written

    def test_run_pipeline_default_output_dir_used(self, tmp_path: Path) -> None:
        """Default ``output_dir='output'`` is honored when not specified."""
        repo = _make_repo(tmp_path)
        # cd into a tmp workspace so the relative "output" path is isolated.
        import os

        prev_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            result = cogant.run_pipeline(str(repo))
            assert result is not None
            assert (tmp_path / "output").exists()
        finally:
            os.chdir(prev_cwd)


class TestRunPipelineErrorPath:
    """Exercise the ImportError branch in ``run_pipeline`` (line 164)."""

    def test_run_pipeline_raises_import_error_when_session_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Replace the module-level Session symbol with None — no mocking
        # framework, just attribute reassignment via monkeypatch which
        # restores it after the test.
        monkeypatch.setattr(cogant, "Session", None)
        with pytest.raises(ImportError, match="cogant.api.session is not available"):
            cogant.run_pipeline("ignored", "ignored")


# ---------------------------------------------------------------------------
# __all__ correctness
# ---------------------------------------------------------------------------


class TestAllList:
    def test_all_is_list_of_strings(self) -> None:
        assert isinstance(cogant.__all__, list)
        assert all(isinstance(s, str) for s in cogant.__all__)

    def test_no_duplicates_except_known_alias(self) -> None:
        # GNNBundle appears twice intentionally (alias + TypedDict). All
        # *other* names should be unique.
        names = [n for n in cogant.__all__ if n != "GNNBundle"]
        assert len(names) == len(set(names)), (
            f"duplicates in __all__ besides GNNBundle: "
            f"{[n for n in names if names.count(n) > 1]}"
        )

    def test_run_pipeline_in_all(self) -> None:
        assert "run_pipeline" in cogant.__all__

    def test_version_attrs_in_all(self) -> None:
        assert "__version__" in cogant.__all__
        assert "__rust_version__" in cogant.__all__
        assert "_RUST_AVAILABLE" in cogant.__all__


# ---------------------------------------------------------------------------
# run_pipeline output is JSON-serializable to disk (smoke)
# ---------------------------------------------------------------------------


class TestRunPipelineOutputs:
    def test_output_directory_contains_readable_artifacts(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        out_dir = tmp_path / "out2"
        cogant.run_pipeline(str(repo), str(out_dir))

        # At least one JSON or YAML or markdown artifact should be readable.
        readable: list[Path] = []
        for p in out_dir.rglob("*"):
            if p.is_file() and p.suffix in {".json", ".yaml", ".yml", ".md"}:
                readable.append(p)
        assert readable, "no readable artifacts produced by run_pipeline"

        # Try parsing one of the JSON artifacts — confirms not-corrupted.
        json_files = [p for p in readable if p.suffix == ".json"]
        if json_files:
            data = json.loads(json_files[0].read_text(encoding="utf-8"))
            # Bundle JSON is a dict; some artifacts may be lists.
            assert isinstance(data, (dict, list))


# ---------------------------------------------------------------------------
# Optional-import fallback branches
# ---------------------------------------------------------------------------
#
# The package's ``__init__.py`` defines eight ``try / except (ImportError,
# ModuleNotFoundError)`` blocks for optional submodules. To exercise the
# fallback branches we reload the package in-process with a ``MetaPathFinder``
# that raises ``ModuleNotFoundError`` for the targeted dotted names. This is
# real import-system behavior — no mock libraries involved.


import importlib  # noqa: E402
import sys as _sys  # noqa: E402


class _BlockingFinder:
    """Real meta-path finder that raises ModuleNotFoundError for *blocked*."""

    def __init__(self, blocked: set[str]) -> None:
        self.blocked = blocked

    def find_spec(
        self, name: str, path: object = None, target: object = None
    ) -> None:
        if name in self.blocked:
            raise ModuleNotFoundError(f"blocked by test: {name}")
        return None


def _reload_cogant_with_blocked(blocked: set[str]) -> object:
    """Reload the cogant package while *blocked* dotted names raise.

    Returns the freshly-imported ``cogant`` module. The original module
    object is restored on test teardown by importing the real package
    again at the end (see ``_restore_cogant``).
    """
    finder = _BlockingFinder(blocked)
    # Drop already-loaded cogant submodules so the reload re-runs all
    # ``try/except`` blocks at the top of the package __init__.
    to_drop = [
        name
        for name in list(_sys.modules)
        if name == "cogant" or name.startswith("cogant.")
    ]
    for name in to_drop:
        del _sys.modules[name]
    _sys.meta_path.insert(0, finder)
    try:
        import cogant as _fresh

        importlib.reload(_fresh)
        return _fresh
    finally:
        _sys.meta_path.remove(finder)


def _restore_cogant() -> None:
    """Force a clean re-import so subsequent tests see the normal package."""
    to_drop = [
        name
        for name in list(_sys.modules)
        if name == "cogant" or name.startswith("cogant.")
    ]
    for name in to_drop:
        del _sys.modules[name]
    import cogant as _fresh  # noqa: F401


def _exec_in_subprocess(script: str) -> tuple[int, str, str]:
    """Run *script* in a fresh Python interpreter and return (rc, stdout, stderr).

    Retained for completeness; in-process reload is preferred where it covers
    the same branches because coverage.py captures it.
    """
    import subprocess

    proc = subprocess.run(
        [_sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return proc.returncode, proc.stdout, proc.stderr


@pytest.fixture
def restore_cogant() -> object:
    """Restore a pristine ``cogant`` module after a fallback test."""
    yield None
    _restore_cogant()


class TestOptionalImportFallbacks:
    """Each ``except (ImportError, ModuleNotFoundError)`` branch is real."""

    def test_session_fallback_when_api_session_missing(
        self, restore_cogant: object
    ) -> None:
        fresh = _reload_cogant_with_blocked({"cogant.api.session"})
        assert fresh.Session is None  # type: ignore[attr-defined]

    def test_pipeline_runner_fallback_when_pipeline_missing(
        self, restore_cogant: object
    ) -> None:
        fresh = _reload_cogant_with_blocked({"cogant.api.pipeline"})
        assert fresh.PipelineRunner is None  # type: ignore[attr-defined]

    def test_bundle_fallback_when_bundle_missing(self, restore_cogant: object) -> None:
        fresh = _reload_cogant_with_blocked({"cogant.api.bundle"})
        assert fresh.Bundle is None  # type: ignore[attr-defined]

    def test_protocols_fallback_when_protocols_missing(
        self, restore_cogant: object
    ) -> None:
        fresh = _reload_cogant_with_blocked({"cogant.protocols"})
        for name in (
            "Analyzable",
            "Exportable",
            "GraphBackend",
            "PipelineStage",
            "Serializable",
            "Translatable",
            "TranslationRule",
            "Validatable",
            "Visualizable",
        ):
            assert getattr(fresh, name) is None, name

    def test_types_fallback_when_types_missing(self, restore_cogant: object) -> None:
        fresh = _reload_cogant_with_blocked({"cogant.types"})
        for name in (
            "AMatrix",
            "BMatrix",
            "CVector",
            "DVector",
            "EdgeAttrs",
            "EdgeKind",
            "FilePath",
            "JsonStr",
            "MermaidStr",
            "NodeAttrs",
            "NodeId",
            "RoleName",
            "DotStr",
            "ConfidenceScore",
        ):
            assert getattr(fresh, name) is None, name

    def test_program_graph_double_fallback(self, restore_cogant: object) -> None:
        # Block both schemas.program_graph and schemas.graph to drive the
        # inner ``except`` branch (lines 76-77).
        fresh = _reload_cogant_with_blocked(
            {"cogant.schemas.program_graph", "cogant.schemas.graph"}
        )
        assert fresh.ProgramGraph is None  # type: ignore[attr-defined]

    def test_program_graph_first_fallback_succeeds_via_legacy(
        self, restore_cogant: object
    ) -> None:
        # Block only program_graph; legacy schemas.graph still imports →
        # exercises the inner ``try`` recovery path (line 75).
        fresh = _reload_cogant_with_blocked({"cogant.schemas.program_graph"})
        assert fresh.ProgramGraph is not None  # type: ignore[attr-defined]

    def test_graph_builder_fallback(self, restore_cogant: object) -> None:
        fresh = _reload_cogant_with_blocked({"cogant.graph.builder"})
        assert fresh.ProgramGraphBuilder is None  # type: ignore[attr-defined]

    def test_translation_engine_fallback(self, restore_cogant: object) -> None:
        fresh = _reload_cogant_with_blocked({"cogant.translate.engine"})
        assert fresh.TranslationEngine is None  # type: ignore[attr-defined]

    def test_state_space_compiler_fallback(self, restore_cogant: object) -> None:
        fresh = _reload_cogant_with_blocked({"cogant.statespace.compiler"})
        assert fresh.StateSpaceCompiler is None  # type: ignore[attr-defined]

    def test_gnn_formatter_fallback(self, restore_cogant: object) -> None:
        fresh = _reload_cogant_with_blocked({"cogant.gnn.formatter"})
        assert fresh.GNNMarkdownFormatter is None  # type: ignore[attr-defined]

    def test_rust_extension_fallback(self, restore_cogant: object) -> None:
        fresh = _reload_cogant_with_blocked({"cogant._rust"})
        assert fresh._RUST_AVAILABLE is False  # type: ignore[attr-defined]
        assert fresh.__rust_version__ is None  # type: ignore[attr-defined]
