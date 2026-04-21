#!/usr/bin/env python3
"""Coverage boost batch 38 — ingest/language_detect.py, ingest/manifest.py,
dynamic/enrichment.py helpers.

Covers:
- LanguageDetector: detect_language, detect_repo_languages, get_supported_languages,
  get_parser (ImportError path), EXTENSION_MAP
- ManifestParser: parse (dispatch), parse_requirements_txt, parse_package_json,
  parse_setup_py, parse_pyproject_toml, parse_cargo_toml,
  _parse_requirement_line, _parse_requirement_list, _parse_requirements_string
- dynamic/enrichment: _normalize_path, _node_spans_line, _stable_edge_id,
  _build_function_index, enrich_graph (no-op paths)
- reverse/idempotency: RoundtripResult dataclass, _ONTOLOGY_TO_ROLE,
  _role_multiset_from_model, _role_multiset_from_mappings,
  _model_matrices, _state_space_matrices, _nodes_edges_from_mappings
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# LanguageDetector
# ---------------------------------------------------------------------------


class TestLanguageDetectorDetectLanguage:
    def test_py_extension(self):
        from cogant.ingest.language_detect import LanguageDetector

        assert LanguageDetector.detect_language(Path("foo.py")) == "python"

    def test_ts_extension(self):
        from cogant.ingest.language_detect import LanguageDetector

        assert LanguageDetector.detect_language(Path("foo.ts")) == "typescript"

    def test_tsx_extension(self):
        from cogant.ingest.language_detect import LanguageDetector

        assert LanguageDetector.detect_language(Path("foo.tsx")) == "typescript"

    def test_js_extension(self):
        from cogant.ingest.language_detect import LanguageDetector

        assert LanguageDetector.detect_language(Path("foo.js")) == "javascript"

    def test_jsx_extension(self):
        from cogant.ingest.language_detect import LanguageDetector

        assert LanguageDetector.detect_language(Path("foo.jsx")) == "javascript"

    def test_rs_extension(self):
        from cogant.ingest.language_detect import LanguageDetector

        assert LanguageDetector.detect_language(Path("foo.rs")) == "rust"

    def test_go_extension(self):
        from cogant.ingest.language_detect import LanguageDetector

        assert LanguageDetector.detect_language(Path("foo.go")) == "go"

    def test_pyx_extension(self):
        from cogant.ingest.language_detect import LanguageDetector

        assert LanguageDetector.detect_language(Path("foo.pyx")) == "python"

    def test_pyi_extension(self):
        from cogant.ingest.language_detect import LanguageDetector

        assert LanguageDetector.detect_language(Path("foo.pyi")) == "python"

    def test_unknown_extension_returns_none(self):
        from cogant.ingest.language_detect import LanguageDetector

        assert LanguageDetector.detect_language(Path("foo.xyz")) is None

    def test_accepts_string_path(self):
        from cogant.ingest.language_detect import LanguageDetector

        assert LanguageDetector.detect_language("foo.py") == "python"  # type: ignore

    def test_case_insensitive_extension(self):
        from cogant.ingest.language_detect import LanguageDetector

        # .PY should still match
        result = LanguageDetector.detect_language(Path("foo.PY"))
        assert result == "python"


class TestLanguageDetectorDetectRepoLanguages:
    def test_empty_dir_returns_empty(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        result = LanguageDetector.detect_repo_languages(tmp_path)
        assert result == {}

    def test_single_py_file(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        (tmp_path / "foo.py").write_text("x = 1")
        result = LanguageDetector.detect_repo_languages(tmp_path)
        assert result.get("python") == 1

    def test_multiple_py_files(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        (tmp_path / "a.py").write_text("x = 1")
        (tmp_path / "b.py").write_text("y = 2")
        result = LanguageDetector.detect_repo_languages(tmp_path)
        assert result.get("python") == 2

    def test_mixed_languages(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        (tmp_path / "a.py").write_text("x = 1")
        (tmp_path / "b.ts").write_text("const x = 1;")
        result = LanguageDetector.detect_repo_languages(tmp_path)
        assert result.get("python") == 1
        assert result.get("typescript") == 1

    def test_string_path(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        (tmp_path / "foo.py").write_text("x = 1")
        result = LanguageDetector.detect_repo_languages(str(tmp_path))  # type: ignore
        assert isinstance(result, dict)

    def test_nonexistent_dir_returns_empty(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        result = LanguageDetector.detect_repo_languages(tmp_path / "nonexistent")
        assert result == {}


class TestLanguageDetectorGetParser:
    def test_unsupported_language_raises_import_error(self):
        from cogant.ingest.language_detect import LanguageDetector

        with pytest.raises(ImportError):
            LanguageDetector.get_parser("brainfuck")

    def test_get_supported_languages_returns_list(self):
        from cogant.ingest.language_detect import LanguageDetector

        result = LanguageDetector.get_supported_languages()
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# ManifestParser — Dependency dataclass
# ---------------------------------------------------------------------------


class TestDependencyDataclass:
    def test_creation(self):
        from cogant.ingest.manifest import Dependency

        dep = Dependency(name="requests", version=">=2.0")
        assert dep.name == "requests"
        assert dep.version == ">=2.0"
        assert dep.is_dev is False
        assert dep.is_local is False

    def test_dev_dependency(self):
        from cogant.ingest.manifest import Dependency

        dep = Dependency(name="pytest", is_dev=True)
        assert dep.is_dev is True

    def test_local_dependency(self):
        from cogant.ingest.manifest import Dependency

        dep = Dependency(name="mylib", is_local=True)
        assert dep.is_local is True


class TestManifestParserRequirementLine:
    def test_simple_package(self):
        from cogant.ingest.manifest import ManifestParser

        dep = ManifestParser._parse_requirement_line("requests")
        assert dep is not None
        assert dep.name == "requests"

    def test_versioned_package(self):
        from cogant.ingest.manifest import ManifestParser

        dep = ManifestParser._parse_requirement_line("requests>=2.0,<3.0")
        assert dep is not None
        assert dep.name == "requests"
        assert ">=2.0" in dep.version

    def test_empty_line_returns_none(self):
        from cogant.ingest.manifest import ManifestParser

        dep = ManifestParser._parse_requirement_line("")
        assert dep is None

    def test_whitespace_only_returns_none(self):
        from cogant.ingest.manifest import ManifestParser

        dep = ManifestParser._parse_requirement_line("   ")
        assert dep is None

    def test_editable_install(self):
        from cogant.ingest.manifest import ManifestParser

        dep = ManifestParser._parse_requirement_line("-e file:./mylib")
        assert dep is not None
        assert dep.is_local is True


class TestManifestParserRequirementList:
    def test_parses_list(self):
        from cogant.ingest.manifest import ManifestParser

        deps = ManifestParser._parse_requirement_list(["requests>=2.0", "pytest"])
        assert len(deps) == 2
        assert deps[0].name == "requests"
        assert deps[1].name == "pytest"

    def test_empty_list(self):
        from cogant.ingest.manifest import ManifestParser

        deps = ManifestParser._parse_requirement_list([])
        assert deps == []


class TestManifestParserRequirementsString:
    def test_comma_separated(self):
        from cogant.ingest.manifest import ManifestParser

        deps = ManifestParser._parse_requirements_string('"requests", "pytest"')
        assert len(deps) == 2

    def test_empty_string(self):
        from cogant.ingest.manifest import ManifestParser

        deps = ManifestParser._parse_requirements_string("")
        assert deps == []


class TestManifestParserRequirementsTxt:
    def test_parses_requirements_txt(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests>=2.0\npytest\n# comment\n\nflask==2.0.0\n")
        parser = ManifestParser()
        deps = parser.parse_requirements_txt(req_file)
        names = [d.name for d in deps]
        assert "requests" in names
        assert "pytest" in names
        assert "flask" in names
        assert len(deps) == 3

    def test_skips_blank_and_comments(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        req_file = tmp_path / "requirements.txt"
        req_file.write_text("# This is a comment\n\ndjango>=3.0\n")
        parser = ManifestParser()
        deps = parser.parse_requirements_txt(req_file)
        assert len(deps) == 1
        assert deps[0].name == "django"

    def test_missing_file_returns_empty(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        parser = ManifestParser()
        deps = parser.parse_requirements_txt(tmp_path / "nonexistent.txt")
        assert deps == []


class TestManifestParserPackageJson:
    def test_parses_package_json(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        pkg = {
            "name": "myapp",
            "version": "1.0.0",
            "description": "test",
            "dependencies": {"react": "^18.0.0"},
            "devDependencies": {"jest": "^29.0.0"},
        }
        pkg_file = tmp_path / "package.json"
        pkg_file.write_text(json.dumps(pkg))
        parser = ManifestParser()
        meta, deps = parser.parse_package_json(pkg_file)
        assert meta["name"] == "myapp"
        assert meta["version"] == "1.0.0"
        names = [d.name for d in deps]
        assert "react" in names
        assert "jest" in names
        dev_deps = [d for d in deps if d.is_dev]
        assert any(d.name == "jest" for d in dev_deps)

    def test_missing_file_returns_empty(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        parser = ManifestParser()
        meta, deps = parser.parse_package_json(tmp_path / "no.json")
        assert meta == {}
        assert deps == []

    def test_no_deps_returns_empty_deps(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        pkg = {"name": "myapp", "version": "1.0.0"}
        pkg_file = tmp_path / "package.json"
        pkg_file.write_text(json.dumps(pkg))
        parser = ManifestParser()
        meta, deps = parser.parse_package_json(pkg_file)
        assert deps == []
        assert meta["name"] == "myapp"


class TestManifestParserSetupPy:
    def test_parses_setup_py(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        content = """
