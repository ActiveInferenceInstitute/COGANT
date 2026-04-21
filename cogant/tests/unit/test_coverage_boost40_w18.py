#!/usr/bin/env python3
"""Coverage boost batch 40 — cogant/__init__.py, observability/logging.py,
rust_backend.py, ingest/files.py, export/parquet.py.

Covers:
- cogant/__init__.py: __version__, _RUST_AVAILABLE, module-level symbols,
  run_pipeline (Session=None path), convenience aliases
- observability/logging.py: setup_logging, get_logger (stdlib fallback)
- rust_backend.py: RUST_AVAILABLE, rust_version, get_program_graph_impl,
  create_example_graph (RuntimeError path), _env_prefers_rust,
  build_program_graph (pure-Python path)
- ingest/files.py: FileInfo, LANGUAGE_EXTENSIONS, TEST_PATTERNS, IGNORE_PATTERNS,
  FileEnumerator (_detect_language, _is_test_file, _compute_checksum,
  _should_ignore, _load_gitignore, enumerate)
- export/parquet.py: ParquetExporter (_prepare_nodes_data, _prepare_edges_data,
  export when pyarrow missing)
"""

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# cogant/__init__.py
# ---------------------------------------------------------------------------


class TestCogantInit:
    def test_version_string(self):
        import cogant

        assert isinstance(cogant.__version__, str)
        assert len(cogant.__version__) > 0

    def test_rust_available_is_bool(self):
        import cogant

        assert isinstance(cogant._RUST_AVAILABLE, bool)

    def test_rust_version_none_or_str(self):
        import cogant

        assert cogant.__rust_version__ is None or isinstance(cogant.__rust_version__, str)

    def test_cogant_session_alias(self):
        import cogant

        # CogantSession is either Session or None
        assert cogant.CogantSession is cogant.Session

    def test_gnn_bundle_alias(self):
        import cogant

        assert cogant.GNNBundle is cogant.Bundle

    def test_all_exports_accessible(self):
        import cogant

        for name in cogant.__all__:
            assert hasattr(cogant, name), f"Missing: {name}"

    def test_run_pipeline_session_none_raises(self):
        import cogant

        original = cogant.Session
        try:
            cogant.Session = None
            with pytest.raises(ImportError):
                cogant.run_pipeline("/tmp/nowhere")
        finally:
            cogant.Session = original


# ---------------------------------------------------------------------------
# observability/logging.py
# ---------------------------------------------------------------------------


class TestSetupLogging:
    def test_setup_logging_info(self):
        from cogant.observability.logging import setup_logging

        # Should not raise
        setup_logging(level="INFO", format="json")

    def test_setup_logging_debug(self):
        from cogant.observability.logging import setup_logging

        setup_logging(level="DEBUG", format="json")

    def test_setup_logging_console_format(self):
        from cogant.observability.logging import setup_logging

        setup_logging(level="WARNING", format="console")

    def test_setup_logging_uppercase_level(self):
        from cogant.observability.logging import setup_logging

        setup_logging(level="ERROR")


class TestGetLogger:
    def test_returns_logger_object(self):
        from cogant.observability.logging import get_logger

        logger = get_logger("test.module")
        assert logger is not None

    def test_stdlib_logger_has_info(self):
        from cogant.observability.logging import _STRUCTLOG_AVAILABLE, get_logger

        logger = get_logger("test")
        if not _STRUCTLOG_AVAILABLE:
            import logging

            assert isinstance(logger, logging.Logger)


# ---------------------------------------------------------------------------
# rust_backend.py
# ---------------------------------------------------------------------------


class TestRustBackendConstants:
    def test_rust_available_is_bool(self):
        from cogant.rust_backend import RUST_AVAILABLE

        assert isinstance(RUST_AVAILABLE, bool)

    def test_rust_version_none_when_no_rust(self):
        from cogant.rust_backend import RUST_AVAILABLE, rust_version

        v = rust_version()
        if not RUST_AVAILABLE:
            assert v is None
        else:
            assert v is None or isinstance(v, str)


