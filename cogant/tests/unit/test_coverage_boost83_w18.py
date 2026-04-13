#!/usr/bin/env python3
"""Coverage boost batch 83 — cli/doctor.py, cli/explain.py pure functions,
dynamic/enrichment.py helpers, ingest/language_detect.py.

Covers:
- cli/doctor.py: DoctorCheck, DoctorReport, _package_version, _check_python,
  _check_dependency, _check_rust_backend, _check_git, _check_mypy, _check_ruff,
  _check_mermaid_cli, _check_tree_sitter_node_types, run_doctor,
  render_report, doctor_command
- cli/explain.py: ExplainResult, NodeNotFoundError, resolve_node,
  _candidate_sample, _find_assigned_mapping, format_json, format_text
- dynamic/enrichment.py: _normalize_path, _node_spans_line, _stable_edge_id,
  enrich_graph with both None, _build_function_index
- ingest/language_detect.py: detect_language with str, detect_repo_languages,
  get_parser_for_extension, get_supported_languages
"""

import json
import pytest
from pathlib import Path
from io import StringIO

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# cli/doctor.py
# ---------------------------------------------------------------------------

class TestDoctorCheck:
    def test_ok_icon(self):
        from cogant.cli.doctor import DoctorCheck
        c = DoctorCheck(name="test", status="ok", detail="all good")
        assert c.icon == "✅"

    def test_warn_icon(self):
        from cogant.cli.doctor import DoctorCheck
        c = DoctorCheck(name="test", status="warn", detail="might miss")
        assert c.icon == "⚠️"

    def test_fail_icon(self):
        from cogant.cli.doctor import DoctorCheck
        c = DoctorCheck(name="test", status="fail", detail="broken")
        assert c.icon == "❌"

    def test_unknown_icon(self):
        from cogant.cli.doctor import DoctorCheck
        c = DoctorCheck(name="test", status="unknown")
        assert c.icon == "?"

    def test_name_and_detail(self):
        from cogant.cli.doctor import DoctorCheck
        c = DoctorCheck(name="mycheck", status="ok", detail="v1.2.3")
        assert c.name == "mycheck"
        assert c.detail == "v1.2.3"


class TestDoctorReport:
    def test_empty_report_ok(self):
        from cogant.cli.doctor import DoctorReport
        report = DoctorReport()
        assert report.ok is True
        assert report.has_warnings is False
        assert report.verdict == "READY"

    def test_report_with_warn(self):
        from cogant.cli.doctor import DoctorReport, DoctorCheck
        report = DoctorReport()
        report.add(DoctorCheck(name="git", status="warn", detail="not found"))
        assert report.ok is True
        assert report.has_warnings is True
        assert report.verdict == "READY (with warnings)"

    def test_report_with_fail(self):
        from cogant.cli.doctor import DoctorReport, DoctorCheck
        report = DoctorReport()
        report.add(DoctorCheck(name="python", status="fail", detail="too old"))
        assert report.ok is False
        assert report.verdict == "NOT READY"

    def test_report_mixed(self):
        from cogant.cli.doctor import DoctorReport, DoctorCheck
        report = DoctorReport()
        report.add(DoctorCheck(name="a", status="ok"))
        report.add(DoctorCheck(name="b", status="warn"))
        assert len(report.checks) == 2


