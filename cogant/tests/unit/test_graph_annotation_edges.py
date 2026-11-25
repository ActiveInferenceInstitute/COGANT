"""Explicit annotation dependencies use lexical owners and in-repo bindings only."""

from pathlib import Path

from cogant.api.bundle import Bundle
from cogant.api.orchestration import run_graph, run_ingest


def _graph(repo: Path):
    bundle = Bundle(target=str(repo))
    run_ingest(str(repo), bundle)
    run_graph(bundle, str(repo))
    return bundle.artifacts["_program_graph"]


def test_annotations_cover_parameters_returns_fields_and_local_bindings(tmp_path: Path):
    (tmp_path / "domain.py").write_text("class Item:\n    pass\n", encoding="utf-8")
    (tmp_path / "use.py").write_text(
        "from domain import Item as Row\n"
        "import domain as model\n"
        "global_row: Row\n"
        "class Holder:\n"
        "    field: 'model.Item'\n"
        "    def method(self, value: Row, /, *rows: Row, flag: Row, **named: Row) -> list[Row]:\n"
        "        local: Row\n"
        "        return []\n"
        "def combine(value: 'list[model.Item] | None') -> Row:\n"
        "    local: Row\n"
        "    return value\n",
        encoding="utf-8",
    )
    graph = _graph(tmp_path)
    item = next(node for node in graph.nodes.values() if node.name == "Item")
    edges = [edge for edge in graph.edges.values() if edge.metadata.get("type_annotation")]
    owners = {graph.nodes[edge.source_id].qualified_name: edge for edge in edges}
    assert set(owners) == {"use", "use.Holder", "use.Holder.method", "use.combine"}
    assert all(edge.target_id == item.id and edge.kind.value == "depends_on" for edge in edges)
    assert all(edge.evidence_sources == ["static_annotation"] for edge in edges)
    assert {entry["location"] for entry in owners["use.Holder.method"].metadata["annotations"]} == {
        "parameter:value",
        "parameter:rows",
        "parameter:flag",
        "parameter:named",
        "return",
        "variable:local",
    }
    assert {entry["location"] for entry in owners["use.combine"].metadata["annotations"]} == {
        "parameter:value",
        "return",
        "variable:local",
    }


def test_unknown_external_literal_metadata_and_nested_annotations_do_not_guess(tmp_path: Path):
    (tmp_path / "unrelated.py").write_text("class Missing:\n    pass\n", encoding="utf-8")
    (tmp_path / "use.py").write_text(
        "from typing import Annotated as Tag, Literal as Only\n"
        "class Local:\n    pass\n"
        "def unknown(value: Missing, other: external.Local):\n    pass\n"
        "def literals(value: Only['Local'], other: Tag[int, 'Local']):\n    pass\n"
        "def factory(value: make_type()):\n    pass\n"
        "def outer():\n"
        "    def nested(value: Local):\n        pass\n"
        "    return nested\n"
        "def explicit(value: Tag[Local, 'Missing']):\n    pass\n",
        encoding="utf-8",
    )
    graph = _graph(tmp_path)
    dependencies = [edge for edge in graph.edges.values() if edge.metadata.get("type_annotation")]
    explicit = next(node for node in graph.nodes.values() if node.name == "explicit")
    local = next(node for node in graph.nodes.values() if node.name == "Local")
    assert {(edge.source_id, edge.target_id) for edge in dependencies} == {(explicit.id, local.id)}
    assert not any(edge.kind.value in {"calls", "async_calls"} for edge in dependencies)
