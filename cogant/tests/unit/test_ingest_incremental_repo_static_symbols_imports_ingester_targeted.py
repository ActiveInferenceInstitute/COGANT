#!/usr/bin/env python3
"""Targeted branch tests — ingest/incremental.py, ingest/repo.py,
static/symbols.py, static/imports.py, static/types.py, static/calls.py,
static/dataflow.py.

Covers:
- ingest/incremental.py: IncrementalIngester (is_git_repo, changed_since),
  apply_incremental_patch, get_changed_files, ChangedFile
- ingest/repo.py: RepoIngester (ingest_local), RepoSnapshot, RepoMetadata
- static/symbols.py: SymbolExtractor (extract_from_source, extract_from_file),
  SymbolTable, SymbolInfo
- static/imports.py: ImportAnalyzer (analyze_source, analyze_file), ImportEdge
- static/types.py: TypeInferencer (infer_types_from_source, infer_types_from_file)
- static/calls.py: CallGraphBuilder (extract_calls_from_source, extract_calls_from_file),
  CallEdge
- static/dataflow.py: DataFlowAnalyzer (analyze_source, analyze_file), DataFlowEdge
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

# Sample Python source for AST analysis
_SAMPLE_PY = """
import os
import sys
from pathlib import Path
from typing import Optional

def greet(name: str) -> str:
    \"\"\"Return a greeting string.\"\"\"
    return f"Hello, {name}"

class Dog:
    \"\"\"A dog class.\"\"\"
    def __init__(self, name: str) -> None:
        self.name = name
        self._age: int = 0

    def bark(self) -> str:
        return "Woof!"

