#!/usr/bin/env python3
"""Coverage boost batch 84 — ingest/manifest.py additional paths,
ingest/repo.py local ingestion, static/dataflow.py additional paths,
gnn/package.py GNNPackageBuilder helpers.

Covers:
- ingest/manifest.py: Dependency dataclass, parse_setup_py, parse_requirements_txt,
  parse_package_json, _parse_requirements_string, _parse_requirement_list,
  _parse_requirement_line (edge cases), parse dispatch for unknown type
- ingest/repo.py: RepoMetadata, RepoSnapshot, RepoIngester.ingest_local paths,
  _extract_metadata, _extract_dependencies with manifests
- static/dataflow.py: DataFlowVisitor class body analysis, method analysis,
  analyze_source with class, augmented assignments, annotated assigns, call nodes
- gnn/package.py: GNNPackageBuilder init, _enum_value helper
"""

import json

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# ingest/manifest.py — additional paths
# ---------------------------------------------------------------------------


class TestDependencyDataclass:
    def test_basic_fields(self):
        from cogant.ingest.manifest import Dependency

        dep = Dependency(name="requests", version=">=2.28,<3.0")
        assert dep.name == "requests"
        assert dep.version == ">=2.28,<3.0"
        assert dep.is_dev is False
        assert dep.is_local is False

    def test_dev_dependency(self):
        from cogant.ingest.manifest import Dependency

        dep = Dependency(name="pytest", version=">=7.0", is_dev=True)
        assert dep.is_dev is True

    def test_local_dependency(self):
        from cogant.ingest.manifest import Dependency

        dep = Dependency(name="mylib", is_local=True)
        assert dep.is_local is True
        assert dep.version is None


