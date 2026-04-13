"""
GraphML exporter for program graph visualization.

Exports program graph as GraphML XML for compatibility with graph visualization tools.
Optionally includes semantic role annotations from semantic mappings.
"""

import logging
from pathlib import Path
from typing import Any
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

    def export_with_metadata(
        self,
        graph: ProgramGraph,
        mappings: dict[str, Any],
        output_path: str,
    ) -> str:
        """
        Export program graph with semantic role annotations.

        Includes semantic mappings as additional node attributes to annotate
        roles and confidence scores from the translation engine.

        Args:
            graph: ProgramGraph to export.
            mappings: Semantic mappings dict with node roles and confidence.
            output_path: Path where GraphML file should be written.

        Returns:
            Path to the written GraphML file.
        """
        logger.info(f"Exporting program graph with metadata to: {output_path}")

        # Create root element
        graphml = ET.Element("graphml")
        graphml.set("xmlns", "http://graphml.graphdrawing.org/xmlns")
        graphml.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        graphml.set(
            "xsi:schemaLocation",
            "http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd",
        )

        # Add key definitions including semantic roles
        self._add_key_definitions(graphml, with_semantic=True)

        # Create graph
        graph_elem = ET.SubElement(graphml, "graph")
        graph_elem.set("edgedefault", "directed")

        # Add nodes with semantic role annotations
        mappings_dict = mappings.get("mappings", {})
        for _node_id, node in self.graph.nodes.items():
            self._add_node_with_metadata(graph_elem, node, mappings_dict)

        # Add edges
        for _edge_id, edge in self.graph.edges.items():
            self._add_edge(graph_elem, edge)

        # Convert to string and prettify
        tree_str = ET.tostring(graphml, encoding="unicode")
        prettified = self._prettify(tree_str)

        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            f.write(prettified)

        logger.info(f"Exported GraphML with metadata: {output_path}")
        return str(output_file)

    def _add_key_definitions(self, graphml: ET.Element, with_semantic: bool = False) -> None:
        """Add GraphML key definitions."""
        # Node attributes
        node_attrs = ["kind", "qualified_name", "path", "language"]
        if with_semantic:
            node_attrs.extend(["semantic_role", "confidence_score", "module_path", "line_number"])

        for attr in node_attrs:
            key = ET.SubElement(graphml, "key")
            key.set("id", attr)
            key.set("for", "node")
            key.set("attr.name", attr)
            key.set("attr.type", "string")

        # Edge attributes
        edge_attrs = ["kind", "weight", "source_file"]
        for attr in edge_attrs:
            key = ET.SubElement(graphml, "key")
            key.set("id", attr)
            key.set("for", "edge")
            key.set("attr.name", attr)
            key.set("attr.type", "string")

    def _add_node(self, graph_elem: ET.Element, node: Any) -> None:
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

    def _add_node_with_metadata(
        self,
        graph_elem: ET.Element,
        node: Any,
        mappings: dict[str, Any],
    ) -> None:
        """Add a node element with semantic metadata."""
        node_elem = ET.SubElement(graph_elem, "node")
        node_elem.set("id", node.id)
        node_elem.set("labels", node.name)

        # Add standard data elements
        self._add_data(node_elem, "kind", str(node.kind))
        self._add_data(node_elem, "qualified_name", node.qualified_name)
        if node.path:
            self._add_data(node_elem, "path", node.path)
        if node.language:
            self._add_data(node_elem, "language", node.language)

        # Add semantic metadata if available
        if node.id in mappings:
            mapping = mappings[node.id]
            self._add_data(node_elem, "semantic_role", mapping.get("role", ""))
            confidence = mapping.get("confidence", 0.0)
            self._add_data(node_elem, "confidence_score", str(confidence))

        # Add source location metadata
        if node.path:
            self._add_data(node_elem, "module_path", node.path)
        if hasattr(node, "source_range") and node.source_range:
            source_range = node.source_range
            if isinstance(source_range, dict) and "start" in source_range:
                line_num = source_range["start"].get("line", "")
                if line_num:
                    self._add_data(node_elem, "line_number", str(line_num))

    def _add_edge(self, graph_elem: ET.Element, edge: Any) -> None:
        """Add an edge element."""
        edge_elem = ET.SubElement(graph_elem, "edge")
        edge_elem.set("source", edge.source_id)
        edge_elem.set("target", edge.target_id)

        # Add data elements
        self._add_data(edge_elem, "kind", str(edge.kind))
        self._add_data(edge_elem, "weight", str(edge.weight))
        # Add source file if available from metadata
        if hasattr(edge, "metadata") and isinstance(edge.metadata, dict):
            source_file = edge.metadata.get("source_file", "")
            if source_file:
                self._add_data(edge_elem, "source_file", source_file)

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
