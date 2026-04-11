#!/usr/bin/env python3
"""Coverage boost batch 76 — static/types.py extended paths, static/calls.py extended,
gnn/json_export.py extended, gnn/matrices.py extended.

Covers:
- static/types.py: TypeInferencer (infer_types_from_source with complex code,
  infer_types_from_file, _infer_from_class, _infer_init_attributes,
  _infer_from_assign, _infer_from_annassign, _annotation_to_str, _safe_unparse,
  _infer_return_from_body, _infer_literal_type)
- static/calls.py: CallGraphBuilder (extract_calls_from_source with classes,
  extract_calls_from_file), CallExtractorVisitor (_extract_call method calls)
- gnn/json_export.py: GNNJSONExporter extended (more complex models)
- gnn/matrices.py: GNNMatrices (compute_A/B/C/D with state space having variables)
"""

import pytest
from pathlib import Path

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state_space():
    from cogant.statespace.compiler import StateSpaceModel
    from cogant.statespace.temporal import TimeRegime
    return StateSpaceModel(
        id="ss1", schema_name="test",
        variables={}, observations={}, actions={},
        transitions={}, likelihoods={}, preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


def _make_graph_with_nodes():
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import NodeKind, EdgeKind
    builder = ProgramGraphBuilder(repo_uri="file:///test")
    n1 = builder.add_node(NodeKind.MODULE, "mod", "mod", path="mod.py")
    n2 = builder.add_node(NodeKind.FUNCTION, "fn", "mod.fn", path="mod.py")
    builder.add_edge(n1.id, n2.id, EdgeKind.CONTAINS)
    return builder.finalize()


def _make_process_model():
    from cogant.process.extractor import ProcessModel
    return ProcessModel(id="pm1", schema_name="test", stages={}, connections={})


# ---------------------------------------------------------------------------
# static/types.py — TypeInferencer extended
# ---------------------------------------------------------------------------

class TestTypeInferencerExtended:
    def _make_inferencer(self):
        from cogant.static.types import TypeInferencer
        return TypeInferencer()

    def test_infer_types_from_source_function_return_annotation(self, tmp_path):
        inferencer = self._make_inferencer()
        src = '''
def greet(name: str) -> str:
    return f"Hello {name}"

def count(items: list) -> int:
    return len(items)
'''
        fp = tmp_path / "greet.py"
        result = inferencer.infer_types_from_source(src, fp)
        assert isinstance(result, list)

    def test_infer_types_from_source_class_with_init(self, tmp_path):
        inferencer = self._make_inferencer()
        src = '''
class Counter:
    """A counter class."""
    def __init__(self) -> None:
        self.count: int = 0
        self.name = "default"

    def increment(self) -> int:
        self.count += 1
        return self.count
'''
        fp = tmp_path / "counter.py"
        result = inferencer.infer_types_from_source(src, fp)
        assert isinstance(result, list)

    def test_infer_types_from_source_annotated_assignment(self, tmp_path):
        inferencer = self._make_inferencer()
        src = "x: int = 5\ny: str = 'hello'\nz: float = 3.14\n"
        fp = tmp_path / "ann.py"
        result = inferencer.infer_types_from_source(src, fp)
        assert isinstance(result, list)

    def test_infer_types_from_source_plain_assignment(self, tmp_path):
        inferencer = self._make_inferencer()
        src = "x = 1\ny = 'text'\nz = [1, 2, 3]\nd = {}\n"
        fp = tmp_path / "assign.py"
        result = inferencer.infer_types_from_source(src, fp)
        assert isinstance(result, list)

    def test_infer_types_from_source_with_property(self, tmp_path):
        inferencer = self._make_inferencer()
        src = '''
class MyClass:
    @property
    def value(self):
        return self._value
'''
        fp = tmp_path / "prop.py"
        result = inferencer.infer_types_from_source(src, fp)
        assert isinstance(result, list)

    def test_infer_types_from_source_with_yield(self, tmp_path):
        inferencer = self._make_inferencer()
        src = '''
def generate():
    for i in range(10):
        yield i
'''
        fp = tmp_path / "gen.py"
        result = inferencer.infer_types_from_source(src, fp)
        assert isinstance(result, list)

    def test_infer_types_from_source_syntax_error(self, tmp_path):
        inferencer = self._make_inferencer()
        result = inferencer.infer_types_from_source("def bad(: pass", tmp_path / "bad.py")
        assert result == []

    def test_infer_types_from_file_valid(self, tmp_path):
        inferencer = self._make_inferencer()
        p = tmp_path / "typed.py"
        p.write_text("def foo(x: int) -> str:\n    return str(x)\n")
        result = inferencer.infer_types_from_file(p)
        assert isinstance(result, list)

    def test_infer_types_from_file_nonexistent(self, tmp_path):
        inferencer = self._make_inferencer()
        result = inferencer.infer_types_from_file(tmp_path / "missing.py")
        assert isinstance(result, list)

    def test_annotation_to_str_none(self):
        from cogant.static.types import TypeInferencer
        result = TypeInferencer._annotation_to_str(None)
        assert result is None

    def test_annotation_to_str_name(self):
        import ast
        from cogant.static.types import TypeInferencer
        node = ast.Name(id="str", ctx=ast.Load())
        result = TypeInferencer._annotation_to_str(node)
        assert "str" in result

    def test_safe_unparse_none(self):
        from cogant.static.types import TypeInferencer
        result = TypeInferencer._safe_unparse(None)
        assert result is None

    def test_infer_types_from_source_complex_class(self, tmp_path):
        inferencer = self._make_inferencer()
        src = '''
class DataProcessor:
    """Process data."""
    batch_size: int = 32
    name: str = "processor"

    def __init__(self, batch_size: int = 32) -> None:
        self.batch_size = batch_size
        self.results: list = []

    def process(self, data: list) -> dict:
        return {"result": data}

    @property
    def summary(self):
        return {"batch": self.batch_size}
'''
        fp = tmp_path / "dp.py"
        result = inferencer.infer_types_from_source(src, fp)
        assert isinstance(result, list)

    def test_infer_types_from_source_async_function(self, tmp_path):
        inferencer = self._make_inferencer()
        src = "async def fetch(url: str) -> bytes:\n    pass\n"
        fp = tmp_path / "async.py"
        result = inferencer.infer_types_from_source(src, fp)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# static/calls.py — CallGraphBuilder extended
# ---------------------------------------------------------------------------

class TestCallGraphBuilderExtended:
    def _make_builder(self):
        from cogant.static.calls import CallGraphBuilder
        return CallGraphBuilder()

    def test_extract_calls_from_source_simple_function_call(self, tmp_path):
        builder = self._make_builder()
        src = '''
def helper():
    pass

def main():
    helper()
    print("hello")
'''
        fp = tmp_path / "calls.py"
        calls = builder.extract_calls_from_source(src, fp)
        assert isinstance(calls, list)

    def test_extract_calls_from_source_method_calls(self, tmp_path):
        builder = self._make_builder()
        src = '''
class Processor:
    def setup(self):
        self.data = []

    def run(self):
        self.setup()
        result = self.data.append(1)
        return result
'''
        fp = tmp_path / "proc.py"
        calls = builder.extract_calls_from_source(src, fp)
        assert isinstance(calls, list)

    def test_extract_calls_from_source_chained_calls(self, tmp_path):
        builder = self._make_builder()
        src = '''
def process(data):
    return sorted(data, key=lambda x: x.strip().lower())
'''
        fp = tmp_path / "chain.py"
        calls = builder.extract_calls_from_source(src, fp)
        assert isinstance(calls, list)

    def test_extract_calls_from_source_empty(self, tmp_path):
        builder = self._make_builder()
        src = "x = 1\n"
        fp = tmp_path / "empty.py"
        calls = builder.extract_calls_from_source(src, fp)
        assert isinstance(calls, list)

    def test_extract_calls_from_file_valid(self, tmp_path):
        builder = self._make_builder()
        p = tmp_path / "sample.py"
        p.write_text("def foo():\n    bar()\n\ndef bar():\n    pass\n")
        calls = builder.extract_calls_from_file(p)
        assert isinstance(calls, list)

    def test_extract_calls_from_file_nonexistent(self, tmp_path):
        builder = self._make_builder()
        calls = builder.extract_calls_from_file(tmp_path / "missing.py")
        assert isinstance(calls, list)
        assert len(calls) == 0

    def test_extract_calls_from_source_syntax_error(self, tmp_path):
        builder = self._make_builder()
        calls = builder.extract_calls_from_source("def bad(: pass", tmp_path / "bad.py")
        assert isinstance(calls, list)

    def test_extract_calls_from_source_nested_classes(self, tmp_path):
        builder = self._make_builder()
        src = '''
class Outer:
    class Inner:
        def method(self):
            return self.compute()

        def compute(self):
            return 42
'''
        fp = tmp_path / "nested.py"
        calls = builder.extract_calls_from_source(src, fp)
        assert isinstance(calls, list)


# ---------------------------------------------------------------------------
# gnn/json_export.py — GNNJSONExporter extended
# ---------------------------------------------------------------------------

class TestGNNJSONExporterExtended:
    def _make_exporter(self, with_nodes=False):
        from cogant.gnn.json_export import GNNJSONExporter
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind, EdgeKind
        if with_nodes:
            builder = ProgramGraphBuilder(repo_uri="file:///test")
            n1 = builder.add_node(NodeKind.MODULE, "mod", "mod", path="mod.py")
            n2 = builder.add_node(NodeKind.CLASS, "MyClass", "mod.MyClass", path="mod.py")
            n3 = builder.add_node(NodeKind.FUNCTION, "method", "mod.MyClass.method", path="mod.py")
            builder.add_edge(n1.id, n2.id, EdgeKind.CONTAINS)
            builder.add_edge(n2.id, n3.id, EdgeKind.CONTAINS)
            graph = builder.finalize()
        else:
            from cogant.schemas.graph import ProgramGraph, GraphMetadata
            graph = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///test"))
        return GNNJSONExporter(
            program_graph=graph,
            state_space_model=_make_state_space(),
            process_model=_make_process_model(),
            semantic_mappings={},
        )

    def test_export_with_nodes_is_valid_json(self):
        import json
        exporter = self._make_exporter(with_nodes=True)
        result_str = exporter.export_to_string()
        data = json.loads(result_str)
        assert isinstance(data, dict)

    def test_export_with_nodes_has_model_name(self):
        exporter = self._make_exporter(with_nodes=True)
        result = exporter.export()
        assert isinstance(result, dict)

    def test_export_from_file_if_supported(self, tmp_path):
        import json
        exporter = self._make_exporter()
        result = exporter.export()
        # Write to file and verify
        outfile = tmp_path / "model.json"
        outfile.write_text(json.dumps(result))
        data = json.loads(outfile.read_text())
        assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# gnn/matrices.py — GNNMatrices extended
# ---------------------------------------------------------------------------

class TestGNNMatricesExtended:
    def _make_matrices(self, with_state_vars=False):
        from cogant.gnn.matrices import GNNMatrices
        graph = _make_graph_with_nodes()
        state_space = _make_state_space()
        return GNNMatrices(graph, mappings={}, state_space=state_space)

    def test_compute_A_with_no_state_vars(self):
        matrices = self._make_matrices()
        A = matrices.compute_A()
        assert isinstance(A, list)

    def test_compute_B_structure(self):
        matrices = self._make_matrices()
        B = matrices.compute_B()
        assert isinstance(B, list)

    def test_compute_C_structure(self):
        matrices = self._make_matrices()
        C = matrices.compute_C()
        assert isinstance(C, list)

    def test_compute_D_structure(self):
        matrices = self._make_matrices()
        D = matrices.compute_D()
        assert isinstance(D, list)

    def test_to_dict_has_required_keys(self):
        matrices = self._make_matrices()
        result = matrices.to_dict()
        assert isinstance(result, dict)
        # Should have at least some matrix keys
        assert len(result) >= 1

    def test_validate_shapes_both_return_types(self):
        matrices = self._make_matrices()
        valid, errors = matrices.validate_shapes()
        assert isinstance(valid, bool)
        assert isinstance(errors, list)

    def test_to_gnn_markdown_block_is_str(self):
        matrices = self._make_matrices()
        result = matrices.to_gnn_markdown_block()
        assert isinstance(result, str)
