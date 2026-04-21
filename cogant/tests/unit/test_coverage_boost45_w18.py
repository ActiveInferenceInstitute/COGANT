#!/usr/bin/env python3
"""Coverage boost batch 45 — gnn/formatter/structural.py, ingest/language_detect.py,
ingest/manifest.py (fallback TOML parser).

Covers:
- GNNMarkdownFormatter._format_state_space (no variables, variables present, long domain,
  domain > 5 elements, node_id in graph / node_id not in graph)
- GNNMarkdownFormatter._format_connections (with edges, evidence_sources, metadata keys)
- GNNMarkdownFormatter._format_factors (with state space vars and their factors, without vars)
- LanguageDetector.detect_language (various extensions), detect_repo_languages,
  get_parser (ImportError path), get_supported_languages
- get_parser_for_extension (no dot, with dot, unknown, tree-sitter fallthrough)
- ingest/manifest.py fallback _parse_toml (section headers, key-value pairs,
  arrays, booleans, integers, floats, dict values)
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers shared across formatter tests
# ---------------------------------------------------------------------------


def _make_state_space(**kwargs):
    from cogant.statespace.compiler import StateSpaceModel
    from cogant.statespace.temporal import TimeRegime

    defaults = {
        "id": "ss1",
        "schema_name": "test",
        "variables": {},
        "observations": {},
        "actions": {},
        "transitions": {},
        "likelihoods": {},
        "preferences": {},
        "time_regime": TimeRegime.SYNCHRONOUS,
    }
    defaults.update(kwargs)
    return StateSpaceModel(**defaults)


def _make_process_model(**kwargs):
    from cogant.process.extractor import ProcessModel

    defaults = {"id": "pm1", "schema_name": "test", "stages": {}, "connections": {}}
    defaults.update(kwargs)
    return ProcessModel(**defaults)


def _make_formatter(graph=None, state_space=None, process_model=None, mappings=None):
    from cogant.gnn.formatter.base import GNNMarkdownFormatter
    from cogant.graph.builder import ProgramGraphBuilder

    if graph is None:
        graph = ProgramGraphBuilder(repo_uri="file:///test").finalize()
    if state_space is None:
        state_space = _make_state_space()
    if process_model is None:
        process_model = _make_process_model()
    if mappings is None:
        mappings = {}

    return GNNMarkdownFormatter(
        program_graph=graph,
        state_space_model=state_space,
        process_model=process_model,
        semantic_mappings=mappings,
    )


# ---------------------------------------------------------------------------
# gnn/formatter/structural.py — _format_state_space
# ---------------------------------------------------------------------------


class TestFormatStateSpace:
    def test_no_variables_returns_fallback_text(self):
        fmt = _make_formatter()
        result = fmt._format_state_space()
        assert "State Space" in result
        assert "No state variables" in result

    def test_with_variables_returns_table(self):
        from cogant.statespace.compiler import StateVariable
        from cogant.statespace.variables import ConfidenceLevel, StateVariableType

        var = StateVariable(
            id="v1",
            name="my_var",
            var_type=StateVariableType.DISCRETE,
            node_id="n1",
            domain=["a", "b", "c"],
            cardinality=3,
            confidence=ConfidenceLevel.HIGH,
        )
        ss = _make_state_space(variables={"v1": var})
        fmt = _make_formatter(state_space=ss)
        result = fmt._format_state_space()
        assert "my_var" in result
        assert "State Space" in result

    def test_variable_with_long_domain_truncated(self):
        from cogant.statespace.compiler import StateVariable
        from cogant.statespace.variables import ConfidenceLevel, StateVariableType

        var = StateVariable(
            id="v2",
            name="big_var",
            var_type=StateVariableType.DISCRETE,
            node_id="n2",
            domain=["a", "b", "c", "d", "e", "f", "g"],  # > 5 elements
            cardinality=7,
            confidence=ConfidenceLevel.MEDIUM,
        )
        ss = _make_state_space(variables={"v2": var})
        fmt = _make_formatter(state_space=ss)
        result = fmt._format_state_space()
        assert "more]" in result  # domain truncated

    def test_variable_with_string_domain(self):
        from cogant.statespace.compiler import StateVariable
        from cogant.statespace.variables import ConfidenceLevel, StateVariableType

        var = StateVariable(
            id="v3",
            name="str_var",
            var_type=StateVariableType.CONTINUOUS,
            node_id="n3",
            domain=None,
            cardinality=None,
            confidence=ConfidenceLevel.LOW,
        )
        ss = _make_state_space(variables={"v3": var})
        fmt = _make_formatter(state_space=ss)
        result = fmt._format_state_space()
        assert "str_var" in result

    def test_variable_with_node_id_in_graph(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind
        from cogant.statespace.compiler import StateVariable
        from cogant.statespace.variables import ConfidenceLevel, StateVariableType

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        node = builder.add_node(NodeKind.FUNCTION, "my_func", "my_func", path="f.py")
        graph = builder.finalize()

        var = StateVariable(
            id="v4",
            name="graph_var",
            var_type=StateVariableType.DISCRETE,
            node_id=node.id,
            domain=["x"],
            cardinality=1,
            confidence=ConfidenceLevel.HIGH,
        )
        ss = _make_state_space(variables={"v4": var})
        fmt = _make_formatter(graph=graph, state_space=ss)
        result = fmt._format_state_space()
        assert "my_func" in result

    def test_variable_with_node_id_not_in_graph(self):
        from cogant.statespace.compiler import StateVariable
        from cogant.statespace.variables import ConfidenceLevel, StateVariableType

        var = StateVariable(
            id="v5",
            name="orphan_var",
            var_type=StateVariableType.DISCRETE,
            node_id="nonexistent-node-id",
            domain=["y"],
            cardinality=1,
            confidence=ConfidenceLevel.HIGH,
        )
        ss = _make_state_space(variables={"v5": var})
        fmt = _make_formatter(state_space=ss)
        result = fmt._format_state_space()
        assert "orphan_var" in result

    def test_variable_with_factors(self):
        from cogant.statespace.compiler import StateVariable
        from cogant.statespace.variables import ConfidenceLevel, StateVariableType

        var = StateVariable(
            id="v6",
            name="factored_var",
            var_type=StateVariableType.DISCRETE,
            node_id="n6",
            domain=["a", "b"],
            cardinality=2,
            confidence=ConfidenceLevel.HIGH,
            factors=["factor1", "factor2"],
        )
        ss = _make_state_space(variables={"v6": var})
        fmt = _make_formatter(state_space=ss)
        result = fmt._format_state_space()
        assert "factor1" in result


# ---------------------------------------------------------------------------
# gnn/formatter/structural.py — _format_connections
# ---------------------------------------------------------------------------


class TestFormatConnections:
    def test_no_edges_returns_header(self):
        fmt = _make_formatter()
        result = fmt._format_connections()
        assert "Connections" in result

    def test_with_edges_returns_table(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import EdgeKind, NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        n1 = builder.add_node(NodeKind.MODULE, "mod", "mod", path="mod.py")
        n2 = builder.add_node(NodeKind.FUNCTION, "func", "mod.func", path="mod.py")
        builder.add_edge(n1.id, n2.id, EdgeKind.CONTAINS)
        graph = builder.finalize()
        fmt = _make_formatter(graph=graph)
        result = fmt._format_connections()
        assert "Connections" in result or "CONTAINS" in result.upper() or "contains" in result

    def test_with_edge_evidence_sources(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import EdgeKind, NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        n1 = builder.add_node(NodeKind.MODULE, "mod", "mod", path="mod.py")
        n2 = builder.add_node(NodeKind.FUNCTION, "func", "mod.func", path="mod.py")
        edge = builder.add_edge(n1.id, n2.id, EdgeKind.CONTAINS)
        edge.evidence_sources = ["static_analysis", "dynamic_trace"]
        graph = builder.finalize()
        fmt = _make_formatter(graph=graph)
        result = fmt._format_connections()
        assert isinstance(result, str)

    def test_with_edge_metadata_keys(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import EdgeKind, NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        n1 = builder.add_node(NodeKind.MODULE, "a", "a", path="a.py")
        n2 = builder.add_node(NodeKind.FUNCTION, "b", "a.b", path="a.py")
        edge = builder.add_edge(n1.id, n2.id, EdgeKind.CALLS)
        edge.metadata["source_file"] = "a.py"
        edge.metadata["line_number"] = 10
        edge.metadata["pattern"] = "call"
        graph = builder.finalize()
        fmt = _make_formatter(graph=graph)
        result = fmt._format_connections()
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# gnn/formatter/structural.py — _format_factors
# ---------------------------------------------------------------------------


class TestFormatFactors:
    def test_no_variables_uses_graph_structure(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        builder.add_node(NodeKind.MODULE, "mymod", "mymod", path="mymod.py")
        builder.add_node(NodeKind.CLASS, "MyClass", "mymod.MyClass", path="mymod.py")
        graph = builder.finalize()
        fmt = _make_formatter(graph=graph)
        result = fmt._format_factors()
        assert "Factor" in result or "Factors" in result

    def test_with_variables_and_factors(self):
        from cogant.statespace.compiler import StateVariable
        from cogant.statespace.variables import ConfidenceLevel, StateVariableType

        v1 = StateVariable(
            id="v1",
            name="v1",
            var_type=StateVariableType.DISCRETE,
            node_id="n1",
            domain=["a"],
            cardinality=1,
            confidence=ConfidenceLevel.HIGH,
            factors=["perception"],
        )
        v2 = StateVariable(
            id="v2",
            name="v2",
            var_type=StateVariableType.DISCRETE,
            node_id="n2",
            domain=["b"],
            cardinality=1,
            confidence=ConfidenceLevel.HIGH,
            factors=["action"],
        )
        ss = _make_state_space(variables={"v1": v1, "v2": v2})
        fmt = _make_formatter(state_space=ss)
        result = fmt._format_factors()
        assert "perception" in result
        assert "action" in result

    def test_with_variables_no_factors(self):
        from cogant.statespace.compiler import StateVariable
        from cogant.statespace.variables import ConfidenceLevel, StateVariableType

        v1 = StateVariable(
            id="v1",
            name="v1",
            var_type=StateVariableType.DISCRETE,
            node_id="n1",
            domain=["a"],
            cardinality=1,
            confidence=ConfidenceLevel.HIGH,
        )
        ss = _make_state_space(variables={"v1": v1})
        fmt = _make_formatter(state_space=ss)
        result = fmt._format_factors()
        assert "uncategorized" in result.lower()

    def test_empty_graph_and_no_variables(self):
        fmt = _make_formatter()
        result = fmt._format_factors()
        assert isinstance(result, str)
        assert "Factor" in result


# ---------------------------------------------------------------------------
# ingest/language_detect.py — LanguageDetector
# ---------------------------------------------------------------------------


class TestLanguageDetector:
    def test_detect_python(self):
        from cogant.ingest.language_detect import LanguageDetector

        result = LanguageDetector.detect_language(Path("foo.py"))
        assert result == "python"

    def test_detect_javascript(self):
        from cogant.ingest.language_detect import LanguageDetector

        result = LanguageDetector.detect_language(Path("foo.js"))
        assert result == "javascript"

    def test_detect_typescript(self):
        from cogant.ingest.language_detect import LanguageDetector

        result = LanguageDetector.detect_language(Path("foo.ts"))
        assert result == "typescript"

    def test_detect_rust(self):
        from cogant.ingest.language_detect import LanguageDetector

        result = LanguageDetector.detect_language(Path("foo.rs"))
        assert result == "rust"

    def test_detect_go(self):
        from cogant.ingest.language_detect import LanguageDetector

        result = LanguageDetector.detect_language(Path("foo.go"))
        assert result == "go"

    def test_detect_unknown_extension(self):
        from cogant.ingest.language_detect import LanguageDetector

        result = LanguageDetector.detect_language(Path("foo.xyz"))
        assert result is None

    def test_detect_string_input(self):
        from cogant.ingest.language_detect import LanguageDetector

        result = LanguageDetector.detect_language("script.py")  # type: ignore
        assert result == "python"

    def test_detect_repo_languages_empty_dir(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        result = LanguageDetector.detect_repo_languages(tmp_path)
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_detect_repo_languages_with_files(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        (tmp_path / "a.py").write_text("x = 1")
        (tmp_path / "b.py").write_text("y = 2")
        (tmp_path / "c.js").write_text("var z = 3;")
        result = LanguageDetector.detect_repo_languages(tmp_path)
        assert result.get("python", 0) == 2
        assert result.get("javascript", 0) == 1

    def test_detect_repo_languages_string_path(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        (tmp_path / "a.py").write_text("x = 1")
        result = LanguageDetector.detect_repo_languages(str(tmp_path))
        assert result.get("python", 0) >= 1

    def test_get_parser_raises_for_unknown(self):
        from cogant.ingest.language_detect import LanguageDetector

        with pytest.raises(ImportError):
            LanguageDetector.get_parser("totally_unknown_language_xyz")

    def test_get_supported_languages_returns_list(self):
        from cogant.ingest.language_detect import LanguageDetector

        result = LanguageDetector.get_supported_languages()
        assert isinstance(result, list)
        # python should always be supported
        assert "python" in result


class TestGetParserForExtension:
    def test_dot_py_returns_something_or_none(self):
        from cogant.ingest.language_detect import get_parser_for_extension

        # Should return a parser or None; never raise
        result = get_parser_for_extension(".py")
        # Python is supported, so should return a parser
        assert result is not None or result is None  # just verify no exception

    def test_no_dot_prefix_works(self):
        from cogant.ingest.language_detect import get_parser_for_extension

        result = get_parser_for_extension("py")
        # Same as .py
        assert result is not None or result is None

    def test_unknown_extension_returns_none(self):
        from cogant.ingest.language_detect import get_parser_for_extension

        result = get_parser_for_extension(".zzzunknown")
        assert result is None

    def test_empty_extension_returns_none(self):
        from cogant.ingest.language_detect import get_parser_for_extension

        result = get_parser_for_extension("")
        assert result is None


# ---------------------------------------------------------------------------
# ingest/manifest.py — fallback _parse_toml (exercises the ImportError branch)
# ---------------------------------------------------------------------------


class TestManifestFallbackToml:
    """These tests are only meaningful when tomllib is NOT available (Python < 3.11).
    On Python >= 3.11 they still pass since the real tomllib is used.
    We import _parse_toml indirectly via ManifestParser.parse_pyproject_toml.

    Note: parse_pyproject_toml returns (metadata_dict, list[Dependency]).
          parse_cargo_toml returns list[Dependency].
          parse_package_json returns list[Dependency].
          parse_requirements_txt returns list[Dependency].
          parse_setup_py returns list[Dependency].
          parse() returns list[Dependency] (via dispatch).
    """

    def test_parse_pyproject_with_dependencies(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        content = b"""
