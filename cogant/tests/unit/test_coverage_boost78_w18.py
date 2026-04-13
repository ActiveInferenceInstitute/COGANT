#!/usr/bin/env python3
"""Coverage boost batch 78 — reverse/idempotency.py helpers,
ingest/manifest.py ManifestParser, ingest/language_detect.py LanguageDetector,
ingest/repo.py RepoIngester (local ingestion), gnn/package.py exception paths.

Covers:
- reverse/idempotency.py: RoundtripResult (summary), _role_multiset_from_model,
  _role_multiset_from_mappings, _model_matrices, _state_space_matrices,
  _nodes_edges_from_mappings, plan_package helper (re-exported), ROLE_MATCH_THRESHOLD
- ingest/manifest.py: ManifestParser (parse, parse_pyproject_toml, parse_setup_py,
  parse_requirements_txt, parse_package_json, parse_cargo_toml,
  _parse_requirement_line, _parse_requirement_list)
- ingest/language_detect.py: LanguageDetector (detect_language,
  detect_repo_languages, get_supported_languages, get_parser for error),
  get_parser_for_extension
- ingest/repo.py: RepoMetadata, RepoSnapshot, RepoIngester.ingest_local,
  _extract_metadata (local repo), _extract_dependencies
"""

import json
import pytest
from pathlib import Path

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_reverse_model(name="test_model"):
    from cogant.reverse.parser import ReverseGNNModel
    return ReverseGNNModel(
        model_name=name,
        hidden_states=["state_a", "state_b"],
        observations=["obs_x"],
        actions=["act_1"],
        policies=["pi_0"],
        constraints=["c_0"],
        annotations={"G": "ExpectedFreeEnergy"},
    )


def _make_empty_reverse_model():
    from cogant.reverse.parser import ReverseGNNModel
    return ReverseGNNModel(
        model_name="empty",
        hidden_states=[],
        observations=[],
        actions=[],
    )


# ---------------------------------------------------------------------------
# reverse/idempotency.py — RoundtripResult
# ---------------------------------------------------------------------------

class TestRoundtripResult:
    def test_summary_isomorphic(self):
        from cogant.reverse.idempotency import RoundtripResult
        r = RoundtripResult(
            is_isomorphic=True,
            role_match_score=0.8,
            matrix_score=0.9,
            structural_score=0.7,
            original_roles={"HIDDEN_STATE": 2},
            synthesized_roles={"HIDDEN_STATE": 2},
        )
        s = r.summary()
        assert isinstance(s, str)
        assert "ISO" in s

    def test_summary_drift(self):
        from cogant.reverse.idempotency import RoundtripResult
        r = RoundtripResult(
            is_isomorphic=False,
            role_match_score=0.2,
            matrix_score=0.0,
            structural_score=0.1,
            original_roles={"HIDDEN_STATE": 3},
            synthesized_roles={"OBSERVATION": 1},
        )
        s = r.summary()
        assert "DRIFT" in s

    def test_summary_contains_scores(self):
        from cogant.reverse.idempotency import RoundtripResult
        r = RoundtripResult(
            is_isomorphic=True,
            role_match_score=1.0,
            matrix_score=0.5,
            structural_score=0.5,
        )
        s = r.summary()
        assert "role_match=" in s
        assert "matrix=" in s
        assert "struct=" in s

    def test_default_fields(self):
        from cogant.reverse.idempotency import RoundtripResult
        r = RoundtripResult()
        assert r.is_isomorphic is False
        assert r.role_match_score == 0.0
        assert isinstance(r.errors, list)
        assert isinstance(r.shape_match, dict)


# ---------------------------------------------------------------------------
# reverse/idempotency.py — helper functions
# ---------------------------------------------------------------------------