class TestGetProgramGraphImpl:
    def test_returns_a_class(self):
        from cogant.rust_backend import get_program_graph_impl

        impl = get_program_graph_impl()
        assert isinstance(impl, type)

    def test_returns_python_builder_when_no_rust(self):
        from cogant.rust_backend import RUST_AVAILABLE, get_program_graph_impl

        if not RUST_AVAILABLE:
            from cogant.graph.builder import ProgramGraphBuilder

            assert get_program_graph_impl() is ProgramGraphBuilder


class TestCreateExampleGraph:
    def test_raises_runtime_error_when_no_rust(self):
        from cogant.rust_backend import RUST_AVAILABLE, create_example_graph

        if not RUST_AVAILABLE:
            with pytest.raises(RuntimeError, match="Rust backend not available"):
                create_example_graph()


class TestEnvPrefersRust:
    def test_unset_returns_none(self):
        from cogant.rust_backend import _env_prefers_rust

        env = os.environ.copy()
        os.environ.pop("COGANT_USE_RUST", None)
        try:
            result = _env_prefers_rust()
            assert result is None
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_1_returns_true(self):
        from cogant.rust_backend import _env_prefers_rust

        env = os.environ.copy()
        os.environ["COGANT_USE_RUST"] = "1"
        try:
            assert _env_prefers_rust() is True
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_0_returns_false(self):
        from cogant.rust_backend import _env_prefers_rust

        env = os.environ.copy()
        os.environ["COGANT_USE_RUST"] = "0"
        try:
            assert _env_prefers_rust() is False
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_true_string_returns_true(self):
        from cogant.rust_backend import _env_prefers_rust

        env = os.environ.copy()
        os.environ["COGANT_USE_RUST"] = "true"
        try:
            assert _env_prefers_rust() is True
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_false_string_returns_false(self):
        from cogant.rust_backend import _env_prefers_rust

        env = os.environ.copy()
        os.environ["COGANT_USE_RUST"] = "false"
        try:
            assert _env_prefers_rust() is False
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_unknown_string_returns_none(self):
        from cogant.rust_backend import _env_prefers_rust

        env = os.environ.copy()
        os.environ["COGANT_USE_RUST"] = "maybe"
        try:
            result = _env_prefers_rust()
            assert result is None
        finally:
            os.environ.clear()
            os.environ.update(env)