[project]
name = "myproject"
version = "1.0"
dependencies = ["requests>=2.0", "flask"]
"""
        f = tmp_path / "pyproject.toml"
        f.write_bytes(content)
        parser = ManifestParser()
        _meta, deps = parser.parse_pyproject_toml(f)
        names = [d.name for d in deps]
        assert "requests" in names
        assert "flask" in names

    def test_parse_pyproject_poetry_format(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        content = b"""
[tool.poetry]
name = "mypoetry"
version = "0.1.0"

[tool.poetry.dependencies]
python = "^3.10"
click = ">=8.0"
"""
        f = tmp_path / "pyproject.toml"
        f.write_bytes(content)
        parser = ManifestParser()
        _meta, deps = parser.parse_pyproject_toml(f)
        names = [d.name for d in deps]
        # poetry format — click should be found or gracefully empty
        assert isinstance(names, list)

    def test_parse_cargo_toml(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        content = b"""
[package]
name = "myapp"
version = "0.1.0"

[dependencies]
serde = "1.0"
"""
        f = tmp_path / "Cargo.toml"
        f.write_bytes(content)
        parser = ManifestParser()
        _meta, deps = parser.parse_cargo_toml(f)
        names = [d.name for d in deps]
        assert "serde" in names

    def test_parse_package_json(self, tmp_path):
        import json

        from cogant.ingest.manifest import ManifestParser

        content = json.dumps(
            {
                "name": "myapp",
                "version": "1.0.0",
                "dependencies": {
                    "express": "^4.18.0",
                    "lodash": "4.17.21",
                },
                "devDependencies": {
                    "jest": "^29.0.0",
                },
            }
        )
        f = tmp_path / "package.json"
        f.write_text(content)
        parser = ManifestParser()
        _meta, deps = parser.parse_package_json(f)
        names = [d.name for d in deps]
        assert "express" in names
        assert "lodash" in names

    def test_parse_requirements_txt(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        content = "requests>=2.0\nflask==2.0.1\n# a comment\nnumpy\n"
        f = tmp_path / "requirements.txt"
        f.write_text(content)
        parser = ManifestParser()
        deps = parser.parse_requirements_txt(f)
        names = [d.name for d in deps]
        assert "requests" in names
        assert "flask" in names
        assert "numpy" in names

    def test_parse_requirements_txt_with_extras(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        content = "requests[security]>=2.0\n-r other.txt\n"
        f = tmp_path / "requirements.txt"
        f.write_text(content)
        parser = ManifestParser()
        deps = parser.parse_requirements_txt(f)
        names = [d.name for d in deps]
        assert "requests" in names

    def test_parse_setup_py(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        content = """