from setuptools import setup
setup(
    name="mypackage",
    version="1.0.0",
    description="A package",
    install_requires=["requests>=2.0", "flask"],
)
"""
        setup_file = tmp_path / "setup.py"
        setup_file.write_text(content)
        parser = ManifestParser()
        meta, deps = parser.parse_setup_py(setup_file)
        assert meta.get("name") == "mypackage"
        assert meta.get("version") == "1.0.0"
        names = [d.name for d in deps]
        assert "requests" in names

    def test_missing_file_returns_empty(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        parser = ManifestParser()
        meta, deps = parser.parse_setup_py(tmp_path / "nosetup.py")
        assert meta == {}
        assert deps == []


class TestManifestParserPyprojectToml:
    def test_parses_pyproject_toml(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        content = """
[project]
name = "myproject"
version = "0.1.0"
description = "A project"
dependencies = ["requests>=2.0", "flask"]

[project.optional-dependencies]
dev = ["pytest", "mypy"]
"""
        toml_file = tmp_path / "pyproject.toml"
        toml_file.write_bytes(content.encode())
        parser = ManifestParser()
        meta, deps = parser.parse_pyproject_toml(toml_file)
        assert meta.get("name") == "myproject"
        names = [d.name for d in deps]
        assert "requests" in names
        assert "pytest" in names

    def test_missing_file_returns_empty(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        parser = ManifestParser()
        meta, deps = parser.parse_pyproject_toml(tmp_path / "nopyproject.toml")
        assert meta == {}
        assert deps == []


class TestManifestParserCargoToml:
    def test_parses_cargo_toml(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        content = """