class TestManifestParserAdditional:
    def test_parse_setup_py_basic(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        setup = tmp_path / "setup.py"
        setup.write_text(
            "from setuptools import setup\n"
            "setup(\n"
            '    name="mylib",\n'
            '    version="1.2.3",\n'
            '    description="A test library",\n'
            "    install_requires=[\n"
            '        "requests>=2.0",\n'
            '        "click>=7.0",\n'
            "    ],\n"
            ")\n"
        )
        meta, deps = ManifestParser().parse_setup_py(setup)
        assert isinstance(meta, dict)
        assert isinstance(deps, list)
        assert meta.get("name") == "mylib"
        assert meta.get("version") == "1.2.3"
        assert len(deps) >= 1

    def test_parse_setup_py_nonexistent(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        meta, deps = ManifestParser().parse_setup_py(tmp_path / "missing_setup.py")
        assert isinstance(meta, dict)
        assert isinstance(deps, list)

    def test_parse_requirements_txt_basic(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        req = tmp_path / "requirements.txt"
        req.write_text(
            "# Main dependencies\n"
            "requests>=2.28\n"
            "click==8.0.0\n"
            "pydantic>=1.0,<2.0\n"
            "\n"
            "# Comment line\n"
            "numpy\n"
        )
        deps = ManifestParser().parse_requirements_txt(req)
        assert isinstance(deps, list)
        assert len(deps) >= 3
        names = [d.name for d in deps]
        assert "requests" in names
        assert "click" in names

    def test_parse_requirements_txt_empty(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        req = tmp_path / "requirements.txt"
        req.write_text("# Just comments\n\n# No deps\n")
        deps = ManifestParser().parse_requirements_txt(req)
        assert deps == []

    def test_parse_requirements_txt_nonexistent(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        deps = ManifestParser().parse_requirements_txt(tmp_path / "missing.txt")
        assert deps == []

    def test_parse_package_json_basic(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        pkg = tmp_path / "package.json"
        pkg.write_text(
            json.dumps(
                {
                    "name": "myapp",
                    "version": "2.0.0",
                    "description": "Test Node app",
                    "dependencies": {
                        "react": "^18.0.0",
                        "axios": "^1.0.0",
                    },
                    "devDependencies": {
                        "jest": "^29.0.0",
                    },
                }
            )
        )
        meta, deps = ManifestParser().parse_package_json(pkg)
        assert meta["name"] == "myapp"
        assert meta["version"] == "2.0.0"
        assert len(deps) >= 2
        dev_deps = [d for d in deps if d.is_dev]
        assert len(dev_deps) >= 1

    def test_parse_package_json_minimal(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({"name": "minimal"}))
        meta, deps = ManifestParser().parse_package_json(pkg)
        assert meta["name"] == "minimal"
        assert deps == []

    def test_parse_package_json_nonexistent(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        meta, deps = ManifestParser().parse_package_json(tmp_path / "missing.json")
        assert isinstance(meta, dict)
        assert isinstance(deps, list)

    def test_parse_dispatch_setup_py(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        f = tmp_path / "setup.py"
        f.write_text("setup(name='x', version='1.0')\n")
        meta, deps = ManifestParser().parse(f)
        assert isinstance(meta, dict)

    def test_parse_dispatch_requirements_txt(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        f = tmp_path / "requirements.txt"
        f.write_text("requests>=2.0\n")
        meta, deps = ManifestParser().parse(f)
        assert isinstance(meta, dict)
        assert isinstance(deps, list)

    def test_parse_dispatch_package_json(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        f = tmp_path / "package.json"
        f.write_text('{"name": "test"}')
        meta, deps = ManifestParser().parse(f)
        assert isinstance(meta, dict)

    def test_parse_dispatch_unknown_raises(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        f = tmp_path / "unknown_manifest.yml"
        f.write_text("something: true\n")
        with pytest.raises(ValueError, match="Unknown manifest"):
            ManifestParser().parse(f)

    def test_parse_requirement_line_editable(self):
        from cogant.ingest.manifest import ManifestParser

        dep = ManifestParser._parse_requirement_line("-e file:./mylib")
        assert dep is not None
        assert dep.is_local is True

    def test_parse_requirement_line_empty(self):
        from cogant.ingest.manifest import ManifestParser

        dep = ManifestParser._parse_requirement_line("")
        assert dep is None

    def test_parse_requirements_string(self):
        from cogant.ingest.manifest import ManifestParser

        deps = ManifestParser._parse_requirements_string(
            '"requests>=2.0", "click>=7.0", "pydantic"'
        )
        assert isinstance(deps, list)
        assert len(deps) >= 2

    def test_parse_requirement_list(self):
        from cogant.ingest.manifest import ManifestParser

        deps = ManifestParser._parse_requirement_list(["requests>=2.0", "click==8.0", ""])
        assert isinstance(deps, list)
        assert len(deps) >= 2

    def test_parse_setup_py_with_extras_require(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        setup = tmp_path / "setup.py"
        setup.write_text(
            "setup(\n"
            '    name="mylib",\n'
            '    install_requires=["requests"],\n'
            '    extras_require={"dev": ["pytest", "black"]},\n'
            ")\n"
        )
        meta, deps = ManifestParser().parse_setup_py(setup)
        dev_deps = [d for d in deps if d.is_dev]
        assert len(dev_deps) >= 1


# ---------------------------------------------------------------------------
# ingest/repo.py — RepoMetadata, RepoSnapshot, RepoIngester local paths
# ---------------------------------------------------------------------------


class TestRepoMetadata:
    def test_basic_creation(self):
        from cogant.ingest.repo import RepoMetadata

        meta = RepoMetadata(name="myrepo", url="file:///myrepo")
        assert meta.name == "myrepo"
        assert meta.url == "file:///myrepo"
        assert meta.commit_hash is None
        assert meta.language is None


class TestRepoSnapshot:
    def test_basic_creation(self, tmp_path):
        from cogant.ingest.repo import RepoMetadata, RepoSnapshot

        meta = RepoMetadata(name="test", url="file:///test")
        snapshot = RepoSnapshot(
            metadata=meta,
            files=[],
            dependencies=[],
            root_path=tmp_path,
        )
        assert snapshot.metadata.name == "test"
        assert snapshot.files == []
        assert snapshot.root_path == tmp_path


class TestRepoIngester:
    def test_init(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        ingester = RepoIngester(work_dir=tmp_path)
        assert ingester is not None
        assert ingester.work_dir == tmp_path

    def test_init_default_work_dir(self):
        from cogant.ingest.repo import RepoIngester

        ingester = RepoIngester()
        assert ingester.work_dir is not None

    def test_ingest_local_basic(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        (tmp_path / "main.py").write_text("x = 1\n")
        ingester = RepoIngester(work_dir=tmp_path / "work")
        snapshot = ingester.ingest_local(tmp_path)
        assert snapshot is not None
        assert snapshot.root_path.exists()
        assert isinstance(snapshot.files, list)
        assert isinstance(snapshot.dependencies, list)

    def test_ingest_local_with_python_files(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        (tmp_path / "main.py").write_text("def main(): pass\n")
        (tmp_path / "util.py").write_text("def helper(): pass\n")
        ingester = RepoIngester(work_dir=tmp_path / "work")
        snapshot = ingester.ingest_local(tmp_path)
        py_files = [f for f in snapshot.files if f.path.suffix == ".py"]
        assert len(py_files) >= 1

    def test_ingest_local_nonexistent_raises(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        ingester = RepoIngester(work_dir=tmp_path / "work")
        with pytest.raises(ValueError, match="does not exist"):
            ingester.ingest_local(tmp_path / "nonexistent_dir")

    def test_ingest_local_not_dir_raises(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        f = tmp_path / "myfile.py"
        f.write_text("x = 1\n")
        ingester = RepoIngester(work_dir=tmp_path / "work")
        with pytest.raises(ValueError, match="not a directory"):
            ingester.ingest_local(f)

    def test_ingest_local_with_requirements(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        (tmp_path / "main.py").write_text("import requests\n")
        (tmp_path / "requirements.txt").write_text("requests>=2.0\nclick\n")
        ingester = RepoIngester(work_dir=tmp_path / "work")
        snapshot = ingester.ingest_local(tmp_path)
        dep_names = [d.name for d in snapshot.dependencies]
        assert "requests" in dep_names

    def test_ingest_local_detects_primary_language(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        (tmp_path / "a.py").write_text("x = 1\n")
        (tmp_path / "b.py").write_text("y = 2\n")
        (tmp_path / "c.py").write_text("z = 3\n")
        ingester = RepoIngester(work_dir=tmp_path / "work")
        snapshot = ingester.ingest_local(tmp_path)
        assert snapshot.metadata.language == "python"

    def test_extract_metadata_non_git(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        ingester = RepoIngester(work_dir=tmp_path / "work")
        meta = ingester._extract_metadata(tmp_path)
        assert meta.name == tmp_path.name
        assert meta.url == str(tmp_path)

    def test_extract_dependencies_empty_dir(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        ingester = RepoIngester(work_dir=tmp_path / "work")
        deps = ingester._extract_dependencies(tmp_path)
        assert deps == []

    def test_extract_dependencies_with_cargo(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        (tmp_path / "Cargo.toml").write_text(
            '[package]\nname = "mylib"\nversion = "1.0.0"\n[dependencies]\nserde = "1.0"\n'
        )
        ingester = RepoIngester(work_dir=tmp_path / "work")
        deps = ingester._extract_dependencies(tmp_path)
        dep_names = [d.name for d in deps]
        assert "serde" in dep_names

    def test_extract_dependencies_deduplication(self, tmp_path):
        from cogant.ingest.repo import RepoIngester

        (tmp_path / "requirements.txt").write_text("requests>=2.0\nrequests>=2.0\n")
        ingester = RepoIngester(work_dir=tmp_path / "work")
        deps = ingester._extract_dependencies(tmp_path)
        # After dedup, only one requests
        req_deps = [d for d in deps if d.name == "requests"]
        assert len(req_deps) == 1


# ---------------------------------------------------------------------------
# static/dataflow.py — class body and method analysis
# ---------------------------------------------------------------------------


class TestDataFlowAnalyzerAdditional:
    def test_analyze_source_with_class_body(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        src = """
class Config:
    MAX_RETRIES: int = 3
    default_timeout = 30

    def __init__(self, timeout=None):
        self.timeout = timeout or self.default_timeout

    def reset(self):
        self.timeout = self.default_timeout
"""
        fp = tmp_path / "cfg.py"
        flows = DataFlowAnalyzer().analyze_source(src, fp)
        assert isinstance(flows, list)

    def test_analyze_source_with_augassign(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        src = "total = 0\ntotal += 5\ntotal -= 1\ntotal *= 2\n"
        fp = tmp_path / "aug.py"
        flows = DataFlowAnalyzer().analyze_source(src, fp)
        assert isinstance(flows, list)

    def test_analyze_source_with_annassign(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        src = "x: int = 5\ny: str\nz: float = 3.14\n"
        fp = tmp_path / "ann.py"
        flows = DataFlowAnalyzer().analyze_source(src, fp)
        assert isinstance(flows, list)

    def test_analyze_source_with_return_statement(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        src = """
def compute(a, b):
    result = a + b
    return result
"""
        fp = tmp_path / "ret.py"
        flows = DataFlowAnalyzer().analyze_source(src, fp)
        assert isinstance(flows, list)

    def test_analyze_source_invalid_syntax_returns_empty(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        src = "def broken(:\n    pass\n"
        fp = tmp_path / "bad.py"
        flows = DataFlowAnalyzer().analyze_source(src, fp)
        assert flows == []

    def test_analyze_file_nonexistent(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        flows = DataFlowAnalyzer().analyze_file(tmp_path / "missing.py")
        assert flows == []

    def test_analyze_source_with_call_nodes(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        src = """
def process():
    data = load_data()
    result = transform(data)
    save(result)
    return result
"""
        fp = tmp_path / "calls.py"
        flows = DataFlowAnalyzer().analyze_source(src, fp)
        assert isinstance(flows, list)

    def test_analyze_source_async_function(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        src = """
async def fetch_data():
    result = await get_response()
    return result
"""
        fp = tmp_path / "async.py"
        flows = DataFlowAnalyzer().analyze_source(src, fp)
        assert isinstance(flows, list)

    def test_dataflow_edge_fields(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer, DataFlowEdge

        src = "x = 5\ny = x + 1\n"
        fp = tmp_path / "edge.py"
        flows = DataFlowAnalyzer().analyze_source(src, fp)
        for edge in flows:
            assert isinstance(edge, DataFlowEdge)
            assert isinstance(edge.id, str)
            assert isinstance(edge.edge_type, str)


# ---------------------------------------------------------------------------
# gnn/package.py — GNNPackageBuilder init and helpers
# ---------------------------------------------------------------------------


class TestGNNPackageBuilderHelpers:
    def _make_components(self):
        from cogant.process.extractor import ProcessModel
        from cogant.schemas.graph import GraphMetadata, ProgramGraph
        from cogant.statespace.compiler import StateSpaceModel
        from cogant.statespace.temporal import TimeRegime

        graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///test"))
        state_space = StateSpaceModel(
            id="ss1",
            schema_name="test",
            variables={},
            observations={},
            actions={},
            transitions={},
            likelihoods={},
            preferences={},
            time_regime=TimeRegime.SYNCHRONOUS,
        )
        process_model = ProcessModel(id="pm1", schema_name="test", stages={}, connections={})
        return graph, state_space, process_model

    def test_enum_value_with_enum(self):
        from cogant.gnn.package import _enum_value
        from cogant.schemas.core import NodeKind

        result = _enum_value(NodeKind.FUNCTION)
        assert isinstance(result, str)
        assert result == "function"  # unwrapped to string value

    def test_enum_value_with_plain_value(self):
        from cogant.gnn.package import _enum_value

        assert _enum_value("hello") == "hello"
        assert _enum_value(42) == 42
        assert _enum_value(None) is None

    def test_package_builder_init(self):
        from cogant.gnn.package import GNNPackageBuilder

        graph, ss, pm = self._make_components()
        builder = GNNPackageBuilder(
            graph=graph,
            state_space=ss,
            process_model=pm,
            mappings={},
        )
        assert builder is not None
        assert builder.graph is graph
        assert builder.state_space is ss
        assert builder.config == {}

    def test_package_builder_init_with_config(self):
        from cogant.gnn.package import GNNPackageBuilder

        graph, ss, pm = self._make_components()
        builder = GNNPackageBuilder(
            graph=graph,
            state_space=ss,
            process_model=pm,
            mappings={},
            config={"key": "value"},
        )
        assert builder.config == {"key": "value"}

    def test_package_builder_has_required_files(self):
        from cogant.gnn.package import GNNPackageBuilder

        assert isinstance(GNNPackageBuilder.REQUIRED_FILES, list)
        assert "manifest.json" in GNNPackageBuilder.REQUIRED_FILES
        assert "model.gnn.json" in GNNPackageBuilder.REQUIRED_FILES

    def test_package_builder_package_version(self):
        from cogant.gnn.package import GNNPackageBuilder

        assert isinstance(GNNPackageBuilder.PACKAGE_VERSION, str)
        assert "." in GNNPackageBuilder.PACKAGE_VERSION
