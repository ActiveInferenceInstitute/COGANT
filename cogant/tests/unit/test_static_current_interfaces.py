import ast
from pathlib import Path

import pytest

from cogant.static.dataflow import DataFlowAnalyzer, DataFlowVisitor
from cogant.static.types import TypeInferencer


def test_dataflow_source_and_ast_visitor_agree(tmp_path: Path) -> None:
    analyzer = DataFlowAnalyzer(tmp_path)
    visitor = DataFlowVisitor(tmp_path / "example.py", "module", ast.parse("y = x\n").body)
    analyzed = analyzer.analyze_source("y = x\n", tmp_path / "example.py")
    assert [(edge.source_symbol, edge.target_symbol, edge.edge_type) for edge in analyzed] == [
        (edge.source_symbol, edge.target_symbol, edge.edge_type) for edge in visitor.flows
    ]
    assert any(edge.source_symbol == "x" and edge.target_symbol == "y" for edge in visitor.flows)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("None", "None"),
        ("True", "bool"),
        ("False", "bool"),
        ("[1, 2]", "list"),
        ("{'key': 1}", "dict"),
        ("{1, 2}", "set"),
        ("(1, 2)", "tuple"),
        ("'hello'", "str"),
        ('"world"', "str"),
        ("42", "int"),
        ("-5", None),
        ("3.14", "float"),
        ("list()", "list"),
        ("dict()", "dict"),
        ("set()", "set"),
        ("tuple()", "tuple"),
        ("some_variable", None),
    ],
)
def test_public_assignment_inference_preserves_current_ast_semantics(
    tmp_path: Path, value: str, expected: str | None
) -> None:
    inferred = TypeInferencer(tmp_path).infer_types_from_source(
        f"value = {value}\n", tmp_path / "source.py"
    )
    records = [item for item in inferred if item.symbol_name == "value"]
    if expected is None:
        assert records == []
    else:
        assert len(records) == 1
        assert records[0].inferred_type == expected