[package]
name = "mycrate"
version = "0.1.0"
description = "A crate"

[dependencies]
serde = "1.0"
tokio = { version = "1.0" }

[dev-dependencies]
cargo-test = "0.1"
"""
        cargo_file = tmp_path / "Cargo.toml"
        cargo_file.write_bytes(content.encode())
        parser = ManifestParser()
        meta, deps = parser.parse_cargo_toml(cargo_file)
        assert meta.get("name") == "mycrate"
        names = [d.name for d in deps]
        assert "serde" in names
        dev_deps = [d for d in deps if d.is_dev]
        assert any(d.name == "cargo-test" for d in dev_deps)

    def test_missing_file_returns_empty(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        parser = ManifestParser()
        meta, deps = parser.parse_cargo_toml(tmp_path / "no.toml")
        assert meta == {}
        assert deps == []


class TestManifestParserDispatch:
    def test_dispatch_requirements_txt(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests\n")
        parser = ManifestParser()
        meta, deps = parser.parse(req_file)
        assert meta == {}
        assert len(deps) >= 1

    def test_dispatch_unknown_raises(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        unknown = tmp_path / "unknown.yaml"
        unknown.write_text("key: value\n")
        parser = ManifestParser()
        with pytest.raises(ValueError):
            parser.parse(unknown)

    def test_dispatch_package_json(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        pkg = {"name": "app", "version": "1.0.0"}
        pkg_file = tmp_path / "package.json"
        pkg_file.write_text(json.dumps(pkg))
        parser = ManifestParser()
        meta, deps = parser.parse(pkg_file)
        assert meta["name"] == "app"


# ---------------------------------------------------------------------------
# dynamic/enrichment — helpers
# ---------------------------------------------------------------------------


class TestNormalizePath:
    def test_strips_leading_dotslash(self):
        from cogant.dynamic.enrichment import _normalize_path

        assert _normalize_path("./foo/bar.py") == "foo/bar.py"

    def test_strips_multiple_dotslash(self):
        from cogant.dynamic.enrichment import _normalize_path

        assert _normalize_path("././foo.py") == "foo.py"

    def test_converts_backslashes(self):
        from cogant.dynamic.enrichment import _normalize_path

        assert _normalize_path("foo\\bar\\baz.py") == "foo/bar/baz.py"

    def test_no_change_on_clean_path(self):
        from cogant.dynamic.enrichment import _normalize_path

        assert _normalize_path("foo/bar.py") == "foo/bar.py"


class TestNodeSpansLine:
    def _make_node(self, start, end):
        """Create a minimal node-like object."""

        class FakeNode:
            source_range = {"start_line": start, "end_line": end}

        return FakeNode()

    def test_line_within_range(self):
        from cogant.dynamic.enrichment import _node_spans_line

        node = self._make_node(10, 20)
        assert _node_spans_line(node, 15) is True

    def test_line_at_start(self):
        from cogant.dynamic.enrichment import _node_spans_line

        node = self._make_node(10, 20)
        assert _node_spans_line(node, 10) is True

    def test_line_at_end(self):
        from cogant.dynamic.enrichment import _node_spans_line

        node = self._make_node(10, 20)
        assert _node_spans_line(node, 20) is True

    def test_line_before_range(self):
        from cogant.dynamic.enrichment import _node_spans_line

        node = self._make_node(10, 20)
        assert _node_spans_line(node, 5) is False

    def test_line_after_range(self):
        from cogant.dynamic.enrichment import _node_spans_line

        node = self._make_node(10, 20)
        assert _node_spans_line(node, 25) is False

    def test_no_source_range(self):
        from cogant.dynamic.enrichment import _node_spans_line

        class FakeNode:
            source_range = None

        assert _node_spans_line(FakeNode(), 10) is False


class TestStableEdgeId:
    def test_returns_string(self):
        from cogant.dynamic.enrichment import _stable_edge_id

        result = _stable_edge_id("a", "b", "calls")
        assert isinstance(result, str)

    def test_deterministic(self):
        from cogant.dynamic.enrichment import _stable_edge_id

        r1 = _stable_edge_id("src", "tgt", "calls")
        r2 = _stable_edge_id("src", "tgt", "calls")
        assert r1 == r2

    def test_different_inputs_produce_different_ids(self):
        from cogant.dynamic.enrichment import _stable_edge_id

        r1 = _stable_edge_id("a", "b", "calls")
        r2 = _stable_edge_id("a", "c", "calls")
        assert r1 != r2

    def test_length_16(self):
        from cogant.dynamic.enrichment import _stable_edge_id

        assert len(_stable_edge_id("x", "y", "z")) == 16


class TestBuildFunctionIndex:
    def test_indexes_functions(self):
        from cogant.dynamic.enrichment import _build_function_index
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        fn = builder.add_node(NodeKind.FUNCTION, "myfunc", "mod.myfunc", path="mod.py")
        graph = builder.finalize()
        index = _build_function_index(graph)
        assert "myfunc" in index
        assert fn.id in index["myfunc"]

    def test_excludes_non_callable_nodes(self):
        from cogant.dynamic.enrichment import _build_function_index
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        builder.add_node(NodeKind.MODULE, "mymod", "mymod", path="mymod.py")
        graph = builder.finalize()
        index = _build_function_index(graph)
        assert "mymod" not in index

    def test_empty_graph(self):
        from cogant.dynamic.enrichment import _build_function_index
        from cogant.graph.builder import ProgramGraphBuilder

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        graph = builder.finalize()
        index = _build_function_index(graph)
        assert index == {}


class TestEnrichGraph:
    def test_no_paths_returns_summary(self):
        from cogant.dynamic.enrichment import enrich_graph
        from cogant.graph.builder import ProgramGraphBuilder

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        graph = builder.finalize()
        summary = enrich_graph(graph)
        assert summary["coverage_nodes_enriched"] == 0
        assert summary["trace_nodes_enriched"] == 0
        assert summary["evidence_sources"] == []
        assert summary["graph"] is graph


# ---------------------------------------------------------------------------
# reverse/idempotency — data model and helpers
# ---------------------------------------------------------------------------


class TestRoundtripResultDataclass:
    def test_defaults(self):
        from cogant.reverse.idempotency import RoundtripResult

        r = RoundtripResult()
        assert r.is_isomorphic is False
        assert r.role_match_score == 0.0
        assert r.matrix_score == 0.0
        assert r.structural_score == 0.0
        assert r.original_roles == {}
        assert r.synthesized_roles == {}
        assert r.shape_match == {}
        assert r.package_path is None
        assert r.errors == []

    def test_custom_values(self):
        from cogant.reverse.idempotency import RoundtripResult

        r = RoundtripResult(
            is_isomorphic=True,
            role_match_score=0.8,
            original_roles={"HIDDEN_STATE": 2},
            synthesized_roles={"HIDDEN_STATE": 2},
        )
        assert r.is_isomorphic is True
        assert r.role_match_score == 0.8

    def test_summary_iso(self):
        from cogant.reverse.idempotency import RoundtripResult

        r = RoundtripResult(is_isomorphic=True, role_match_score=1.0)
        s = r.summary()
        assert "ISO" in s

    def test_summary_drift(self):
        from cogant.reverse.idempotency import RoundtripResult

        r = RoundtripResult(is_isomorphic=False, role_match_score=0.3)
        s = r.summary()
        assert "DRIFT" in s

    def test_summary_contains_scores(self):
        from cogant.reverse.idempotency import RoundtripResult

        r = RoundtripResult(role_match_score=0.75, matrix_score=0.5, structural_score=0.6)
        s = r.summary()
        assert "role_match" in s
        assert "matrix" in s
        assert "struct" in s


class TestOntologyToRole:
    def test_hidden_state(self):
        from cogant.reverse.idempotency import _ONTOLOGY_TO_ROLE

        assert _ONTOLOGY_TO_ROLE["HiddenState"] == "HIDDEN_STATE"

    def test_observation(self):
        from cogant.reverse.idempotency import _ONTOLOGY_TO_ROLE

        assert _ONTOLOGY_TO_ROLE["Observation"] == "OBSERVATION"

    def test_action(self):
        from cogant.reverse.idempotency import _ONTOLOGY_TO_ROLE

        assert _ONTOLOGY_TO_ROLE["Action"] == "ACTION"

    def test_policy(self):
        from cogant.reverse.idempotency import _ONTOLOGY_TO_ROLE

        assert _ONTOLOGY_TO_ROLE["Policy"] == "POLICY"


class TestRoleMultisetFromMappings:
    def test_empty_returns_empty(self):
        from cogant.reverse.idempotency import _role_multiset_from_mappings

        result = _role_multiset_from_mappings(None)
        assert sum(result.values()) == 0

    def test_empty_dict_returns_empty(self):
        from cogant.reverse.idempotency import _role_multiset_from_mappings

        result = _role_multiset_from_mappings({})
        assert sum(result.values()) == 0

    def test_counts_kinds_from_mapping_objects(self):
        from cogant.reverse.idempotency import _role_multiset_from_mappings
        from cogant.schemas.semantic import MappingKind

        class FakeMapping:
            def __init__(self, kind):
                self.kind = kind

        mappings = {
            "a": FakeMapping(MappingKind.HIDDEN_STATE),
            "b": FakeMapping(MappingKind.OBSERVATION),
            "c": FakeMapping(MappingKind.HIDDEN_STATE),
        }
        result = _role_multiset_from_mappings(mappings)
        assert result["HIDDEN_STATE"] == 2
        assert result["OBSERVATION"] == 1

    def test_list_input(self):
        from cogant.reverse.idempotency import _role_multiset_from_mappings
        from cogant.schemas.semantic import MappingKind

        class FakeMapping:
            def __init__(self, kind):
                self.kind = kind

        mappings = [FakeMapping(MappingKind.ACTION)]
        result = _role_multiset_from_mappings(mappings)
        assert result["ACTION"] == 1


class TestModelMatrices:
    def test_empty_model_returns_empty(self):
        from cogant.reverse.idempotency import _model_matrices
        from cogant.reverse.parser import ReverseGNNModel

        model = ReverseGNNModel(model_name="test")
        result = _model_matrices(model)
        assert result == {}

    def test_model_with_A_included(self):
        from cogant.reverse.idempotency import _model_matrices
        from cogant.reverse.parser import ReverseGNNModel

        model = ReverseGNNModel(model_name="test", A=[[1.0, 0.0], [0.0, 1.0]])
        result = _model_matrices(model)
        assert "A" in result


class TestStateSpaceMatrices:
    def test_none_returns_empty(self):
        from cogant.reverse.idempotency import _state_space_matrices

        assert _state_space_matrices(None) == {}

    def test_object_without_matrices_returns_empty(self):
        from cogant.reverse.idempotency import _state_space_matrices

        class FakeSS:
            pass

        result = _state_space_matrices(FakeSS())
        assert result == {}

    def test_object_with_A_matrix(self):
        from cogant.reverse.idempotency import _state_space_matrices

        class FakeSS:
            A = [[1.0]]
            B = None
            C = None
            D = None

        result = _state_space_matrices(FakeSS())
        assert "A" in result
        assert "B" not in result


class TestNodesEdgesFromMappings:
    def test_none_returns_empty(self):
        from cogant.reverse.idempotency import _nodes_edges_from_mappings

        nodes, edges = _nodes_edges_from_mappings(None)
        assert nodes == []
        assert edges == []

    def test_empty_dict_returns_empty(self):
        from cogant.reverse.idempotency import _nodes_edges_from_mappings

        nodes, edges = _nodes_edges_from_mappings({})
        assert nodes == []
        assert edges == []

    def test_creates_node_per_mapping(self):
        from cogant.reverse.idempotency import _nodes_edges_from_mappings
        from cogant.schemas.semantic import MappingKind

        class FakeMapping:
            def __init__(self, kind):
                self.kind = kind

        mappings = {
            "a": FakeMapping(MappingKind.HIDDEN_STATE),
            "b": FakeMapping(MappingKind.OBSERVATION),
        }
        nodes, edges = _nodes_edges_from_mappings(mappings)
        assert len(nodes) == 2
        assert edges == []
        roles = {n["role"] for n in nodes}
        assert "HIDDEN_STATE" in roles
        assert "OBSERVATION" in roles