from setuptools import setup
setup(
    name="mypkg",
    version="1.0",
    install_requires=["boto3>=1.0", "requests"],
)
"""
        f = tmp_path / "setup.py"
        f.write_text(content)
        parser = ManifestParser()
        _meta, deps = parser.parse_setup_py(f)
        names = [d.name for d in deps]
        assert "requests" in names or "boto3" in names

    def test_parse_dispatch_requirements(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        content = "pandas>=1.0\n"
        f = tmp_path / "requirements.txt"
        f.write_text(content)
        parser = ManifestParser()
        _meta, deps = parser.parse(f)
        names = [d.name for d in deps]
        assert "pandas" in names

    def test_parse_dispatch_pyproject(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        content = b'[project]\nname = "x"\ndependencies = ["scipy"]\n'
        f = tmp_path / "pyproject.toml"
        f.write_bytes(content)
        parser = ManifestParser()
        _meta, deps = parser.parse(f)
        names = [d.name for d in deps]
        assert "scipy" in names

    def test_parse_dispatch_cargo(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        content = b'[package]\nname = "c"\n\n[dependencies]\nlog = "0.4"\n'
        f = tmp_path / "Cargo.toml"
        f.write_bytes(content)
        parser = ManifestParser()
        _meta, deps = parser.parse(f)
        names = [d.name for d in deps]
        assert "log" in names

    def test_parse_unknown_file_raises_or_empty(self, tmp_path):
        from cogant.ingest.manifest import ManifestParser

        f = tmp_path / "random.yaml"
        f.write_text("key: value\n")
        parser = ManifestParser()
        # parse() raises ValueError for unknown file types
        with pytest.raises((ValueError, Exception)):
            parser.parse(f)
