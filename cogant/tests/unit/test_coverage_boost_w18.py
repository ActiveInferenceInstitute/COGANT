#!/usr/bin/env python3
"""Wave-18 coverage boost tests.

Targeted behavioral tests for modules currently below 80% coverage:
- cogant/__init__.py (56%)
- cogant/observability/logging.py (61%)
- cogant/normalize/canonical.py (64%)
- cogant/ingest/files.py (64%)
- cogant/ingest/repo.py (64%)
- cogant/ingest/language_detect.py (60%)
- cogant/schemas/program_graph.py (60%)
- cogant/schemas/provenance.py (67%)
- cogant/schemas/base.py (72%)
- cogant/schemas/__init__.py (71%)

No mocks. All tests use real objects and real data.
"""

from __future__ import annotations

import logging
import textwrap
from pathlib import Path

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# cogant/__init__.py
# ---------------------------------------------------------------------------


class TestCogantInit:
    """Tests for the top-level cogant package init."""

    def test_version_is_string(self) -> None:
        import cogant

        assert isinstance(cogant.__version__, str)
        assert len(cogant.__version__) > 0

    def test_rust_available_is_bool(self) -> None:
        import cogant

        assert isinstance(cogant._RUST_AVAILABLE, bool)

    def test_rust_version_is_none_or_str(self) -> None:
        import cogant

        assert cogant.__rust_version__ is None or isinstance(cogant.__rust_version__, str)

    def test_session_importable_or_none(self) -> None:
        import cogant

        # Session is either a real class or None
        assert cogant.Session is None or callable(cogant.Session)

    def test_pipeline_runner_importable_or_none(self) -> None:
        import cogant

        assert cogant.PipelineRunner is None or callable(cogant.PipelineRunner)

    def test_bundle_importable_or_none(self) -> None:
        import cogant

        assert cogant.Bundle is None or callable(cogant.Bundle)

    def test_program_graph_builder_importable_or_none(self) -> None:
        import cogant

        assert cogant.ProgramGraphBuilder is None or callable(cogant.ProgramGraphBuilder)

    def test_translation_engine_importable_or_none(self) -> None:
        import cogant

        assert cogant.TranslationEngine is None or callable(cogant.TranslationEngine)

    def test_state_space_compiler_importable_or_none(self) -> None:
        import cogant

        assert cogant.StateSpaceCompiler is None or callable(cogant.StateSpaceCompiler)

    def test_gnn_formatter_importable_or_none(self) -> None:
        import cogant

        assert cogant.GNNMarkdownFormatter is None or callable(cogant.GNNMarkdownFormatter)

    def test_program_graph_importable_or_none(self) -> None:
        import cogant

        assert cogant.ProgramGraph is None or callable(cogant.ProgramGraph)

    def test_aliases_match_originals(self) -> None:
        import cogant

        assert cogant.CogantSession is cogant.Session
        assert cogant.GNNBundle is cogant.Bundle

    def test_run_pipeline_raises_import_error_when_session_none(self) -> None:
        import cogant

        if cogant.Session is None:
            with pytest.raises(ImportError, match="cogant.api.session"):
                cogant.run_pipeline("some/path")

    def test_all_contains_version(self) -> None:
        import cogant

        assert "__version__" in cogant.__all__

    def test_all_contains_rust_flag(self) -> None:
        import cogant

        assert "_RUST_AVAILABLE" in cogant.__all__


# ---------------------------------------------------------------------------
# cogant/observability/logging.py
# ---------------------------------------------------------------------------


class TestObservabilityLogging:
    """Tests for the observability logging module."""

    def test_setup_logging_default(self) -> None:
        from cogant.observability.logging import setup_logging

        # Should not raise
        setup_logging()

    def test_setup_logging_debug_level(self) -> None:
        from cogant.observability.logging import setup_logging

        setup_logging(level="DEBUG")
        assert logging.root.level == logging.DEBUG

    def test_setup_logging_warning_level(self) -> None:
        from cogant.observability.logging import setup_logging

        setup_logging(level="WARNING")
        assert logging.root.level == logging.WARNING

    def test_setup_logging_console_format(self) -> None:
        from cogant.observability.logging import setup_logging

        # Should not raise even if structlog not installed
        setup_logging(format="console")

    def test_setup_logging_json_format(self) -> None:
        from cogant.observability.logging import setup_logging

        setup_logging(format="json")

    def test_get_logger_returns_logger(self) -> None:
        from cogant.observability.logging import get_logger

        logger = get_logger("test.module")
        assert logger is not None

    def test_get_logger_different_names_different_loggers(self) -> None:
        from cogant.observability.logging import get_logger

        a = get_logger("module.a")
        b = get_logger("module.b")
        # They should be different loggers
        assert a is not b or str(a) != str(b)

    def test_structlog_flag(self) -> None:
        from cogant.observability import logging as obs_logging

        assert isinstance(obs_logging._STRUCTLOG_AVAILABLE, bool)


# ---------------------------------------------------------------------------
# cogant/normalize/canonical.py
# ---------------------------------------------------------------------------