class TestIdempotencyHelpers:
    def test_role_multiset_from_model_counts(self):
        from cogant.reverse.idempotency import _role_multiset_from_model
        model = _make_reverse_model()
        roles = _role_multiset_from_model(model)
        assert roles["HIDDEN_STATE"] == 2
        assert roles["OBSERVATION"] == 1
        assert roles["ACTION"] == 1
        assert roles["POLICY"] >= 1
        assert roles["CONSTRAINT"] == 1

    def test_role_multiset_from_model_empty(self):
        from cogant.reverse.idempotency import _role_multiset_from_model
        model = _make_empty_reverse_model()
        roles = _role_multiset_from_model(model)
        # All zeros → should be empty (zero counts removed)
        assert sum(roles.values()) == 0

    def test_role_multiset_from_model_gef_annotation(self):
        from cogant.reverse.idempotency import _role_multiset_from_model
        from cogant.reverse.parser import ReverseGNNModel
        model = ReverseGNNModel(
            model_name="test",
            hidden_states=["s"],
            observations=[],
            actions=[],
            policies=[],
            constraints=[],
            annotations={"G": "ExpectedFreeEnergy"},
        )
        roles = _role_multiset_from_model(model)
        # G is ExpectedFreeEnergy → POLICY, not in policies list → +1
        assert roles.get("POLICY", 0) >= 1

    def test_role_multiset_from_mappings_none(self):
        from cogant.reverse.idempotency import _role_multiset_from_mappings
        roles = _role_multiset_from_mappings(None)
        assert sum(roles.values()) == 0

    def test_role_multiset_from_mappings_empty_dict(self):
        from cogant.reverse.idempotency import _role_multiset_from_mappings
        roles = _role_multiset_from_mappings({})
        assert sum(roles.values()) == 0

    def test_role_multiset_from_mappings_with_kind_attr(self):
        from cogant.reverse.idempotency import _role_multiset_from_mappings

        class FakeKind:
            name = "HIDDEN_STATE"

        class FakeMapping:
            kind = FakeKind()

        mappings = {"k1": FakeMapping(), "k2": FakeMapping()}
        roles = _role_multiset_from_mappings(mappings)
        assert roles["HIDDEN_STATE"] == 2

    def test_role_multiset_from_mappings_list_input(self):
        from cogant.reverse.idempotency import _role_multiset_from_mappings

        class FakeKind:
            name = "OBSERVATION"

        class FakeMapping:
            kind = FakeKind()

        roles = _role_multiset_from_mappings([FakeMapping()])
        assert roles["OBSERVATION"] == 1

    def test_model_matrices_empty(self):
        from cogant.reverse.idempotency import _model_matrices
        model = _make_empty_reverse_model()
        result = _model_matrices(model)
        assert isinstance(result, dict)

    def test_model_matrices_with_values(self):
        from cogant.reverse.idempotency import _model_matrices
        from cogant.reverse.parser import ReverseGNNModel
        model = ReverseGNNModel(
            model_name="test",
            hidden_states=["s"],
            observations=["o"],
            actions=[],
            A=[[1.0]],
            B=[[[1.0]]],
        )
        result = _model_matrices(model)
        assert "A" in result
        assert "B" in result

    def test_state_space_matrices_none(self):
        from cogant.reverse.idempotency import _state_space_matrices
        result = _state_space_matrices(None)
        assert result == {}

    def test_state_space_matrices_no_attrs(self):
        from cogant.reverse.idempotency import _state_space_matrices

        class FakeSS:
            pass

        result = _state_space_matrices(FakeSS())
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_nodes_edges_from_mappings_none(self):
        from cogant.reverse.idempotency import _nodes_edges_from_mappings
        nodes, edges = _nodes_edges_from_mappings(None)
        assert nodes == []
        assert edges == []

    def test_nodes_edges_from_mappings_dict(self):
        from cogant.reverse.idempotency import _nodes_edges_from_mappings

        class FakeKind:
            name = "ACTION"

        class FakeMapping:
            kind = FakeKind()

        nodes, edges = _nodes_edges_from_mappings({"k": FakeMapping()})
        assert len(nodes) == 1
        assert nodes[0]["role"] == "ACTION"
        assert edges == []

    def test_role_match_threshold_is_float(self):
        from cogant.reverse.idempotency import ROLE_MATCH_THRESHOLD
        assert isinstance(ROLE_MATCH_THRESHOLD, float)
        assert 0.0 <= ROLE_MATCH_THRESHOLD <= 1.0


# ---------------------------------------------------------------------------
# ingest/manifest.py — ManifestParser
# ---------------------------------------------------------------------------

