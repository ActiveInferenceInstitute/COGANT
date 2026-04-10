"""
GraphML exporter for program graph visualization.

Exports program graph as GraphML XML for compatibility with graph visualization tools.
"""

import logging
from xml.etree import ElementTree as ET

from cogant.schemas.graph import ProgramGraph

logger = logging.getLogger(__name__)


class GraphMLExporter:
    """
    Exports program graph to GraphML XML format.
    """

    def __init__(self, program_graph: ProgramGraph):
        """
        Initialize the exporter.

        Args:
            program_graph: The program graph to export.
        """
        self.graph = program_graph

    def export(self) -> str:
        """
        Export the program graph as GraphML XML.

        Returns:
            GraphML XML string.
        """
        logger.info("Exporting program graph to GraphML...")

        # Create root element
        graphml = ET.Element("graphml")
        graphml.set("xmlns", "http://graphml.graphdrawing.org/xmlns")
        graphml.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        graphml.set("xsi:schemaLocation",
                   "http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd")

        # Add key definitions
        self._add_key_definitions(graphml)

        # Create graph
        graph_elem = ET.SubElement(graphml, "graph")
        graph_elem.set("edgedefault", "directed")

        # Add nodes
        for _node_id, node in self.graph.nodes.items():
            self._add_node(graph_elem, node)

        # Add edges
        for _edge_id, edge in self.graph.edges.items():
            self._add_edge(graph_elem, edge)

        # Convert to string
        tree_str = ET.tostring(graphml, encoding="unicode")
        return self._prettify(tree_str)

    def _add_key_definitions(self, graphml: ET.Element) -> None:
        """Add GraphML key definitions."""
        # Node attributes
        for attr in ["kind", "qualified_name", "path", "language"]:
            key = ET.SubElement(graphml, "key")
            key.set("id", attr)
            key.set("for", "node")
            key.set("attr.name", attr)
            key.set("attr.type", "string")

        # Edge attributes
        for attr in ["kind", "weight"]:
            key = ET.SubElement(graphml, "key")
            key.set("id", attr)
            key.set("for", "edge")
            key.set("attr.name", attr)
            key.set("attr.type", "string")

    def _add_node(self, graph_elem: ET.Element, node) -> None:
        """Add a node element."""
        node_elem = ET.SubElement(graph_elem, "node")
        node_elem.set("id", node.id)
        node_elem.set("labels", node.name)

        # Add data elements
        self._add_data(node_elem, "kind", str(node.kind))
        self._add_data(node_elem, "qualified_name", node.qualified_name)
        if node.path:
            self._add_data(node_elem, "path", node.path)
        if node.language:
            self._add_data(node_elem, "language", node.language)

    def _add_edge(self, graph_elem: ET.Element, edge) -> None:
        """Add an edge element."""
        edge_elem = ET.SubElement(graph_elem, "edge")
        edge_elem.set("source", edge.source_id)
        edge_elem.set("target", edge.target_id)

        # Add data elements
        self._add_data(edge_elem, "kind", str(edge.kind))
        self._add_data(edge_elem, "weight", str(edge.weight))

    def _add_data(self, parent: ET.Element, key: str, value: str) -> None:
        """Add a data element."""
        data = ET.SubElement(parent, "data")
        data.set("key", key)
        data.text = value

    def _prettify(self, xml_string: str) -> str:
        """Pretty-print XML string."""
        # Simple prettification
        import xml.dom.minidom
        dom = xml.dom.minidom.parseString(xml_string)
        return dom.toprettyxml(indent="  ")