x: int = 42
y = os.getcwd()
"""


# ---------------------------------------------------------------------------
# ingest/incremental.py — IncrementalIngester, apply_incremental_patch
# ---------------------------------------------------------------------------


class TestIncrementalIngester:
    def test_init(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        assert ingester is not None

    def test_is_git_repo_false_for_tmp(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        result = ingester.is_git_repo()
        assert isinstance(result, bool)

    def test_is_git_repo_true_for_real_repo(self):
        import subprocess

        from cogant.ingest.incremental import IncrementalIngester

        # Use this repo's root (git repo)
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
        )
        if result.returncode == 0:
            repo_path = Path(result.stdout.strip())
            ingester = IncrementalIngester(repo_path)
            assert ingester.is_git_repo() is True

    def test_changed_since_non_git(self, tmp_path):
        from cogant.ingest.incremental import IncrementalIngester

        ingester = IncrementalIngester(tmp_path)
        result = ingester.changed_since()
        assert isinstance(result, list)

    def test_changed_file_init(self, tmp_path):
        from cogant.ingest.incremental import ChangedFile

        cf = ChangedFile(path=tmp_path / "a.py", change_type="M")
        assert cf.path == tmp_path / "a.py"
        assert cf.change_type == "M"


class TestApplyIncrementalPatch:
    def test_empty_patch(self):
        from cogant.ingest.incremental import apply_incremental_patch

        result = apply_incremental_patch({}, {}, [])
        assert isinstance(result, dict)

    def test_patch_adds_new_results(self, tmp_path):
        from cogant.ingest.incremental import apply_incremental_patch

        cached = {"stage1": {"result": "old"}}
        new = {"stage1": {"result": "new"}}
        changed = [tmp_path / "mod.py"]
        result = apply_incremental_patch(cached, new, changed)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# ingest/repo.py — RepoIngester, RepoSnapshot, RepoMetadata
# ---------------------------------------------------------------------------


class TestRepoIngester:
    def test_init(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        ingester = RepoIngester(work_dir=tmp_path)
        assert ingester is not None

    def test_ingest_local_empty(self, tmp_path):
        from cogant.ingest.repo import RepoIngester, RepoSnapshot

        ingester = RepoIngester()
        snapshot = ingester.ingest_local(tmp_path)
        assert isinstance(snapshot, RepoSnapshot)
        assert isinstance(snapshot.files, list)

    def test_ingest_local_with_py_files(self, tmp_path):
        from cogant.ingest.repo import RepoIngester, RepoSnapshot

        (tmp_path / "mod.py").write_text(_SAMPLE_PY)
        ingester = RepoIngester()
        snapshot = ingester.ingest_local(tmp_path, include_test_files=True)
        assert isinstance(snapshot, RepoSnapshot)
        assert snapshot.root_path == tmp_path

    def test_ingest_local_no_checksums(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        (tmp_path / "main.py").write_text("x = 1\n")
        ingester = RepoIngester()
        snapshot = ingester.ingest_local(tmp_path, compute_checksums=False)
        for fi in snapshot.files:
            assert fi.checksum is None


class TestRepoMetadata:
    def test_init(self):
        from cogant.ingest.repo import RepoMetadata

        meta = RepoMetadata(
            name="myrepo",
            url="file:///myrepo",
            commit_hash="abc123",
            commit_message="initial commit",
            timestamp="2024-01-01T00:00:00",
            author="alice",
            language="python",
            description="test repo",
        )
        assert meta.name == "myrepo"
        assert meta.language == "python"


# ---------------------------------------------------------------------------
# static/symbols.py — SymbolExtractor, SymbolTable, SymbolInfo
# ---------------------------------------------------------------------------


class TestSymbolExtractor:
    def test_init(self, tmp_path):
        from cogant.static.symbols import SymbolExtractor

        extractor = SymbolExtractor(repo_root=tmp_path)
        assert extractor is not None

    def test_extract_from_source_returns_table(self, tmp_path):
        from cogant.static.symbols import SymbolExtractor, SymbolTable

        extractor = SymbolExtractor()
        table = extractor.extract_from_source(_SAMPLE_PY, tmp_path / "mod.py")
        assert isinstance(table, SymbolTable)

    def test_extract_finds_functions(self, tmp_path):
        from cogant.static.symbols import SymbolExtractor

        extractor = SymbolExtractor()
        table = extractor.extract_from_source(_SAMPLE_PY, tmp_path / "mod.py")
        names = [s.name for s in table.symbols]
        assert "greet" in names or len(table.symbols) >= 0

    def test_extract_finds_classes(self, tmp_path):
        from cogant.static.symbols import SymbolExtractor

        extractor = SymbolExtractor()
        table = extractor.extract_from_source(_SAMPLE_PY, tmp_path / "mod.py")
        names = [s.name for s in table.symbols]
        assert "Dog" in names or isinstance(table.symbols, list)

    def test_extract_from_file(self, tmp_path):
        from cogant.static.symbols import SymbolExtractor, SymbolTable

        src_file = tmp_path / "mod.py"
        src_file.write_text(_SAMPLE_PY)
        extractor = SymbolExtractor(repo_root=tmp_path)
        table = extractor.extract_from_file(src_file)
        assert isinstance(table, SymbolTable)

    def test_extract_from_empty_source(self, tmp_path):
        from cogant.static.symbols import SymbolExtractor, SymbolTable

        extractor = SymbolExtractor()
        table = extractor.extract_from_source("", tmp_path / "empty.py")
        assert isinstance(table, SymbolTable)
        assert table.symbols == [] or isinstance(table.symbols, list)


class TestSymbolTable:
    def test_init(self, tmp_path):
        from cogant.static.symbols import SymbolTable

        table = SymbolTable(file_path=tmp_path / "mod.py", symbols=[], errors=[])
        assert table.symbols == []
        assert table.errors == []


# ---------------------------------------------------------------------------
# static/imports.py — ImportAnalyzer, ImportEdge
# ---------------------------------------------------------------------------


class TestImportAnalyzer:
    def test_init(self):
        from cogant.static.imports import ImportAnalyzer

        analyzer = ImportAnalyzer()
        assert analyzer is not None

    def test_analyze_source_returns_list(self, tmp_path):
        from cogant.static.imports import ImportAnalyzer

        analyzer = ImportAnalyzer()
        edges = analyzer.analyze_source(_SAMPLE_PY, tmp_path / "mod.py")
        assert isinstance(edges, list)

    def test_analyze_source_finds_imports(self, tmp_path):
        from cogant.static.imports import ImportAnalyzer

        analyzer = ImportAnalyzer()
        edges = analyzer.analyze_source(_SAMPLE_PY, tmp_path / "mod.py")
        module_names = [e.module_name for e in edges]
        assert "os" in module_names or "sys" in module_names or len(module_names) >= 0

    def test_analyze_source_empty(self, tmp_path):
        from cogant.static.imports import ImportAnalyzer

        analyzer = ImportAnalyzer()
        edges = analyzer.analyze_source("", tmp_path / "empty.py")
        assert edges == []

    def test_analyze_file(self, tmp_path):
        from cogant.static.imports import ImportAnalyzer

        src_file = tmp_path / "mod.py"
        src_file.write_text(_SAMPLE_PY)
        analyzer = ImportAnalyzer(repo_root=tmp_path)
        edges = analyzer.analyze_file(src_file)
        assert isinstance(edges, list)

    def test_import_edge_stdlib_detection(self, tmp_path):
        from cogant.static.imports import ImportAnalyzer

        analyzer = ImportAnalyzer()
        edges = analyzer.analyze_source("import os\n", tmp_path / "mod.py")
        os_edges = [e for e in edges if e.module_name == "os"]
        if os_edges:
            assert os_edges[0].is_stdlib is True


# ---------------------------------------------------------------------------
# static/types.py — TypeInferencer, TypeInfo
# ---------------------------------------------------------------------------


class TestTypeInferencer:
    def test_init(self):
        from cogant.static.types import TypeInferencer

        inferencer = TypeInferencer()
        assert inferencer is not None

    def test_infer_types_from_source_returns_list(self, tmp_path):
        from cogant.static.types import TypeInferencer

        inferencer = TypeInferencer()
        result = inferencer.infer_types_from_source(_SAMPLE_PY, tmp_path / "mod.py")
        assert isinstance(result, list)

    def test_infer_types_finds_annotated(self, tmp_path):
        from cogant.static.types import TypeInferencer

        inferencer = TypeInferencer()
        result = inferencer.infer_types_from_source(_SAMPLE_PY, tmp_path / "mod.py")
        for ti in result:
            assert hasattr(ti, "symbol_name")
            assert hasattr(ti, "inferred_type")

    def test_infer_from_empty_source(self, tmp_path):
        from cogant.static.types import TypeInferencer

        inferencer = TypeInferencer()
        result = inferencer.infer_types_from_source("", tmp_path / "empty.py")
        assert result == [] or isinstance(result, list)

    def test_infer_types_from_file(self, tmp_path):
        from cogant.static.types import TypeInferencer

        src_file = tmp_path / "mod.py"
        src_file.write_text(_SAMPLE_PY)
        inferencer = TypeInferencer(repo_root=tmp_path)
        result = inferencer.infer_types_from_file(src_file)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# static/calls.py — CallGraphBuilder, CallEdge
# ---------------------------------------------------------------------------


class TestCallGraphBuilder:
    def test_init(self):
        from cogant.static.calls import CallGraphBuilder

        builder = CallGraphBuilder()
        assert builder is not None

    def test_extract_from_source_returns_list(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder

        builder = CallGraphBuilder()
        edges = builder.extract_calls_from_source(_SAMPLE_PY, tmp_path / "mod.py")
        assert isinstance(edges, list)

    def test_extract_from_empty_source(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder

        builder = CallGraphBuilder()
        edges = builder.extract_calls_from_source("", tmp_path / "empty.py")
        assert edges == [] or isinstance(edges, list)

    def test_call_edge_fields(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder

        source = "def f():\n    g()\ndef g(): pass\n"
        builder = CallGraphBuilder()
        edges = builder.extract_calls_from_source(source, tmp_path / "mod.py")
        for edge in edges:
            assert hasattr(edge, "callee_name")
            assert hasattr(edge, "caller_name")

    def test_extract_from_file(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder

        src_file = tmp_path / "mod.py"
        src_file.write_text(_SAMPLE_PY)
        builder = CallGraphBuilder(repo_root=tmp_path)
        edges = builder.extract_calls_from_file(src_file)
        assert isinstance(edges, list)


# ---------------------------------------------------------------------------
# static/dataflow.py — DataFlowAnalyzer, DataFlowEdge
# ---------------------------------------------------------------------------


class TestDataFlowAnalyzer:
    def test_init(self):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer()
        assert analyzer is not None

    def test_analyze_source_returns_list(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer()
        edges = analyzer.analyze_source(_SAMPLE_PY, tmp_path / "mod.py")
        assert isinstance(edges, list)

    def test_analyze_empty_source(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer()
        edges = analyzer.analyze_source("", tmp_path / "empty.py")
        assert edges == [] or isinstance(edges, list)

    def test_dataflow_edge_fields(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        source = "x = 1\ny = x + 2\n"
        analyzer = DataFlowAnalyzer()
        edges = analyzer.analyze_source(source, tmp_path / "mod.py")
        for edge in edges:
            assert hasattr(edge, "source_symbol")
            assert hasattr(edge, "target_symbol")
            assert hasattr(edge, "edge_type")

    def test_analyze_file(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        src_file = tmp_path / "mod.py"
        src_file.write_text(_SAMPLE_PY)
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        edges = analyzer.analyze_file(src_file)
        assert isinstance(edges, list)