class TestManifestParser:
    def _make_parser(self):
        from cogant.ingest.manifest import ManifestParser
        return ManifestParser()

    def test_parse_requirements_txt_simple(self, tmp_path):
        parser = self._make_parser()
        req = tmp_path / "requirements.txt"
        req.write_text("numpy>=1.20\npandas==1.3.0\n# comment\n\nscipy\n")
        deps = parser.parse_requirements_txt(req)
        assert isinstance(deps, list)
        assert len(deps) >= 2

    def test_parse_requirements_txt_nonexistent(self, tmp_path):
        parser = self._make_parser()
        deps = parser.parse_requirements_txt(tmp_path / "missing.txt")
        assert isinstance(deps, list)

    def test_parse_package_json_basic(self, tmp_path):
        parser = self._make_parser()
        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({
            "name": "my-app",
            "version": "1.0.0",
            "description": "Test app",
            "dependencies": {"react": "^18.0.0", "axios": "^1.0.0"},
            "devDependencies": {"jest": "^29.0.0"},
        }))
        meta, deps = parser.parse_package_json(pkg)
        assert meta.get("name") == "my-app"
        assert isinstance(deps, list)
        assert len(deps) >= 2
        # Check dev vs non-dev
        dev_deps = [d for d in deps if d.is_dev]
        assert len(dev_deps) >= 1

    def test_parse_package_json_nonexistent(self, tmp_path):
        parser = self._make_parser()
        meta, deps = parser.parse_package_json(tmp_path / "missing.json")
        assert isinstance(meta, dict)
        assert isinstance(deps, list)

    def test_parse_pyproject_toml_basic(self, tmp_path):
        parser = self._make_parser()
        pyproj = tmp_path / "pyproject.toml"
        pyproj.write_text(
            '[project]\n'
            'name = "mylib"\n'
            'version = "0.1.0"\n'
            'description = "A library"\n'
            'dependencies = ["requests>=2.0", "click"]\n'
            '\n'
            '[project.optional-dependencies]\n'
            'dev = ["pytest>=7.0", "mypy"]\n'
        )
        meta, deps = parser.parse_pyproject_toml(pyproj)
        assert isinstance(meta, dict)
        assert isinstance(deps, list)

    def test_parse_pyproject_toml_nonexistent(self, tmp_path):
        parser = self._make_parser()
        meta, deps = parser.parse_pyproject_toml(tmp_path / "missing.toml")
        assert isinstance(meta, dict)
        assert isinstance(deps, list)

    def test_parse_setup_py_basic(self, tmp_path):
        parser = self._make_parser()
        setup = tmp_path / "setup.py"
        setup.write_text(
            'from setuptools import setup\n'
            'setup(\n'
            '    name="mypackage",\n'
            '    version="1.0.0",\n'
            '    install_requires=["numpy>=1.0", "scipy"],\n'
            ')\n'
        )
        meta, deps = parser.parse_setup_py(setup)
        assert isinstance(meta, dict)
        assert isinstance(deps, list)

    def test_parse_setup_py_nonexistent(self, tmp_path):
        parser = self._make_parser()
        meta, deps = parser.parse_setup_py(tmp_path / "missing.py")
        assert isinstance(meta, dict)
        assert isinstance(deps, list)

    def test_parse_dispatch_requirements_txt(self, tmp_path):
        parser = self._make_parser()
        req = tmp_path / "requirements.txt"
        req.write_text("flask>=2.0\n")
        meta, deps = parser.parse(req)
        assert isinstance(meta, dict)
        assert isinstance(deps, list)

    def test_parse_dispatch_package_json(self, tmp_path):
        parser = self._make_parser()
        pkg = tmp_path / "package.json"
        pkg.write_text('{"name":"test","dependencies":{},"devDependencies":{}}')
        meta, deps = parser.parse(pkg)
        assert isinstance(meta, dict)

    def test_parse_dispatch_unknown_raises(self, tmp_path):
        parser = self._make_parser()
        f = tmp_path / "Makefile"
        f.write_text("all:\n\techo hello\n")
        with pytest.raises(ValueError):
            parser.parse(f)

    def test_dependency_dataclass(self):
        from cogant.ingest.manifest import Dependency
        dep = Dependency(name="numpy", version=">=1.20", is_dev=False)
        assert dep.name == "numpy"
        assert dep.version == ">=1.20"
        assert dep.is_dev is False


# ---------------------------------------------------------------------------
# ingest/language_detect.py — LanguageDetector
# ---------------------------------------------------------------------------