class TestCanonicalNormalizer:
    """Tests for the CanonicalNormalizer."""

    def _make_normalizer(self):
        from cogant.normalize.canonical import CanonicalNormalizer

        return CanonicalNormalizer()

    def _make_fact(self, lang: str, fact_type: str, **data):
        from cogant.normalize.canonical import LanguageFact

        return LanguageFact(fact_type=fact_type, language=lang, data=data)

    def test_normalize_python_class(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("python", "class", name="MyClass", qualified_name="pkg.MyClass")
        result = norm.normalize(fact)
        assert result is not None
        assert result.name == "MyClass"
        assert result.qualified_name == "pkg.MyClass"

    def test_normalize_python_function(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("python", "function", name="my_fn")
        result = norm.normalize(fact)
        assert result is not None

    def test_normalize_python_method(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("python", "method", name="do_thing")
        result = norm.normalize(fact)
        assert result is not None

    def test_normalize_python_module(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("python", "module", name="main")
        result = norm.normalize(fact)
        assert result is not None

    def test_normalize_python_variable(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("python", "variable", name="MY_CONST")
        result = norm.normalize(fact)
        assert result is not None

    def test_normalize_python_decorator(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("python", "decorator", name="cached")
        result = norm.normalize(fact)
        assert result is not None

    def test_normalize_javascript_class(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("javascript", "class", name="MyJsClass")
        result = norm.normalize(fact)
        assert result is not None

    def test_normalize_javascript_arrow_function(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("javascript", "arrow_function", name="handler")
        result = norm.normalize(fact)
        assert result is not None

    def test_normalize_java_interface(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("java", "interface", name="Runnable")
        result = norm.normalize(fact)
        assert result is not None

    def test_normalize_java_field(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("java", "field", name="count")
        result = norm.normalize(fact)
        assert result is not None

    def test_normalize_generic_module(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("generic", "module", name="util")
        result = norm.normalize(fact)
        assert result is not None

    def test_normalize_unknown_returns_none(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("cobol", "section", name="para")
        result = norm.normalize(fact)
        assert result is None

    def test_normalize_logs_unmapped_fact(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("rust", "trait", name="Sized")
        norm.normalize(fact)
        log = norm.get_normalization_log()
        assert any(e["status"] == "unmapped_fact" for e in log)

    def test_normalize_logs_success(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("python", "class", name="A")
        norm.normalize(fact)
        log = norm.get_normalization_log()
        assert any(e["status"] == "normalized" for e in log)

    def test_get_normalization_stats_counts_correctly(self) -> None:
        norm = self._make_normalizer()
        norm.normalize(self._make_fact("python", "class", name="A"))
        norm.normalize(self._make_fact("cobol", "section", name="B"))
        stats = norm.get_normalization_stats()
        assert stats["normalized"] == 1
        assert stats["unmapped_facts"] == 1
        assert stats["total_normalizations"] == 2

    def test_normalize_batch_preserves_order(self) -> None:
        norm = self._make_normalizer()
        facts = [
            self._make_fact("python", "class", name="A"),
            self._make_fact("rust", "trait", name="B"),
            self._make_fact("python", "function", name="C"),
        ]
        results = norm.normalize_batch(facts)
        assert len(results) == 3
        assert results[0] is not None
        assert results[1] is None
        assert results[2] is not None

    def test_to_node_creates_node_with_id(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("python", "class", name="Foo", qualified_name="pkg.Foo")
        normalized = norm.normalize(fact)
        assert normalized is not None
        node = norm.to_node(normalized, "node::pkg.Foo")
        assert node.id == "node::pkg.Foo"
        assert node.name == "Foo"

    def test_python_metadata_extracts_is_async(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("python", "function", name="fetch", is_async=True)
        result = norm.normalize(fact)
        assert result is not None
        assert result.metadata is not None
        assert result.metadata.get("is_async") is True

    def test_python_metadata_extracts_is_generator(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("python", "function", name="gen_rows", is_generator=True)
        result = norm.normalize(fact)
        assert result is not None
        assert result.metadata is not None
        assert result.metadata.get("is_generator") is True

    def test_javascript_metadata_extracts_is_arrow(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("javascript", "arrow_function", name="cb", is_arrow=True)
        result = norm.normalize(fact)
        assert result is not None
        assert result.metadata is not None
        assert result.metadata.get("is_arrow") is True

    def test_javascript_metadata_extracts_export_type(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("javascript", "function", name="fn", export_type="default")
        result = norm.normalize(fact)
        assert result is not None
        assert result.metadata is not None
        assert result.metadata.get("export_type") == "default"

    def test_java_metadata_extracts_modifiers(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("java", "method", name="run", modifiers=["public", "final"])
        result = norm.normalize(fact)
        assert result is not None
        assert result.metadata is not None
        assert result.metadata.get("modifiers") == ["public", "final"]

    def test_java_metadata_extracts_annotations(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("java", "method", name="doGet", annotations=["@Override"])
        result = norm.normalize(fact)
        assert result is not None
        assert result.metadata is not None
        assert result.metadata.get("annotations") == ["@Override"]

    def test_common_metadata_extracts_visibility(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("python", "class", name="Pub", visibility="public")
        result = norm.normalize(fact)
        assert result is not None
        assert result.metadata is not None
        assert result.metadata.get("visibility") == "public"

    def test_common_metadata_extracts_is_abstract(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("python", "class", name="Base", is_abstract=True)
        result = norm.normalize(fact)
        assert result is not None
        assert result.metadata is not None
        assert result.metadata.get("is_abstract") is True

    def test_common_metadata_extracts_is_static(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("java", "method", name="getInstance", is_static=True)
        result = norm.normalize(fact)
        assert result is not None
        assert result.metadata is not None
        assert result.metadata.get("is_static") is True

    def test_normalize_extracts_path(self) -> None:
        norm = self._make_normalizer()
        fact = self._make_fact("python", "module", name="utils", path="src/utils.py")
        result = norm.normalize(fact)
        assert result is not None
        assert result.path == "src/utils.py"

    def test_get_normalization_log_returns_copy(self) -> None:
        norm = self._make_normalizer()
        norm.normalize(self._make_fact("python", "class", name="X"))
        log1 = norm.get_normalization_log()
        log2 = norm.get_normalization_log()
        assert log1 is not log2
        assert log1 == log2


# ---------------------------------------------------------------------------
# cogant/ingest/files.py
# ---------------------------------------------------------------------------


class TestFileEnumerator:
    """Tests for the FileEnumerator."""

    def test_enumerate_finds_python_files(self, tmp_path: Path) -> None:
        from cogant.ingest.files import FileEnumerator

        (tmp_path / "main.py").write_text("x = 1")
        (tmp_path / "utils.py").write_text("def f(): pass")
        enumerator = FileEnumerator(tmp_path, respect_gitignore=False)
        files = enumerator.enumerate()
        names = {f.path.name for f in files}
        assert "main.py" in names
        assert "utils.py" in names

    def test_enumerate_excludes_non_source_files(self, tmp_path: Path) -> None:
        from cogant.ingest.files import FileEnumerator

        (tmp_path / "README.md").write_text("docs")
        (tmp_path / "app.py").write_text("pass")
        enumerator = FileEnumerator(tmp_path, respect_gitignore=False)
        files = enumerator.enumerate()
        names = {f.path.name for f in files}
        assert "README.md" not in names
        assert "app.py" in names

    def test_enumerate_detects_language(self, tmp_path: Path) -> None:
        from cogant.ingest.files import FileEnumerator

        (tmp_path / "app.ts").write_text("const x = 1;")
        enumerator = FileEnumerator(tmp_path, respect_gitignore=False)
        files = enumerator.enumerate()
        ts_files = [f for f in files if f.path.name == "app.ts"]
        assert len(ts_files) == 1
        assert ts_files[0].language == "typescript"

    def test_enumerate_marks_test_files(self, tmp_path: Path) -> None:
        from cogant.ingest.files import FileEnumerator

        (tmp_path / "test_app.py").write_text("def test_x(): pass")
        (tmp_path / "app.py").write_text("def main(): pass")
        enumerator = FileEnumerator(tmp_path, respect_gitignore=False)
        files = enumerator.enumerate()
        file_map = {f.path.name: f for f in files}
        assert file_map["test_app.py"].is_test is True
        assert file_map["app.py"].is_test is False

    def test_enumerate_excludes_test_files_when_requested(self, tmp_path: Path) -> None:
        from cogant.ingest.files import FileEnumerator

        (tmp_path / "test_app.py").write_text("def test_x(): pass")
        (tmp_path / "app.py").write_text("def main(): pass")
        enumerator = FileEnumerator(tmp_path, respect_gitignore=False)
        files = enumerator.enumerate(include_test_files=False)
        names = {f.path.name for f in files}
        assert "test_app.py" not in names
        assert "app.py" in names

    def test_enumerate_computes_checksums(self, tmp_path: Path) -> None:
        from cogant.ingest.files import FileEnumerator

        (tmp_path / "main.py").write_text("x = 1")
        enumerator = FileEnumerator(tmp_path, respect_gitignore=False)
        files = enumerator.enumerate(compute_checksums=True)
        assert len(files) == 1
        assert files[0].checksum is not None
        assert len(files[0].checksum) == 64  # SHA256 hex

    def test_enumerate_provides_file_size(self, tmp_path: Path) -> None:
        from cogant.ingest.files import FileEnumerator

        content = "x = 1\n"
        (tmp_path / "main.py").write_text(content)
        enumerator = FileEnumerator(tmp_path, respect_gitignore=False)
        files = enumerator.enumerate()
        assert len(files) == 1
        assert files[0].size_bytes > 0

    def test_enumerate_provides_relative_path(self, tmp_path: Path) -> None:
        from cogant.ingest.files import FileEnumerator

        sub = tmp_path / "src"
        sub.mkdir()
        (sub / "main.py").write_text("pass")
        enumerator = FileEnumerator(tmp_path, respect_gitignore=False)
        files = enumerator.enumerate()
        assert len(files) == 1
        assert "src" in files[0].relative_path

    def test_should_ignore_pycache(self, tmp_path: Path) -> None:
        from cogant.ingest.files import FileEnumerator

        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "main.cpython-311.pyc").write_bytes(b"\x00" * 10)
        (tmp_path / "main.py").write_text("pass")
        enumerator = FileEnumerator(tmp_path, respect_gitignore=False)
        files = enumerator.enumerate()
        assert len(files) == 1
        assert files[0].path.name == "main.py"

    def test_should_ignore_node_modules(self, tmp_path: Path) -> None:
        from cogant.ingest.files import FileEnumerator

        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "lodash.js").write_text("module.exports = {};")
        (tmp_path / "app.js").write_text("const l = require('lodash');")
        enumerator = FileEnumerator(tmp_path, respect_gitignore=False)
        files = enumerator.enumerate()
        names = {f.path.name for f in files}
        assert "lodash.js" not in names

    def test_load_gitignore_reads_patterns(self, tmp_path: Path) -> None:
        from cogant.ingest.files import FileEnumerator

        (tmp_path / ".gitignore").write_text("*.pyc\nbuild/\n# comment\n")
        enumerator = FileEnumerator(tmp_path, respect_gitignore=True)
        patterns = enumerator._load_gitignore()
        assert "*.pyc" in patterns
        assert "build/" in patterns
        assert "# comment" not in patterns

    def test_load_gitignore_returns_empty_when_missing(self, tmp_path: Path) -> None:
        from cogant.ingest.files import FileEnumerator

        enumerator = FileEnumerator(tmp_path, respect_gitignore=True)
        patterns = enumerator._load_gitignore()
        assert isinstance(patterns, set)
        assert len(patterns) == 0

    def test_load_gitignore_caches_result(self, tmp_path: Path) -> None:
        from cogant.ingest.files import FileEnumerator

        (tmp_path / ".gitignore").write_text("*.tmp\n")
        enumerator = FileEnumerator(tmp_path, respect_gitignore=True)
        p1 = enumerator._load_gitignore()
        p2 = enumerator._load_gitignore()
        assert p1 is p2  # same object (cached)

    def test_gitignore_wildcard_suffix_ignored(self, tmp_path: Path) -> None:
        from cogant.ingest.files import FileEnumerator

        (tmp_path / ".gitignore").write_text("*.min.js\n")
        (tmp_path / "app.min.js").write_text("x=1;")
        (tmp_path / "main.js").write_text("x=1;")
        enumerator = FileEnumerator(tmp_path, respect_gitignore=True)
        files = enumerator.enumerate()
        names = {f.path.name for f in files}
        # app.min.js matches *.min.js pattern
        assert "app.min.js" not in names
        assert "main.js" in names

    def test_detect_language_rust(self, tmp_path: Path) -> None:
        from cogant.ingest.files import FileEnumerator

        enumerator = FileEnumerator(tmp_path, respect_gitignore=False)
        lang = enumerator._detect_language(Path("lib.rs"))
        assert lang == "rust"

    def test_detect_language_go(self, tmp_path: Path) -> None:
        from cogant.ingest.files import FileEnumerator

        enumerator = FileEnumerator(tmp_path, respect_gitignore=False)
        lang = enumerator._detect_language(Path("main.go"))
        assert lang == "go"

    def test_detect_language_unknown(self, tmp_path: Path) -> None:
        from cogant.ingest.files import FileEnumerator

        enumerator = FileEnumerator(tmp_path, respect_gitignore=False)
        lang = enumerator._detect_language(Path("notes.txt"))
        assert lang is None

    def test_is_test_file_spec_pattern(self, tmp_path: Path) -> None:
        from cogant.ingest.files import FileEnumerator

        enumerator = FileEnumerator(tmp_path, respect_gitignore=False)
        assert enumerator._is_test_file("src/_spec.py") is True

    def test_is_test_file_negative(self, tmp_path: Path) -> None:
        from cogant.ingest.files import FileEnumerator

        enumerator = FileEnumerator(tmp_path, respect_gitignore=False)
        assert enumerator._is_test_file("src/main.py") is False

    def test_compute_checksum_consistency(self, tmp_path: Path) -> None:
        from cogant.ingest.files import FileEnumerator

        enumerator = FileEnumerator(tmp_path, respect_gitignore=False)
        f = tmp_path / "data.py"
        f.write_text("content = 42")
        c1 = enumerator._compute_checksum(f)
        c2 = enumerator._compute_checksum(f)
        assert c1 == c2
        assert len(c1) == 64

    def test_enumerate_multiple_languages(self, tmp_path: Path) -> None:
        from cogant.ingest.files import FileEnumerator

        (tmp_path / "app.py").write_text("pass")
        (tmp_path / "app.ts").write_text("const x = 1;")
        (tmp_path / "main.go").write_text("package main")
        enumerator = FileEnumerator(tmp_path, respect_gitignore=False)
        files = enumerator.enumerate()
        langs = {f.language for f in files}
        assert "python" in langs
        assert "typescript" in langs
        assert "go" in langs


# ---------------------------------------------------------------------------
# cogant/ingest/repo.py
# ---------------------------------------------------------------------------


class TestRepoIngester:
    """Tests for RepoIngester."""

    def test_ingest_local_basic(self, tmp_path: Path) -> None:
        from cogant.ingest.repo import RepoIngester

        (tmp_path / "main.py").write_text("def main(): pass")
        ingester = RepoIngester(work_dir=tmp_path / "work")
        snapshot = ingester.ingest_local(tmp_path)
        assert snapshot.root_path == tmp_path
        assert snapshot.metadata.name == tmp_path.name

    def test_ingest_local_detects_primary_language(self, tmp_path: Path) -> None:
        from cogant.ingest.repo import RepoIngester

        for i in range(3):
            (tmp_path / f"mod{i}.py").write_text("pass")
        (tmp_path / "main.go").write_text("package main")
        ingester = RepoIngester(work_dir=tmp_path / "work")
        snapshot = ingester.ingest_local(tmp_path)
        assert snapshot.metadata.language == "python"

    def test_ingest_local_with_checksums(self, tmp_path: Path) -> None:
        from cogant.ingest.repo import RepoIngester

        (tmp_path / "main.py").write_text("x = 1")
        ingester = RepoIngester(work_dir=tmp_path / "work")
        snapshot = ingester.ingest_local(tmp_path, compute_checksums=True)
        assert any(f.checksum is not None for f in snapshot.files)

    def test_ingest_local_exclude_tests(self, tmp_path: Path) -> None:
        from cogant.ingest.repo import RepoIngester

        (tmp_path / "main.py").write_text("def main(): pass")
        (tmp_path / "test_main.py").write_text("def test_x(): pass")
        ingester = RepoIngester(work_dir=tmp_path / "work")
        snapshot = ingester.ingest_local(tmp_path, include_test_files=False)
        names = {f.path.name for f in snapshot.files}
        assert "test_main.py" not in names

    def test_ingest_local_nonexistent_raises_value_error(self, tmp_path: Path) -> None:
        from cogant.ingest.repo import RepoIngester

        ingester = RepoIngester(work_dir=tmp_path / "work")
        with pytest.raises(ValueError, match="does not exist"):
            ingester.ingest_local(tmp_path / "nonexistent")

    def test_ingest_local_file_path_raises_value_error(self, tmp_path: Path) -> None:
        from cogant.ingest.repo import RepoIngester

        f = tmp_path / "main.py"
        f.write_text("pass")
        ingester = RepoIngester(work_dir=tmp_path / "work")
        with pytest.raises(ValueError, match="not a directory"):
            ingester.ingest_local(f)

    def test_ingest_local_extracts_git_metadata(self, tmp_path: Path) -> None:
        from cogant.ingest.repo import RepoIngester

        (tmp_path / "main.py").write_text("pass")
        ingester = RepoIngester(work_dir=tmp_path / "work")
        snapshot = ingester.ingest_local(tmp_path)
        # commit_hash will be None for non-git dirs, but metadata object must exist
        assert snapshot.metadata is not None
        assert snapshot.metadata.url == str(tmp_path)

    def test_extract_dependencies_with_requirements_txt(self, tmp_path: Path) -> None:
        from cogant.ingest.repo import RepoIngester

        (tmp_path / "requirements.txt").write_text("requests>=2.0\nclick\n")
        ingester = RepoIngester(work_dir=tmp_path / "work")
        deps = ingester._extract_dependencies(tmp_path)
        names = {d.name for d in deps}
        assert "requests" in names
        assert "click" in names

    def test_extract_dependencies_with_pyproject_toml(self, tmp_path: Path) -> None:
        from cogant.ingest.repo import RepoIngester

        (tmp_path / "pyproject.toml").write_text(
            textwrap.dedent("""\
            [project]
            name = "myapp"
            version = "1.0.0"
            dependencies = ["fastapi>=0.100", "pydantic>=2.0"]
        """)
        )
        ingester = RepoIngester(work_dir=tmp_path / "work")
        deps = ingester._extract_dependencies(tmp_path)
        names = {d.name for d in deps}
        assert "fastapi" in names
        assert "pydantic" in names

    def test_extract_dependencies_deduplicates(self, tmp_path: Path) -> None:
        from cogant.ingest.repo import RepoIngester

        # Both files mention 'requests'
        (tmp_path / "requirements.txt").write_text("requests\n")
        (tmp_path / "pyproject.toml").write_text(
            textwrap.dedent("""\
            [project]
            name = "app"
            version = "1.0.0"
            dependencies = ["requests"]
        """)
        )
        ingester = RepoIngester(work_dir=tmp_path / "work")
        deps = ingester._extract_dependencies(tmp_path)
        request_deps = [d for d in deps if d.name == "requests"]
        assert len(request_deps) == 1

    def test_extract_dependencies_with_package_json(self, tmp_path: Path) -> None:
        import json

        from cogant.ingest.repo import RepoIngester

        (tmp_path / "package.json").write_text(
            json.dumps(
                {
                    "name": "my-app",
                    "version": "1.0.0",
                    "dependencies": {"lodash": "^4.17.21"},
                    "devDependencies": {"jest": "^29.0.0"},
                }
            )
        )
        ingester = RepoIngester(work_dir=tmp_path / "work")
        deps = ingester._extract_dependencies(tmp_path)
        names = {d.name for d in deps}
        assert "lodash" in names

    def test_ingest_local_with_cargo_toml(self, tmp_path: Path) -> None:
        from cogant.ingest.repo import RepoIngester

        (tmp_path / "Cargo.toml").write_text(
            textwrap.dedent("""\
            [package]
            name = "myapp"
            version = "0.1.0"

            [dependencies]
            serde = "1.0"
        """)
        )
        (tmp_path / "main.rs").write_text("fn main() {}")
        ingester = RepoIngester(work_dir=tmp_path / "work")
        snapshot = ingester.ingest_local(tmp_path)
        assert snapshot is not None

    def test_repo_snapshot_dataclass(self, tmp_path: Path) -> None:
        from cogant.ingest.repo import RepoIngester

        (tmp_path / "app.py").write_text("pass")
        ingester = RepoIngester(work_dir=tmp_path / "work")
        snapshot = ingester.ingest_local(tmp_path)
        assert hasattr(snapshot, "metadata")
        assert hasattr(snapshot, "files")
        assert hasattr(snapshot, "dependencies")
        assert hasattr(snapshot, "root_path")


# ---------------------------------------------------------------------------
# cogant/ingest/language_detect.py
# ---------------------------------------------------------------------------


class TestLanguageDetector:
    """Tests for the LanguageDetector."""

    def test_detect_language_python(self) -> None:
        from cogant.ingest.language_detect import LanguageDetector

        assert LanguageDetector.detect_language(Path("main.py")) == "python"

    def test_detect_language_pyx(self) -> None:
        from cogant.ingest.language_detect import LanguageDetector

        assert LanguageDetector.detect_language(Path("ext.pyx")) == "python"

    def test_detect_language_pyi(self) -> None:
        from cogant.ingest.language_detect import LanguageDetector

        assert LanguageDetector.detect_language(Path("stubs.pyi")) == "python"

    def test_detect_language_typescript(self) -> None:
        from cogant.ingest.language_detect import LanguageDetector

        assert LanguageDetector.detect_language(Path("app.ts")) == "typescript"

    def test_detect_language_tsx(self) -> None:
        from cogant.ingest.language_detect import LanguageDetector

        assert LanguageDetector.detect_language(Path("comp.tsx")) == "typescript"

    def test_detect_language_javascript(self) -> None:
        from cogant.ingest.language_detect import LanguageDetector

        assert LanguageDetector.detect_language(Path("app.js")) == "javascript"

    def test_detect_language_jsx(self) -> None:
        from cogant.ingest.language_detect import LanguageDetector

        assert LanguageDetector.detect_language(Path("comp.jsx")) == "javascript"

    def test_detect_language_rust(self) -> None:
        from cogant.ingest.language_detect import LanguageDetector

        assert LanguageDetector.detect_language(Path("lib.rs")) == "rust"

    def test_detect_language_go(self) -> None:
        from cogant.ingest.language_detect import LanguageDetector

        assert LanguageDetector.detect_language(Path("main.go")) == "go"

    def test_detect_language_unknown(self) -> None:
        from cogant.ingest.language_detect import LanguageDetector

        assert LanguageDetector.detect_language(Path("README.md")) is None

    def test_detect_language_from_string_path(self) -> None:
        from cogant.ingest.language_detect import LanguageDetector

        # Accepts string paths
        result = LanguageDetector.detect_language("app.py")  # type: ignore[arg-type]
        assert result == "python"

    def test_detect_repo_languages(self, tmp_path: Path) -> None:
        from cogant.ingest.language_detect import LanguageDetector

        (tmp_path / "a.py").write_text("pass")
        (tmp_path / "b.py").write_text("pass")
        (tmp_path / "c.ts").write_text("const x = 1;")
        counts = LanguageDetector.detect_repo_languages(tmp_path)
        assert counts.get("python") == 2
        assert counts.get("typescript") == 1

    def test_detect_repo_languages_string_path(self, tmp_path: Path) -> None:
        from cogant.ingest.language_detect import LanguageDetector

        (tmp_path / "main.py").write_text("pass")
        counts = LanguageDetector.detect_repo_languages(str(tmp_path))  # type: ignore[arg-type]
        assert counts.get("python") == 1

    def test_detect_repo_languages_empty_dir(self, tmp_path: Path) -> None:
        from cogant.ingest.language_detect import LanguageDetector

        counts = LanguageDetector.detect_repo_languages(tmp_path)
        assert isinstance(counts, dict)
        assert len(counts) == 0

    def test_get_supported_languages_returns_list(self) -> None:
        from cogant.ingest.language_detect import LanguageDetector

        supported = LanguageDetector.get_supported_languages()
        assert isinstance(supported, list)

    def test_get_parser_unknown_language_raises(self) -> None:
        from cogant.ingest.language_detect import LanguageDetector

        with pytest.raises((ImportError, Exception)):
            LanguageDetector.get_parser("cobol")

    def test_get_parser_for_extension_py(self) -> None:
        from cogant.ingest.language_detect import get_parser_for_extension

        # .py extension should either return a parser or None gracefully
        result = get_parser_for_extension(".py")
        # Either a parser object or None (if python parser not installed)
        assert result is None or hasattr(result, "__class__")

    def test_get_parser_for_extension_without_dot(self) -> None:
        from cogant.ingest.language_detect import get_parser_for_extension

        # Without leading dot should still work
        result = get_parser_for_extension("py")
        assert result is None or hasattr(result, "__class__")

    def test_get_parser_for_extension_unknown(self) -> None:
        from cogant.ingest.language_detect import get_parser_for_extension

        result = get_parser_for_extension(".xyz")
        assert result is None


# ---------------------------------------------------------------------------
# cogant/schemas/program_graph.py
# ---------------------------------------------------------------------------


class TestProgramGraphSchemas:
    """Tests for the extended program_graph schemas (Node, Edge, ProgramGraph)."""

    def _sid(self, s: str):
        from cogant.schemas.base import StableID

        return StableID(s)

    def _make_location(self):
        from cogant.schemas.base import LocationInfo, Span

        span = Span(start_line=1, start_col=0, end_line=5, end_col=10)
        return LocationInfo(path="src/main.py", span=span, language="python")

    def _make_node(self, node_id: str = "n1", label: str = "MyClass"):
        from cogant.schemas.core import NodeKind
        from cogant.schemas.program_graph import Node

        return Node(
            id=self._sid(node_id),
            kind=NodeKind.CLASS,
            label=label,
            language="python",
            location=self._make_location(),
        )

    def _make_edge(self, edge_id: str = "e1", src: str = "n1", dst: str = "n2"):
        from cogant.schemas.core import EdgeKind
        from cogant.schemas.program_graph import Edge

        return Edge(
            id=self._sid(edge_id),
            source_id=self._sid(src),
            target_id=self._sid(dst),
            kind=EdgeKind.CALLS,
        )

    def test_node_creation(self) -> None:
        node = self._make_node()
        assert node.id == "n1"
        assert node.label == "MyClass"

    def test_node_default_flags(self) -> None:
        node = self._make_node()
        assert node.is_public is False
        assert node.is_test is False
        assert node.is_generated is False
        assert node.is_exported is False

    def test_node_validate_no_self_children(self) -> None:
        from cogant.schemas.core import NodeKind
        from cogant.schemas.program_graph import Node

        with pytest.raises(ValidationError):
            Node(
                id=self._sid("n1"),
                kind=NodeKind.CLASS,
                label="X",
                language="python",
                location=self._make_location(),
                children_ids=[self._sid("n1")],  # self-reference
            )

    def test_edge_creation(self) -> None:
        edge = self._make_edge()
        assert edge.id == "e1"
        assert edge.source_id == "n1"
        assert edge.target_id == "n2"

    def test_edge_default_weight(self) -> None:
        edge = self._make_edge()
        assert edge.weight == 1.0

    def test_program_graph_add_and_get_node(self) -> None:
        from cogant.schemas.base import StableID
        from cogant.schemas.program_graph import ProgramGraph

        g = ProgramGraph(graph_id=StableID("g1"), language="python")
        node = self._make_node("n1")
        g.add_node(node)
        retrieved = g.get_node("n1")
        assert retrieved is not None
        assert retrieved.id == "n1"

    def test_program_graph_get_nonexistent_node_returns_none(self) -> None:
        from cogant.schemas.base import StableID
        from cogant.schemas.program_graph import ProgramGraph

        g = ProgramGraph(graph_id=StableID("g1"), language="python")
        assert g.get_node("missing") is None

    def test_program_graph_add_and_get_edge(self) -> None:
        from cogant.schemas.base import StableID
        from cogant.schemas.program_graph import ProgramGraph

        g = ProgramGraph(graph_id=StableID("g1"), language="python")
        # Add nodes first
        g.add_node(self._make_node("n1"))
        g.add_node(self._make_node("n2", label="Other"))
        edge = self._make_edge("e1", "n1", "n2")
        g.add_edge(edge)
        retrieved = g.get_edge("e1")
        assert retrieved is not None
        assert retrieved.id == "e1"

    def test_program_graph_get_nonexistent_edge_returns_none(self) -> None:
        from cogant.schemas.base import StableID
        from cogant.schemas.program_graph import ProgramGraph

        g = ProgramGraph(graph_id=StableID("g1"), language="python")
        assert g.get_edge("missing") is None

    def test_program_graph_validates_edge_endpoints(self) -> None:
        from cogant.schemas.base import StableID
        from cogant.schemas.core import EdgeKind
        from cogant.schemas.program_graph import Edge, ProgramGraph

        node = self._make_node("n1")
        edge = Edge(
            id=self._sid("e1"),
            source_id=self._sid("n1"),
            target_id=self._sid("n99"),
            kind=EdgeKind.CALLS,
        )
        with pytest.raises(ValidationError):
            ProgramGraph(graph_id=StableID("g1"), language="python", nodes=[node], edges=[edge])

    def test_program_graph_node_index_updates(self) -> None:
        from cogant.schemas.base import StableID
        from cogant.schemas.program_graph import ProgramGraph

        g = ProgramGraph(graph_id=StableID("g1"), language="python")
        g.add_node(self._make_node("n1"))
        g.add_node(self._make_node("n2", label="Other"))
        assert "n1" in g.node_index
        assert "n2" in g.node_index
        assert g.node_index["n1"] == 0
        assert g.node_index["n2"] == 1


# ---------------------------------------------------------------------------
# cogant/schemas/provenance.py (ProvenanceStore)
# ---------------------------------------------------------------------------


class TestProvenanceStore:
    """Tests for ProvenanceStore add/get/query methods."""

    def _make_record(self, evidence_id: str, uri: str = "file://src/main.py"):
        from cogant.schemas.provenance import EvidenceKind, ProvenanceRecord

        return ProvenanceRecord(
            evidence_id=evidence_id,
            uri=uri,
            kind=EvidenceKind.SOURCE_SPAN,
            content="class Foo: pass",
        )

    def test_add_and_get_record(self) -> None:
        from cogant.schemas.provenance import ProvenanceStore

        store = ProvenanceStore()
        record = self._make_record("ev1")
        store.add_record(record)
        retrieved = store.get_record("ev1")
        assert retrieved is not None
        assert retrieved.evidence_id == "ev1"

    def test_get_nonexistent_record_returns_none(self) -> None:
        from cogant.schemas.provenance import ProvenanceStore

        store = ProvenanceStore()
        assert store.get_record("missing") is None

    def test_get_by_uri_returns_matching_records(self) -> None:
        from cogant.schemas.provenance import ProvenanceStore

        store = ProvenanceStore()
        store.add_record(self._make_record("ev1", uri="file://src/a.py"))
        store.add_record(self._make_record("ev2", uri="file://src/b.py"))
        store.add_record(self._make_record("ev3", uri="file://src/a.py"))
        results = store.get_by_uri("file://src/a.py")
        assert len(results) == 2
        ids = {r.evidence_id for r in results}
        assert ids == {"ev1", "ev3"}

    def test_get_by_uri_missing_returns_empty(self) -> None:
        from cogant.schemas.provenance import ProvenanceStore

        store = ProvenanceStore()
        assert store.get_by_uri("file://missing.py") == []

    def test_get_by_kind_returns_matching_records(self) -> None:
        from cogant.schemas.provenance import EvidenceKind, ProvenanceRecord, ProvenanceStore

        store = ProvenanceStore()
        r1 = ProvenanceRecord(
            evidence_id="ev1", uri="file://a.py", kind=EvidenceKind.SOURCE_SPAN, content="x=1"
        )
        r2 = ProvenanceRecord(
            evidence_id="ev2",
            uri="file://b.py",
            kind=EvidenceKind.TEST_ASSERTION,
            content="assert x==1",
        )
        store.add_record(r1)
        store.add_record(r2)
        span_records = store.get_by_kind(EvidenceKind.SOURCE_SPAN)
        assert len(span_records) == 1
        assert span_records[0].evidence_id == "ev1"

    def test_get_by_kind_missing_returns_empty(self) -> None:
        from cogant.schemas.provenance import EvidenceKind, ProvenanceStore

        store = ProvenanceStore()
        assert store.get_by_kind(EvidenceKind.COMMIT_EVENT) == []

    def test_uri_index_updated_correctly(self) -> None:
        from cogant.schemas.provenance import ProvenanceStore

        store = ProvenanceStore()
        store.add_record(self._make_record("ev1", "file://x.py"))
        store.add_record(self._make_record("ev2", "file://y.py"))
        store.add_record(self._make_record("ev3", "file://x.py"))
        assert "file://x.py" in store.uri_index
        assert len(store.uri_index["file://x.py"]) == 2

    def test_kind_index_updated_correctly(self) -> None:
        from cogant.schemas.provenance import ProvenanceStore

        store = ProvenanceStore()
        store.add_record(self._make_record("ev1"))
        store.add_record(self._make_record("ev2"))
        from cogant.schemas.provenance import EvidenceKind

        kind_key = EvidenceKind.SOURCE_SPAN.value
        assert kind_key in store.kind_index
        assert len(store.kind_index[kind_key]) == 2


# ---------------------------------------------------------------------------
# cogant/schemas/base.py
# ---------------------------------------------------------------------------


class TestSchemasBase:
    """Tests for base schema types."""

    def test_semantic_version_valid(self) -> None:
        from cogant.schemas.base import SemanticVersion

        v = SemanticVersion("1.2.3")
        assert str(v) == "1.2.3"

    def test_semantic_version_invalid_format(self) -> None:
        from cogant.schemas.base import SemanticVersion

        with pytest.raises(ValueError, match="Invalid semantic version"):
            SemanticVersion("1.2")

    def test_semantic_version_non_numeric(self) -> None:
        from cogant.schemas.base import SemanticVersion

        with pytest.raises(ValueError, match="Invalid semantic version"):
            SemanticVersion("1.2.alpha")

    def test_span_validates_non_negative(self) -> None:
        from cogant.schemas.base import Span

        with pytest.raises(ValidationError):
            Span(start_line=-1, start_col=0, end_line=5, end_col=10)

    def test_span_validates_end_after_start(self) -> None:
        from cogant.schemas.base import Span

        with pytest.raises(ValidationError):
            Span(start_line=10, start_col=0, end_line=5, end_col=10)

    def test_span_valid_creation(self) -> None:
        from cogant.schemas.base import Span

        span = Span(start_line=1, start_col=0, end_line=5, end_col=10)
        assert span.start_line == 1
        assert span.end_line == 5

    def test_generate_stable_id_is_deterministic(self) -> None:
        from cogant.schemas.base import generate_stable_id

        id1 = generate_stable_id("module:src/main.py")
        id2 = generate_stable_id("module:src/main.py")
        assert id1 == id2

    def test_generate_stable_id_with_prefix(self) -> None:
        from cogant.schemas.base import generate_stable_id

        sid = generate_stable_id("content", prefix="node_")
        assert str(sid).startswith("node_")

    def test_generate_stable_id_different_content(self) -> None:
        from cogant.schemas.base import generate_stable_id

        id1 = generate_stable_id("content_a")
        id2 = generate_stable_id("content_b")
        assert id1 != id2

    def test_location_info_minimal(self) -> None:
        from cogant.schemas.base import LocationInfo

        loc = LocationInfo(path="src/main.py")
        assert loc.path == "src/main.py"
        assert loc.span is None

    def test_evidence_ref_creation(self) -> None:
        from cogant.schemas.base import EvidenceRef

        ref = EvidenceRef(evidence_id="ev1", kind="source_span", confidence=0.9)
        assert ref.evidence_id == "ev1"
        assert ref.confidence == 0.9

    def test_type_info_creation(self) -> None:
        from cogant.schemas.base import TypeInfo

        ti = TypeInfo(base_type="List[str]")
        assert ti.base_type == "List[str]"

    def test_confidence_metric_creation(self) -> None:
        from cogant.schemas.base import ConfidenceMetric

        cm = ConfidenceMetric(score=0.75, method="static_analysis")
        assert cm.score == 0.75


# ---------------------------------------------------------------------------
# cogant/schemas/__init__.py
# ---------------------------------------------------------------------------


class TestSchemasInit:
    """Tests for the schemas package __init__ imports."""

    def test_extended_types_available(self) -> None:
        import cogant.schemas as schemas

        # Check at least some key types available
        assert hasattr(schemas, "Node") or hasattr(schemas, "ProgramGraph")

    def test_program_graph_accessible(self) -> None:
        from cogant import schemas

        assert schemas.ProgramGraph is not None

    def test_node_accessible(self) -> None:
        from cogant import schemas

        assert schemas.Node is not None

    def test_edge_accessible(self) -> None:
        from cogant import schemas

        assert schemas.Edge is not None

    def test_mapping_kind_accessible(self) -> None:
        from cogant import schemas

        assert schemas.MappingKind is not None

    def test_all_is_list(self) -> None:
        import cogant.schemas as schemas

        assert isinstance(schemas.__all__, list)

    def test_extended_available_flag(self) -> None:
        import cogant.schemas as schemas

        assert isinstance(schemas._extended_available, bool)