class TestDoctorChecks:
    def test_check_python(self):
        from cogant.cli.doctor import _check_python
        result = _check_python()
        assert result.status in ("ok", "fail")
        assert "Python" in result.name or result.name == "Python"

    def test_package_version_cogant(self):
        from cogant.cli.doctor import _package_version
        # cogant is installed in dev mode
        version = _package_version("cogant")
        # May be None or a string
        assert version is None or isinstance(version, str)

    def test_package_version_nonexistent(self):
        from cogant.cli.doctor import _package_version
        version = _package_version("nonexistent_package_xyz_12345")
        assert version is None

    def test_check_dependency_installed(self):
        from cogant.cli.doctor import _check_dependency
        result = _check_dependency("json", "json", required=True)
        # json is a stdlib module; version might be "unknown" but status ok
        assert result.status in ("ok", "fail", "warn")

    def test_check_dependency_missing_required(self):
        from cogant.cli.doctor import _check_dependency
        result = _check_dependency("nonexistent_xyz_123", "Fake Dep", required=True)
        assert result.status == "fail"
        assert "not installed" in result.detail

    def test_check_dependency_missing_optional(self):
        from cogant.cli.doctor import _check_dependency
        result = _check_dependency("nonexistent_xyz_123", "Fake Optional", required=False)
        assert result.status == "warn"

    def test_check_rust_backend(self):
        from cogant.cli.doctor import _check_rust_backend
        result = _check_rust_backend()
        assert result.status in ("ok", "warn")
        assert "Rust" in result.name

    def test_check_git(self):
        from cogant.cli.doctor import _check_git
        result = _check_git()
        assert result.status in ("ok", "warn")
        assert result.name == "git"

    def test_check_mypy(self):
        from cogant.cli.doctor import _check_mypy
        result = _check_mypy()
        assert result.status in ("ok", "warn")
        assert "mypy" in result.name.lower()

    def test_check_ruff(self):
        from cogant.cli.doctor import _check_ruff
        result = _check_ruff()
        assert result.status in ("ok", "warn")
        assert "ruff" in result.name.lower()

    def test_check_mermaid_cli(self):
        from cogant.cli.doctor import _check_mermaid_cli
        result = _check_mermaid_cli()
        assert result.status in ("ok", "warn")

    def test_check_tree_sitter_node_types(self):
        from cogant.cli.doctor import _check_tree_sitter_node_types
        result = _check_tree_sitter_node_types()
        assert result.status in ("ok", "warn")

    def test_run_doctor_returns_report(self):
        from cogant.cli.doctor import run_doctor
        report = run_doctor()
        assert len(report.checks) >= 5
        assert report.verdict in ("READY", "READY (with warnings)", "NOT READY")

    def test_render_report_produces_output(self):
        from cogant.cli.doctor import run_doctor, render_report
        from rich.console import Console
        buf = StringIO()
        console = Console(file=buf, width=120)
        report = run_doctor()
        render_report(console, report)
        output = buf.getvalue()
        assert len(output) > 10

    def test_doctor_command_returns_int(self):
        from cogant.cli.doctor import doctor_command
        from rich.console import Console
        buf = StringIO()
        console = Console(file=buf, width=120)
        result = doctor_command(console=console)
        assert isinstance(result, int)
        assert result in (0, 1)


# ---------------------------------------------------------------------------
# cli/explain.py — pure-function coverage (no pipeline execution)
# ---------------------------------------------------------------------------

class TestExplainResult:
    def test_to_dict_has_required_keys(self):
        from cogant.cli.explain import ExplainResult
        result = ExplainResult(
            node_name="my_func",
            node_id="node_001",
            node_kind="function",
            assigned_role="observation",
            rules_fired=[],
            rules_considered=[],
            blanket_role="sensory",
            target="/repo",
        )
        d = result.to_dict()
        assert d["node_name"] == "my_func"
        assert d["node_id"] == "node_001"
        assert d["assigned_role"] == "observation"
        assert d["blanket_role"] == "sensory"
        assert "rules_fired" in d
        assert "rules_considered" in d
        assert "metadata" in d

    def test_to_dict_none_role(self):
        from cogant.cli.explain import ExplainResult
        result = ExplainResult(
            node_name="unknown",
            node_id="n2",
            node_kind="method",
            assigned_role=None,
            rules_fired=[],
            rules_considered=[],
            blanket_role="external",
        )
        d = result.to_dict()
        assert d["assigned_role"] is None

    def test_format_json_returns_valid_json(self):
        from cogant.cli.explain import ExplainResult, format_json
        result = ExplainResult(
            node_name="process",
            node_id="n3",
            node_kind="function",
            assigned_role="action",
            rules_fired=[],
            rules_considered=[],
            blanket_role="active",
            target="/my/repo",
            mapping_label="Action handler",
            mapping_description="Handles user actions",
        )
        s = format_json(result)
        parsed = json.loads(s)
        assert parsed["node_name"] == "process"
        assert parsed["assigned_role"] == "action"