class TestBuildProgramGraph:
    def test_returns_python_builder_when_use_rust_false(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.rust_backend import build_program_graph

        builder = build_program_graph(repo_uri="repo://test", use_rust=False)
        assert isinstance(builder, ProgramGraphBuilder)

    def test_builder_can_finalize(self):
        from cogant.rust_backend import build_program_graph

        builder = build_program_graph(repo_uri="repo://test", use_rust=False)
        graph = builder.finalize()
        assert graph is not None

    def test_default_call_returns_builder(self):
        from cogant.rust_backend import build_program_graph

        env = os.environ.copy()
        os.environ["COGANT_USE_RUST"] = "0"
        try:
            builder = build_program_graph()
            assert builder is not None
        finally:
            os.environ.clear()
            os.environ.update(env)


# ---------------------------------------------------------------------------
# ingest/files.py
# ---------------------------------------------------------------------------


class TestFileInfoDataclass:
    def test_creation(self, tmp_path):
        from cogant.ingest.files import FileInfo

        f = FileInfo(
            path=tmp_path / "test.py",
            relative_path="test.py",
            language="python",
            size_bytes=100,
        )
        assert f.language == "python"
        assert f.is_test is False
        assert f.checksum is None

    def test_test_file_flag(self, tmp_path):
        from cogant.ingest.files import FileInfo

        f = FileInfo(
            path=tmp_path / "test_foo.py",
            relative_path="test_foo.py",
            language="python",
            size_bytes=50,
            is_test=True,
        )
        assert f.is_test is True


class TestConstantsExist:
    def test_language_extensions_has_python(self):
        from cogant.ingest.files import LANGUAGE_EXTENSIONS

        assert "python" in LANGUAGE_EXTENSIONS
        assert ".py" in LANGUAGE_EXTENSIONS["python"]

    def test_test_patterns_exist(self):
        from cogant.ingest.files import TEST_PATTERNS

        assert len(TEST_PATTERNS) > 0

    def test_ignore_patterns_exist(self):
        from cogant.ingest.files import IGNORE_PATTERNS

        assert "__pycache__" in IGNORE_PATTERNS


class TestFileEnumeratorDetectLanguage:
    def test_py_file(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        fe = FileEnumerator(tmp_path)
        assert fe._detect_language(Path("foo.py")) == "python"

    def test_js_file(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        fe = FileEnumerator(tmp_path)
        assert fe._detect_language(Path("foo.js")) == "javascript"

    def test_ts_file(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        fe = FileEnumerator(tmp_path)
        assert fe._detect_language(Path("foo.ts")) == "typescript"

    def test_rs_file(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        fe = FileEnumerator(tmp_path)
        assert fe._detect_language(Path("foo.rs")) == "rust"

    def test_unknown_extension(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        fe = FileEnumerator(tmp_path)
        assert fe._detect_language(Path("foo.xyz")) is None


class TestFileEnumeratorIsTestFile:
    def test_test_prefix(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        fe = FileEnumerator(tmp_path)
        assert fe._is_test_file("test_foo.py") is True

    def test_test_suffix(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        fe = FileEnumerator(tmp_path)
        assert fe._is_test_file("foo_test.py") is True

    def test_tests_directory(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        fe = FileEnumerator(tmp_path)
        assert fe._is_test_file("tests/foo.py") is True

    def test_regular_file(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        fe = FileEnumerator(tmp_path)
        assert fe._is_test_file("src/module.py") is False


class TestFileEnumeratorComputeChecksum:
    def test_checksums_file(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        f = tmp_path / "myfile.txt"
        f.write_text("hello world")
        fe = FileEnumerator(tmp_path)
        checksum = fe._compute_checksum(f)
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA256 hex

    def test_missing_file_returns_empty(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        fe = FileEnumerator(tmp_path)
        result = fe._compute_checksum(tmp_path / "nonexistent.txt")
        assert result == ""


class TestFileEnumeratorLoadGitignore:
    def test_no_gitignore_returns_empty(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        fe = FileEnumerator(tmp_path)
        patterns = fe._load_gitignore()
        assert patterns == set()

    def test_gitignore_loaded(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        (tmp_path / ".gitignore").write_text("*.pyc\n# comment\n\nbuild/\n")
        fe = FileEnumerator(tmp_path)
        patterns = fe._load_gitignore()
        assert "*.pyc" in patterns
        assert "build/" in patterns
        assert "# comment" not in patterns

    def test_cached_on_second_call(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        (tmp_path / ".gitignore").write_text("*.pyc\n")
        fe = FileEnumerator(tmp_path)
        p1 = fe._load_gitignore()
        p2 = fe._load_gitignore()
        assert p1 is p2  # Same object (cached)


class TestFileEnumeratorShouldIgnore:
    def test_ignores_pycache(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        fe = FileEnumerator(tmp_path)
        pycache = tmp_path / "__pycache__" / "foo.pyc"
        pycache.parent.mkdir()
        assert fe._should_ignore(pycache) is True

    def test_allows_normal_file(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        fe = FileEnumerator(tmp_path)
        normal = tmp_path / "src" / "module.py"
        normal.parent.mkdir(exist_ok=True)
        assert fe._should_ignore(normal) is False


class TestFileEnumeratorEnumerate:
    def test_empty_dir_returns_empty(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        fe = FileEnumerator(tmp_path)
        files = fe.enumerate()
        assert files == []

    def test_finds_python_files(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        (tmp_path / "a.py").write_text("x = 1")
        (tmp_path / "b.py").write_text("y = 2")
        fe = FileEnumerator(tmp_path)
        files = fe.enumerate()
        assert len(files) == 2
        langs = {f.language for f in files}
        assert langs == {"python"}

    def test_excludes_test_files(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        (tmp_path / "module.py").write_text("x = 1")
        (tmp_path / "test_module.py").write_text("def test_x(): pass")
        fe = FileEnumerator(tmp_path)
        files = fe.enumerate(include_test_files=False)
        names = [f.path.name for f in files]
        assert "module.py" in names
        assert "test_module.py" not in names

    def test_includes_test_files_by_default(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        (tmp_path / "module.py").write_text("x = 1")
        (tmp_path / "test_module.py").write_text("def test_x(): pass")
        fe = FileEnumerator(tmp_path)
        files = fe.enumerate(include_test_files=True)
        names = [f.path.name for f in files]
        assert "test_module.py" in names

    def test_computes_checksums_when_requested(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        (tmp_path / "a.py").write_text("x = 1")
        fe = FileEnumerator(tmp_path)
        files = fe.enumerate(compute_checksums=True)
        assert files[0].checksum is not None
        assert len(files[0].checksum) == 64

    def test_no_checksums_by_default(self, tmp_path):
        from cogant.ingest.files import FileEnumerator

        (tmp_path / "a.py").write_text("x = 1")
        fe = FileEnumerator(tmp_path)
        files = fe.enumerate()
        assert files[0].checksum is None


# ---------------------------------------------------------------------------
# export/parquet.py
# ---------------------------------------------------------------------------


class TestParquetExporterPrepareData:
    def _make_graph(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import EdgeKind, NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        n1 = builder.add_node(NodeKind.MODULE, "mod", "mod", path="mod.py")
        n2 = builder.add_node(NodeKind.FUNCTION, "fn", "mod.fn", path="mod.py")
        builder.add_edge(n1.id, n2.id, EdgeKind.CONTAINS)
        return builder.finalize()

    def test_prepare_nodes_data_structure(self):
        from cogant.export.parquet import ParquetExporter

        graph = self._make_graph()
        exporter = ParquetExporter(graph)
        data = exporter._prepare_nodes_data()
        assert "id" in data
        assert "name" in data
        assert "kind" in data
        assert "qualified_name" in data
        assert len(data["id"]) == 2

    def test_prepare_edges_data_structure(self):
        from cogant.export.parquet import ParquetExporter

        graph = self._make_graph()
        exporter = ParquetExporter(graph)
        data = exporter._prepare_edges_data()
        assert "id" in data
        assert "source_id" in data
        assert "target_id" in data
        assert "kind" in data
        assert "weight" in data
        assert len(data["id"]) == 1

    def test_export_without_pyarrow_returns_empty(self, tmp_path):
        from cogant.export.parquet import ParquetExporter

        graph = self._make_graph()
        exporter = ParquetExporter(graph)
        # Monkeypatch by hiding pyarrow in the module
        import sys

        original = sys.modules.get("pyarrow")
        sys.modules["pyarrow"] = None  # type: ignore
        try:
            files = exporter.export(tmp_path)
            assert files == []
        finally:
            if original is None:
                sys.modules.pop("pyarrow", None)
            else:
                sys.modules["pyarrow"] = original

    def test_nodes_data_path_fallback_to_empty(self):
        from cogant.export.parquet import ParquetExporter
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        builder.add_node(NodeKind.MODULE, "mod", "mod")  # no path
        graph = builder.finalize()
        exporter = ParquetExporter(graph)
        data = exporter._prepare_nodes_data()
        assert data["path"] == [""]  # falls back to ""
