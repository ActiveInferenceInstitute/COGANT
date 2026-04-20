# py/cogant/plugins/ruby.py

from pathlib import Path
from typing import List

import tree_sitter_ruby  # type: ignore
from tree_sitter import Language, Parser, Node as TSNode

from cogant.plugins.base import LanguagePlugin, ParseResult
from cogant.schemas.core import Node, Edge, NodeKind, EdgeKind


_LANGUAGE = Language(tree_sitter_ruby.language(), "ruby")


class RubyPlugin(LanguagePlugin):
    """Parse Ruby source into COGANT program-graph nodes and edges."""

    name = "ruby"
    extensions = (".rb",)
    shebang_patterns = ("ruby",)

    def __init__(self) -> None:
        self._parser = Parser()
        self._parser.set_language(_LANGUAGE)

    def parse_file(self, path: Path) -> ParseResult:
        source = path.read_text(encoding="utf-8")
        return self.parse_source(source, str(path))

    def parse_source(self, source: str, filename: str) -> ParseResult:
        tree = self._parser.parse(source.encode("utf-8"))
        nodes: List[Node] = []
        edges: List[Edge] = []

        module_node = Node(
            id=f"{filename}:module",
            kind=NodeKind.MODULE,
            name=Path(filename).stem,
            file=filename,
        )
        nodes.append(module_node)

        self._walk(tree.root_node, filename, module_node, nodes, edges)
        return ParseResult(nodes=nodes, edges=edges, diagnostics=[])

    def _walk(
        self,
        ts_node: TSNode,
        filename: str,
        parent: Node,
        nodes: List[Node],
        edges: List[Edge],
    ) -> None:
        if ts_node.type == "class":
            name_node = ts_node.child_by_field_name("name")
            class_name = (
                name_node.text.decode("utf-8") if name_node else "<anon>"
            )
            class_node = Node(
                id=f"{filename}:{class_name}",
                kind=NodeKind.CLASS,
                name=class_name,
                file=filename,
                line_start=ts_node.start_point[0] + 1,
                line_end=ts_node.end_point[0] + 1,
            )
            nodes.append(class_node)
            edges.append(
                Edge(source_id=parent.id, target_id=class_node.id,
                     kind=EdgeKind.CONTAINS)
            )
            parent = class_node
        elif ts_node.type == "method":
            name_node = ts_node.child_by_field_name("name")
            method_name = (
                name_node.text.decode("utf-8") if name_node else "<anon>"
            )
            method_node = Node(
                id=f"{filename}:{parent.name}.{method_name}",
                kind=NodeKind.METHOD,
                name=method_name,
                file=filename,
                line_start=ts_node.start_point[0] + 1,
                line_end=ts_node.end_point[0] + 1,
            )
            nodes.append(method_node)
            edges.append(
                Edge(source_id=parent.id, target_id=method_node.id,
                     kind=EdgeKind.CONTAINS)
            )

        for child in ts_node.children:
            self._walk(child, filename, parent, nodes, edges)