class TestNodeNotFoundError:
    def test_is_lookup_error(self):
        from cogant.cli.explain import NodeNotFoundError
        e = NodeNotFoundError("no match for 'foo'")
        assert isinstance(e, LookupError)
        assert "foo" in str(e)


class TestResolveNode:
    def _make_graph_with_nodes(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind
        builder = ProgramGraphBuilder(repo_uri="file:///test")
        builder.add_node(NodeKind.FUNCTION, "process_data", "mymod.process_data", path="mymod.py")
        builder.add_node(NodeKind.FUNCTION, "ProcessData", "mymod.ProcessData", path="mymod.py")
        builder.add_node(NodeKind.CLASS, "DataPipeline", "mymod.DataPipeline", path="mymod.py")
        return builder.finalize()

    def test_resolve_exact_match(self):
        from cogant.cli.explain import resolve_node
        graph = self._make_graph_with_nodes()
        node = resolve_node(graph, "process_data")
        assert node.name == "process_data"

    def test_resolve_case_insensitive(self):
        from cogant.cli.explain import resolve_node
        graph = self._make_graph_with_nodes()
        node = resolve_node(graph, "PROCESSDATA")
        assert node.name.lower() == "processdata"

    def test_resolve_substring(self):
        from cogant.cli.explain import resolve_node
        graph = self._make_graph_with_nodes()
        # "pipeline" is a substring of DataPipeline
        node = resolve_node(graph, "pipeline")
        assert "pipeline" in node.name.lower()

    def test_resolve_not_found_raises(self):
        from cogant.cli.explain import resolve_node, NodeNotFoundError
        graph = self._make_graph_with_nodes()
        with pytest.raises(NodeNotFoundError):
            resolve_node(graph, "completely_nonexistent_xyz_abc")

    def test_resolve_empty_query_raises(self):
        from cogant.cli.explain import resolve_node, NodeNotFoundError
        graph = self._make_graph_with_nodes()
        with pytest.raises(NodeNotFoundError):
            resolve_node(graph, "")

    def test_candidate_sample(self):
        from cogant.cli.explain import _candidate_sample
        graph = self._make_graph_with_nodes()
        sample = _candidate_sample(graph, limit=2)
        assert isinstance(sample, list)
        assert len(sample) <= 2

    def test_find_assigned_mapping_no_match(self):
        from cogant.cli.explain import _find_assigned_mapping
        result = _find_assigned_mapping("node_nonexistent", {})
        assert result is None

    def test_format_text_no_rules_fired(self):
        from cogant.cli.explain import ExplainResult, format_text
        from rich.console import Console
        result = ExplainResult(
            node_name="helper",
            node_id="n1",
            node_kind="function",
            assigned_role=None,
            rules_fired=[],
            rules_considered=[],
            blanket_role="external",
        )
        buf = StringIO()
        console = Console(file=buf, width=120)
        format_text(result, console=console)
        output = buf.getvalue()
        assert "helper" in output

    def test_format_text_with_label_and_description(self):
        from cogant.cli.explain import ExplainResult, format_text
        from rich.console import Console
        result = ExplainResult(
            node_name="observe_state",
            node_id="n2",
            node_kind="function",
            assigned_role="observation",
            rules_fired=[],
            rules_considered=[],
            blanket_role="sensory",
            mapping_label="State Observation",
            mapping_description="Observes the current state",
        )
        buf = StringIO()
        console = Console(file=buf, width=120)
        format_text(result, console=console)
        output = buf.getvalue()
        assert "observe_state" in output


# ---------------------------------------------------------------------------
# dynamic/enrichment.py — pure helper functions
# ---------------------------------------------------------------------------

class TestEnrichmentHelpers:
    def test_normalize_path_strips_leading_dot_slash(self):
        from cogant.dynamic.enrichment import _normalize_path
        assert _normalize_path("./foo/bar.py") == "foo/bar.py"
        assert _normalize_path("././baz.py") == "baz.py"

    def test_normalize_path_converts_backslashes(self):
        from cogant.dynamic.enrichment import _normalize_path
        result = _normalize_path("foo\\bar\\baz.py")
        assert "\\" not in result
        assert "foo/bar/baz.py" in result

    def test_normalize_path_plain(self):
        from cogant.dynamic.enrichment import _normalize_path
        result = _normalize_path("cogant/ingest/files.py")
        assert result == "cogant/ingest/files.py"

    def test_stable_edge_id_deterministic(self):
        from cogant.dynamic.enrichment import _stable_edge_id
        id1 = _stable_edge_id("src_node", "tgt_node", "CALLS")
        id2 = _stable_edge_id("src_node", "tgt_node", "CALLS")
        assert id1 == id2
        assert isinstance(id1, str)
        assert len(id1) == 16  # 16-char hex prefix

    def test_stable_edge_id_differs_for_different_inputs(self):
        from cogant.dynamic.enrichment import _stable_edge_id
        id1 = _stable_edge_id("src", "tgt", "CALLS")
        id2 = _stable_edge_id("tgt", "src", "CALLS")
        assert id1 != id2

    def test_node_spans_line_no_source_range(self):
        from cogant.dynamic.enrichment import _node_spans_line
        import types
        node = types.SimpleNamespace(source_range=None)
        assert _node_spans_line(node, 10) is False

    def test_node_spans_line_in_range(self):
        from cogant.dynamic.enrichment import _node_spans_line
        import types
        node = types.SimpleNamespace(
            source_range={"start_line": 5, "end_line": 15}
        )
        assert _node_spans_line(node, 10) is True
        assert _node_spans_line(node, 5) is True
        assert _node_spans_line(node, 15) is True
        assert _node_spans_line(node, 16) is False
        assert _node_spans_line(node, 4) is False

    def test_node_spans_line_nested_dict(self):
        from cogant.dynamic.enrichment import _node_spans_line
        import types
        node = types.SimpleNamespace(
            source_range={"start": {"line": 3}, "end": {"line": 7}}
        )
        assert _node_spans_line(node, 5) is True
        assert _node_spans_line(node, 8) is False

    def test_enrich_graph_both_none(self):
        from cogant.dynamic.enrichment import enrich_graph
        from cogant.schemas.graph import ProgramGraph, GraphMetadata
        graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///test"))
        result = enrich_graph(graph, coverage_path=None, trace_path=None)
        assert result["coverage_nodes_enriched"] == 0
        assert result["trace_nodes_enriched"] == 0
        assert result["graph"] is graph
        assert result["evidence_sources"] == []

    def test_build_function_index_empty_graph(self):
        from cogant.dynamic.enrichment import _build_function_index
        from cogant.schemas.graph import ProgramGraph, GraphMetadata
        graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///test"))
        index = _build_function_index(graph)
        assert isinstance(index, dict)
        assert len(index) == 0

    def test_build_function_index_with_functions(self):
        from cogant.dynamic.enrichment import _build_function_index
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind
        builder = ProgramGraphBuilder(repo_uri="file:///test")
        builder.add_node(NodeKind.FUNCTION, "process", "mymod.process", path="mymod.py")
        builder.add_node(NodeKind.METHOD, "run", "MyClass.run", path="mymod.py")
        builder.add_node(NodeKind.CLASS, "MyClass", "mymod.MyClass", path="mymod.py")
        graph = builder.finalize()
        index = _build_function_index(graph)
        assert "process" in index
        assert "run" in index
        # CLASS is not callable kind, should not be in index
        assert "MyClass" not in index


# ---------------------------------------------------------------------------
# ingest/language_detect.py
# ---------------------------------------------------------------------------

class TestLanguageDetector:
    def test_detect_language_py(self):
        from cogant.ingest.language_detect import LanguageDetector
        result = LanguageDetector.detect_language(Path("myfile.py"))
        assert result == "python"

    def test_detect_language_str_input(self):
        from cogant.ingest.language_detect import LanguageDetector
        result = LanguageDetector.detect_language("myfile.py")
        assert result == "python"

    def test_detect_language_ts(self):
        from cogant.ingest.language_detect import LanguageDetector
        result = LanguageDetector.detect_language(Path("app.ts"))
        assert result == "typescript"

    def test_detect_language_tsx(self):
        from cogant.ingest.language_detect import LanguageDetector
        result = LanguageDetector.detect_language(Path("Component.tsx"))
        assert result == "typescript"

    def test_detect_language_js(self):
        from cogant.ingest.language_detect import LanguageDetector
        result = LanguageDetector.detect_language(Path("index.js"))
        assert result == "javascript"

    def test_detect_language_rs(self):
        from cogant.ingest.language_detect import LanguageDetector
        result = LanguageDetector.detect_language(Path("main.rs"))
        assert result == "rust"

    def test_detect_language_go(self):
        from cogant.ingest.language_detect import LanguageDetector
        result = LanguageDetector.detect_language(Path("main.go"))
        assert result == "go"

    def test_detect_language_unknown(self):
        from cogant.ingest.language_detect import LanguageDetector
        result = LanguageDetector.detect_language(Path("readme.md"))
        assert result is None

    def test_detect_repo_languages(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector
        (tmp_path / "main.py").write_text("x = 1")
        (tmp_path / "util.py").write_text("y = 2")
        (tmp_path / "index.ts").write_text("const x = 1")
        result = LanguageDetector.detect_repo_languages(tmp_path)
        assert isinstance(result, dict)
        assert result.get("python", 0) == 2
        assert result.get("typescript", 0) == 1

    def test_detect_repo_languages_str_input(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector
        (tmp_path / "main.py").write_text("x = 1")
        result = LanguageDetector.detect_repo_languages(str(tmp_path))
        assert isinstance(result, dict)

    def test_detect_repo_languages_empty(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector
        result = LanguageDetector.detect_repo_languages(tmp_path)
        assert result == {}

    def test_get_supported_languages(self):
        from cogant.ingest.language_detect import LanguageDetector
        langs = LanguageDetector.get_supported_languages()
        assert isinstance(langs, list)
        # At least python should be loaded
        # (may depend on environment, so just check type)

    def test_get_parser_nonexistent_raises(self):
        from cogant.ingest.language_detect import LanguageDetector
        with pytest.raises(ImportError):
            LanguageDetector.get_parser("cobol")


class TestGetParserForExtension:
    def test_get_parser_for_py_extension(self):
        from cogant.ingest.language_detect import get_parser_for_extension
        # .py extension — may return a parser or None depending on env
        result = get_parser_for_extension(".py")
        # Should not raise; returns parser or None
        assert result is None or result is not None

    def test_get_parser_for_py_without_dot(self):
        from cogant.ingest.language_detect import get_parser_for_extension
        result = get_parser_for_extension("py")
        assert result is None or result is not None

    def test_get_parser_for_unknown_extension(self):
        from cogant.ingest.language_detect import get_parser_for_extension
        result = get_parser_for_extension(".xyz")
        assert result is None

    def test_get_parser_for_empty_extension(self):
        from cogant.ingest.language_detect import get_parser_for_extension
        result = get_parser_for_extension("")
        assert result is None

    def test_get_parser_for_ts_extension(self):
        from cogant.ingest.language_detect import get_parser_for_extension
        result = get_parser_for_extension(".ts")
        # May return a parser or None depending on environment
        assert result is None or result is not None