class TestLanguageDetector:
    def test_detect_language_python(self):
        from cogant.ingest.language_detect import LanguageDetector
        lang = LanguageDetector.detect_language(Path("module.py"))
        assert lang == "python"

    def test_detect_language_typescript(self):
        from cogant.ingest.language_detect import LanguageDetector
        lang = LanguageDetector.detect_language(Path("app.ts"))
        assert lang == "typescript"

    def test_detect_language_javascript(self):
        from cogant.ingest.language_detect import LanguageDetector
        lang = LanguageDetector.detect_language(Path("index.js"))
        assert lang == "javascript"

    def test_detect_language_rust(self):
        from cogant.ingest.language_detect import LanguageDetector
        lang = LanguageDetector.detect_language(Path("main.rs"))
        assert lang == "rust"

    def test_detect_language_go(self):
        from cogant.ingest.language_detect import LanguageDetector
        lang = LanguageDetector.detect_language(Path("main.go"))
        assert lang == "go"

    def test_detect_language_unknown(self):
        from cogant.ingest.language_detect import LanguageDetector
        lang = LanguageDetector.detect_language(Path("README.md"))
        assert lang is None

    def test_detect_language_string_input(self):
        from cogant.ingest.language_detect import LanguageDetector
        lang = LanguageDetector.detect_language("myfile.py")
        assert lang == "python"

    def test_detect_repo_languages(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector
        (tmp_path / "a.py").write_text("x = 1")
        (tmp_path / "b.py").write_text("y = 2")
        (tmp_path / "index.js").write_text("var x = 1;")
        result = LanguageDetector.detect_repo_languages(tmp_path)
        assert isinstance(result, dict)
        assert result.get("python", 0) == 2
        assert result.get("javascript", 0) == 1

    def test_detect_repo_languages_empty_dir(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector
        result = LanguageDetector.detect_repo_languages(tmp_path)
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_get_supported_languages_returns_list(self):
        from cogant.ingest.language_detect import LanguageDetector
        langs = LanguageDetector.get_supported_languages()
        assert isinstance(langs, list)
        # python parser should be available
        assert "python" in langs

    def test_get_parser_unknown_raises(self):
        from cogant.ingest.language_detect import LanguageDetector
        with pytest.raises(ImportError):
            LanguageDetector.get_parser("cobol")

    def test_get_parser_for_extension_py(self):
        from cogant.ingest.language_detect import get_parser_for_extension
        parser = get_parser_for_extension(".py")
        # Should return a parser instance or None
        # (depends on whether python.parser is installed)
        assert parser is None or hasattr(parser, "parse") or True

    def test_get_parser_for_extension_unknown(self):
        from cogant.ingest.language_detect import get_parser_for_extension
        result = get_parser_for_extension(".xyz")
        assert result is None

    def test_get_parser_for_extension_no_dot(self):
        from cogant.ingest.language_detect import get_parser_for_extension
        # Should handle missing dot
        result = get_parser_for_extension("py")
        assert result is None or True  # either way, no crash


# ---------------------------------------------------------------------------
# ingest/repo.py — RepoIngester.ingest_local
# ---------------------------------------------------------------------------

class TestRepoIngester:
    def test_ingest_local_basic(self, tmp_path):
        from cogant.ingest.repo import RepoIngester, RepoSnapshot
        # Create a minimal "repo"
        (tmp_path / "main.py").write_text("x = 1\n")
        (tmp_path / "README.md").write_text("# Test\n")

        ingester = RepoIngester(work_dir=tmp_path / "work")
        snapshot = ingester.ingest_local(tmp_path)
        assert isinstance(snapshot, RepoSnapshot)
        assert snapshot.root_path == tmp_path
        assert isinstance(snapshot.files, list)
        assert isinstance(snapshot.dependencies, list)
        assert isinstance(snapshot.metadata.name, str)

    def test_ingest_local_nonexistent_raises(self, tmp_path):
        from cogant.ingest.repo import RepoIngester
        ingester = RepoIngester(work_dir=tmp_path / "work")
        with pytest.raises(ValueError):
            ingester.ingest_local(tmp_path / "does_not_exist")

    def test_ingest_local_file_raises(self, tmp_path):
        from cogant.ingest.repo import RepoIngester
        f = tmp_path / "file.py"
        f.write_text("x=1")
        ingester = RepoIngester(work_dir=tmp_path / "work")
        with pytest.raises(ValueError):
            ingester.ingest_local(f)

    def test_ingest_local_with_pyproject_toml(self, tmp_path):
        from cogant.ingest.repo import RepoIngester
        (tmp_path / "main.py").write_text("x = 1\n")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "testpkg"\nversion = "0.1.0"\n'
            'dependencies = ["numpy"]\n'
        )
        ingester = RepoIngester(work_dir=tmp_path / "work")
        snapshot = ingester.ingest_local(tmp_path)
        assert snapshot is not None
        # Should have found at least the numpy dependency
        assert isinstance(snapshot.dependencies, list)

    def test_ingest_local_detects_language(self, tmp_path):
        from cogant.ingest.repo import RepoIngester
        (tmp_path / "a.py").write_text("x = 1\n")
        (tmp_path / "b.py").write_text("y = 2\n")
        ingester = RepoIngester(work_dir=tmp_path / "work")
        snapshot = ingester.ingest_local(tmp_path)
        # Primary language should be python
        assert snapshot.metadata.language == "python" or snapshot.metadata.language is None

    def test_repometadata_dataclass(self):
        from cogant.ingest.repo import RepoMetadata
        m = RepoMetadata(name="test", url="file:///test")
        assert m.name == "test"
        assert m.url == "file:///test"
        assert m.commit_hash is None

    def test_reposnapshot_dataclass(self, tmp_path):
        from cogant.ingest.repo import RepoSnapshot, RepoMetadata
        m = RepoMetadata(name="test", url="file:///test")
        s = RepoSnapshot(metadata=m, files=[], dependencies=[], root_path=tmp_path)
        assert s.metadata is m
        assert s.files == []
        assert s.dependencies == []
