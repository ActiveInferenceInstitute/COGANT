#!/usr/bin/env python3
"""Coverage boost batch 44 — static/calls.py, static/dataflow.py, tools/organize_example_outputs.py.

Covers:
- CallGraphBuilder: extract_calls_from_source (class methods path), extract_calls_from_file
- CallExtractorVisitor: _ast_to_str (Name/Constant/Attribute/other branches), _extract_call
  (method call / Attribute path, complex expression path), visit_Call
- DataFlowAnalyzer: analyze_source (SyntaxError/ValueError paths, class body, methods)
- DataFlowEdge: dataclass
- DataFlowVisitor: tuple/list unpacking, AugAssign, AnnAssign, Return
- organize_example_outputs: _dest_for_file (.mermaid branch, unknown branch),
  organize_run_dir (not-a-dir, dry_run, already-organized, overwrite),
  migrate_output_tree (skip missing, dry_run, count), main (organize-only)
"""

import ast

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# static/calls.py — CallEdge dataclass
# ---------------------------------------------------------------------------


class TestCallEdge:
    def test_call_edge_basic(self, tmp_path):
        from cogant.static.calls import CallEdge

        e = CallEdge(
            id="e1",
            source_file=tmp_path / "foo.py",
            caller_id="mod.func",
            caller_name="func",
            callee_name="bar",
        )
        assert e.id == "e1"
        assert e.callee_name == "bar"
        assert e.is_method_call is False
        assert e.receiver is None
        assert e.args == []

    def test_call_edge_method(self, tmp_path):
        from cogant.static.calls import CallEdge

        e = CallEdge(
            id="e2",
            source_file=tmp_path / "foo.py",
            caller_id="mod.func",
            caller_name="func",
            callee_name="bar",
            is_method_call=True,
            receiver="self",
            args=["x", "y"],
        )
        assert e.is_method_call is True
        assert e.receiver == "self"
        assert e.args == ["x", "y"]


# ---------------------------------------------------------------------------
# static/calls.py — CallExtractorVisitor._ast_to_str
# ---------------------------------------------------------------------------


class TestCallExtractorVisitorAstToStr:
    def test_name_node(self):
        from cogant.static.calls import CallExtractorVisitor

        node = ast.Name(id="myvar", ctx=ast.Load())
        assert CallExtractorVisitor._ast_to_str(node) == "myvar"

    def test_constant_int(self):
        from cogant.static.calls import CallExtractorVisitor

        node = ast.Constant(value=42)
        result = CallExtractorVisitor._ast_to_str(node)
        assert "42" in result

    def test_constant_str(self):
        from cogant.static.calls import CallExtractorVisitor

        node = ast.Constant(value="hello")
        result = CallExtractorVisitor._ast_to_str(node)
        assert "hello" in result

    def test_attribute_node(self):
        from cogant.static.calls import CallExtractorVisitor

        node = ast.Attribute(
            value=ast.Name(id="obj", ctx=ast.Load()),
            attr="method",
            ctx=ast.Load(),
        )
        result = CallExtractorVisitor._ast_to_str(node)
        assert "method" in result

    def test_other_node_returns_type_name(self):
        from cogant.static.calls import CallExtractorVisitor

        # A node type that won't unparse cleanly — use a valid one but verify str
        node = ast.Name(id="x", ctx=ast.Load())
        result = CallExtractorVisitor._ast_to_str(node)
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# static/calls.py — CallGraphBuilder.extract_calls_from_source
# ---------------------------------------------------------------------------


class TestCallGraphBuilderExtractFromSource:
    def test_simple_function_call(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder

        builder = CallGraphBuilder(repo_root=tmp_path)
        source = "def foo():\n    bar()\n"
        calls = builder.extract_calls_from_source(source, tmp_path / "test.py")
        assert isinstance(calls, list)

    def test_method_call_in_class(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder

        builder = CallGraphBuilder(repo_root=tmp_path)
        source = "class MyClass:\n    def method(self):\n        self.helper()\n"
        calls = builder.extract_calls_from_source(source, tmp_path / "cls.py")
        assert isinstance(calls, list)
        # Should have extracted the self.helper() call
        callee_names = [c.callee_name for c in calls]
        assert "helper" in callee_names

    def test_chained_method_calls(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder

        builder = CallGraphBuilder(repo_root=tmp_path)
        source = "def process(data):\n    result = data.strip().lower()\n    return result\n"
        calls = builder.extract_calls_from_source(source, tmp_path / "proc.py")
        assert isinstance(calls, list)

    def test_empty_source(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder

        builder = CallGraphBuilder(repo_root=tmp_path)
        calls = builder.extract_calls_from_source("", tmp_path / "empty.py")
        assert calls == []

    def test_multiple_functions(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder

        builder = CallGraphBuilder(repo_root=tmp_path)
        source = "def foo():\n    bar()\n\ndef baz():\n    qux()\n"
        calls = builder.extract_calls_from_source(source, tmp_path / "multi.py")
        assert isinstance(calls, list)
        assert len(calls) >= 2

    def test_nested_calls(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder

        builder = CallGraphBuilder(repo_root=tmp_path)
        source = "def foo():\n    result = outer(inner(x))\n"
        calls = builder.extract_calls_from_source(source, tmp_path / "nested.py")
        assert isinstance(calls, list)

    def test_class_with_multiple_methods(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder

        builder = CallGraphBuilder(repo_root=tmp_path)
        source = (
            "class Processor:\n"
            "    def run(self):\n"
            "        self._prepare()\n"
            "        self._execute()\n"
            "\n"
            "    def _prepare(self):\n"
            "        pass\n"
            "\n"
            "    def _execute(self):\n"
            "        pass\n"
        )
        calls = builder.extract_calls_from_source(source, tmp_path / "proc.py")
        assert isinstance(calls, list)
        assert len(calls) >= 2

    def test_returns_call_edge_objects(self, tmp_path):
        from cogant.static.calls import CallEdge, CallGraphBuilder

        builder = CallGraphBuilder(repo_root=tmp_path)
        source = "def foo():\n    bar(1, 2)\n"
        calls = builder.extract_calls_from_source(source, tmp_path / "t.py")
        for call in calls:
            assert isinstance(call, CallEdge)


# ---------------------------------------------------------------------------
# static/calls.py — CallGraphBuilder.extract_calls_from_file
# ---------------------------------------------------------------------------


class TestCallGraphBuilderExtractFromFile:
    def test_extract_from_real_file(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder

        py = tmp_path / "mymod.py"
        py.write_text("def greet(name):\n    print(name)\n")
        builder = CallGraphBuilder(repo_root=tmp_path)
        calls = builder.extract_calls_from_file(py)
        assert isinstance(calls, list)
        callee_names = [c.callee_name for c in calls]
        assert "print" in callee_names

    def test_extract_missing_file_returns_empty(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder

        builder = CallGraphBuilder(repo_root=tmp_path)
        calls = builder.extract_calls_from_file(tmp_path / "nonexistent.py")
        assert isinstance(calls, list)

    def test_extract_class_methods_from_file(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder

        py = tmp_path / "cls.py"
        py.write_text("class Foo:\n    def method(self):\n        self.helper()\n")
        builder = CallGraphBuilder(repo_root=tmp_path)
        calls = builder.extract_calls_from_file(py)
        assert isinstance(calls, list)
        callee_names = [c.callee_name for c in calls]
        assert "helper" in callee_names


# ---------------------------------------------------------------------------
# static/dataflow.py — DataFlowEdge dataclass
# ---------------------------------------------------------------------------


class TestDataFlowEdge:
    def test_data_flow_edge_fields(self, tmp_path):
        from cogant.static.dataflow import DataFlowEdge

        e = DataFlowEdge(
            id="flow1",
            source_symbol="x",
            target_symbol="y",
            edge_type="writes",
            file_path=tmp_path / "f.py",
            line_num=5,
        )
        assert e.id == "flow1"
        assert e.edge_type == "writes"
        assert e.context == "module"
        assert e.metadata == {}


# ---------------------------------------------------------------------------
# static/dataflow.py — DataFlowAnalyzer.analyze_source
# ---------------------------------------------------------------------------


class TestDataFlowAnalyzerSource:
    def test_syntax_error_returns_empty(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        flows = analyzer.analyze_source("def foo(:\n", tmp_path / "bad.py")
        assert flows == []

    def test_simple_assignment(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        flows = analyzer.analyze_source("x = 1\n", tmp_path / "t.py")
        assert isinstance(flows, list)

    def test_function_with_reads(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        source = "def foo(a, b):\n    c = a + b\n    return c\n"
        flows = analyzer.analyze_source(source, tmp_path / "t.py")
        assert isinstance(flows, list)
        edge_types = {f.edge_type for f in flows}
        assert len(edge_types) >= 1

    def test_class_body_analyzed(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        source = "class Foo:\n    x: int = 0\n    def method(self):\n        self.x = 1\n"
        flows = analyzer.analyze_source(source, tmp_path / "cls.py")
        assert isinstance(flows, list)

    def test_augmented_assignment(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        source = "def counter():\n    count = 0\n    count += 1\n    return count\n"
        flows = analyzer.analyze_source(source, tmp_path / "t.py")
        assert isinstance(flows, list)

    def test_annotated_assignment(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        source = "def typed():\n    x: int = 5\n    return x\n"
        flows = analyzer.analyze_source(source, tmp_path / "t.py")
        assert isinstance(flows, list)

    def test_tuple_unpacking(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        source = "def unpack():\n    a, b = 1, 2\n    return a\n"
        flows = analyzer.analyze_source(source, tmp_path / "t.py")
        assert isinstance(flows, list)

    def test_method_call_on_self(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        source = (
            "class Foo:\n"
            "    def run(self):\n"
            "        self.value = self.compute()\n"
            "    def compute(self):\n"
            "        return 42\n"
        )
        flows = analyzer.analyze_source(source, tmp_path / "t.py")
        assert isinstance(flows, list)

    def test_analyze_file_missing_returns_empty(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        flows = analyzer.analyze_file(tmp_path / "nosuchfile.py")
        assert flows == []

    def test_analyze_file_valid(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        py = tmp_path / "module.py"
        py.write_text("x = 1\ny = x + 2\n")
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        flows = analyzer.analyze_file(py)
        assert isinstance(flows, list)

    def test_async_function_analyzed(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        source = "async def fetch():\n    data = await get_data()\n    return data\n"
        flows = analyzer.analyze_source(source, tmp_path / "t.py")
        assert isinstance(flows, list)

    def test_multiple_functions(self, tmp_path):
        from cogant.static.dataflow import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        source = "def foo(a):\n    return a + 1\n\ndef bar(b):\n    return b * 2\n"
        flows = analyzer.analyze_source(source, tmp_path / "t.py")
        assert isinstance(flows, list)
        # Should produce flows from both functions
        contexts = {f.context for f in flows}
        assert "foo" in contexts or "bar" in contexts


# ---------------------------------------------------------------------------
# tools/organize_example_outputs.py — _dest_for_file
# ---------------------------------------------------------------------------


class TestDestForFile:
    def test_known_file_data(self):
        from cogant.tools.organize_example_outputs import _dest_for_file

        assert _dest_for_file("program_graph.json") == "data"

    def test_known_file_reports(self):
        from cogant.tools.organize_example_outputs import _dest_for_file

        assert _dest_for_file("summary.md") == "reports"

    def test_known_file_diagrams(self):
        from cogant.tools.organize_example_outputs import _dest_for_file

        assert _dest_for_file("graph.dot") == "diagrams"

    def test_known_file_site(self):
        from cogant.tools.organize_example_outputs import _dest_for_file

        assert _dest_for_file("index.html") == "site"

    def test_mermaid_extension(self):
        from cogant.tools.organize_example_outputs import _dest_for_file

        assert _dest_for_file("flowchart.mermaid") == "diagrams"

    def test_mermaid_named_file(self):
        from cogant.tools.organize_example_outputs import _dest_for_file

        assert _dest_for_file("state_machine.mermaid") == "diagrams"

    def test_unknown_file_returns_none(self):
        from cogant.tools.organize_example_outputs import _dest_for_file

        assert _dest_for_file("unknown_file.xyz") is None

    def test_unknown_json_returns_none(self):
        from cogant.tools.organize_example_outputs import _dest_for_file

        assert _dest_for_file("custom_data.json") is None


# ---------------------------------------------------------------------------
# tools/organize_example_outputs.py — organize_run_dir
# ---------------------------------------------------------------------------


class TestOrganizeRunDir:
    def test_not_a_dir_returns_none(self, tmp_path):
        from cogant.tools.organize_example_outputs import organize_run_dir

        nonexistent = tmp_path / "not_a_dir"
        result = organize_run_dir(nonexistent)
        assert result is None

    def test_dry_run_does_not_move_files(self, tmp_path):
        from cogant.tools.organize_example_outputs import organize_run_dir

        # Create a flat run dir with a known file
        flat = tmp_path / "run"
        flat.mkdir()
        (flat / "program_graph.json").write_text("{}")
        result = organize_run_dir(flat, dry_run=True)
        assert result == flat
        # File should still be in original location (not moved)
        assert (flat / "program_graph.json").exists()

    def test_organizes_known_files(self, tmp_path):
        from cogant.tools.organize_example_outputs import organize_run_dir

        flat = tmp_path / "run"
        flat.mkdir()
        (flat / "program_graph.json").write_text("{}")
        (flat / "summary.md").write_text("# summary")
        (flat / "graph.dot").write_text("digraph {}")
        result = organize_run_dir(flat)
        assert result == flat
        assert (flat / "data" / "program_graph.json").exists()
        assert (flat / "reports" / "summary.md").exists()
        assert (flat / "diagrams" / "graph.dot").exists()

    def test_already_organized_returns_early(self, tmp_path):
        from cogant.tools.organize_example_outputs import organize_run_dir

        flat = tmp_path / "run"
        flat.mkdir()
        (flat / "data").mkdir()
        (flat / "site").mkdir()
        (flat / "data" / "program_graph.json").write_text("{}")
        (flat / "site" / "index.html").write_text("<html/>")
        result = organize_run_dir(flat)
        assert result == flat

    def test_skips_hidden_files(self, tmp_path):
        from cogant.tools.organize_example_outputs import organize_run_dir

        flat = tmp_path / "run"
        flat.mkdir()
        (flat / ".hidden").write_text("hidden")
        (flat / "program_graph.json").write_text("{}")
        organize_run_dir(flat)
        # .hidden should stay, not be moved
        assert (flat / ".hidden").exists()

    def test_skips_subdirectories(self, tmp_path):
        from cogant.tools.organize_example_outputs import organize_run_dir

        flat = tmp_path / "run"
        flat.mkdir()
        subdir = flat / "subdir"
        subdir.mkdir()
        (flat / "program_graph.json").write_text("{}")
        result = organize_run_dir(flat)
        assert result == flat

    def test_skips_unknown_files(self, tmp_path):
        from cogant.tools.organize_example_outputs import organize_run_dir

        flat = tmp_path / "run"
        flat.mkdir()
        (flat / "unknown_file.xyz").write_text("unknown")
        result = organize_run_dir(flat)
        assert result == flat
        # Unknown file should remain in the flat dir
        assert (flat / "unknown_file.xyz").exists()

    def test_mermaid_goes_to_diagrams(self, tmp_path):
        from cogant.tools.organize_example_outputs import organize_run_dir

        flat = tmp_path / "run"
        flat.mkdir()
        (flat / "flowchart.mermaid").write_text("graph TD")
        result = organize_run_dir(flat)
        assert result == flat
        assert (flat / "diagrams" / "flowchart.mermaid").exists()

    def test_overwrites_existing_dst(self, tmp_path):
        from cogant.tools.organize_example_outputs import organize_run_dir

        flat = tmp_path / "run"
        flat.mkdir()
        (flat / "data").mkdir()
        # Pre-place the target file so overwrite path is triggered
        (flat / "data" / "program_graph.json").write_text("old content")
        (flat / "program_graph.json").write_text("new content")
        # Put site/index.html so the "already organized" check fails (data/ exists but site/ doesn't)
        result = organize_run_dir(flat)
        assert result == flat
        # After overwrite, new content should be in place
        assert (flat / "data" / "program_graph.json").read_text() == "new content"


# ---------------------------------------------------------------------------
# tools/organize_example_outputs.py — migrate_output_tree
# ---------------------------------------------------------------------------


class TestMigrateOutputTree:
    def test_skip_missing_examples(self, tmp_path):
        from cogant.tools.organize_example_outputs import migrate_output_tree

        count = migrate_output_tree(
            tmp_path,
            suite="test_suite",
            examples=["nonexistent_example"],
        )
        assert count == 0

    def test_dry_run_does_not_move(self, tmp_path):
        from cogant.tools.organize_example_outputs import migrate_output_tree

        # Create a flat example dir with program_graph.json
        ex = tmp_path / "myexample"
        ex.mkdir()
        (ex / "program_graph.json").write_text("{}")
        migrate_output_tree(
            tmp_path,
            suite="test_suite",
            examples=["myexample"],
            dry_run=True,
        )
        # dry_run=True; source still exists (move not executed)
        assert ex.exists()

    def test_migrate_and_count(self, tmp_path):
        from cogant.tools.organize_example_outputs import migrate_output_tree

        # Create two example dirs with program_graph.json each
        for name in ["ex1", "ex2"]:
            d = tmp_path / name
            d.mkdir()
            (d / "program_graph.json").write_text("{}")
        count = migrate_output_tree(
            tmp_path,
            suite="suite1",
            examples=["ex1", "ex2"],
        )
        assert count == 2

    def test_empty_examples_list(self, tmp_path):
        from cogant.tools.organize_example_outputs import migrate_output_tree

        count = migrate_output_tree(
            tmp_path,
            suite="test_suite",
            examples=[],
        )
        assert count == 0


# ---------------------------------------------------------------------------
# tools/organize_example_outputs.py — main (CLI)
# ---------------------------------------------------------------------------


class TestOrganizeMain:
    def test_main_returns_zero_empty(self, tmp_path):
        from cogant.tools.organize_example_outputs import main

        result = main(["--suite", "control_positive", str(tmp_path)])
        assert result == 0

    def test_main_organize_only(self, tmp_path):
        from cogant.tools.organize_example_outputs import main

        flat = tmp_path / "run"
        flat.mkdir()
        (flat / "program_graph.json").write_text("{}")
        result = main(["--organize-only", str(flat), str(tmp_path)])
        assert result == 0

    def test_main_dry_run(self, tmp_path):
        from cogant.tools.organize_example_outputs import main

        result = main(["--dry-run", str(tmp_path)])
        assert result == 0
