//! Program graph representation and manipulation.
//!
//! This crate provides a labeled directed graph for representing program structure,
//! with nodes for functions, variables, types, etc., and edges for relationships.

use cogant_core::{Confidence, EdgeKind, NodeKind, Provenance, SemanticRole, StableId};
use petgraph::graph::{DiGraph, NodeIndex};
use petgraph::visit::EdgeRef;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Metadata associated with a graph node.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeData {
    /// Unique identifier for this node
    pub id: StableId,
    /// Human-readable name
    pub name: String,
    /// Kind of node (function, variable, type, etc.)
    pub kind: NodeKind,
    /// Primary semantic role
    pub role: SemanticRole,
    /// Optional type information
    pub type_name: Option<String>,
    /// Source code location
    pub provenance: Provenance,
    /// Confidence in the node's classification
    pub confidence: Confidence,
    /// Additional attributes (key-value pairs)
    pub attributes: HashMap<String, String>,
    /// Optional documentation
    pub documentation: Option<String>,
}

impl NodeData {
    /// Create a new node with basic information.
    pub fn new(
        id: StableId,
        name: impl Into<String>,
        kind: NodeKind,
        role: SemanticRole,
        provenance: Provenance,
    ) -> Self {
        Self {
            id,
            name: name.into(),
            kind,
            role,
            type_name: None,
            provenance,
            confidence: Confidence::MEDIUM,
            attributes: HashMap::new(),
            documentation: None,
        }
    }

    /// Set the type name for this node.
    pub fn with_type(mut self, type_name: impl Into<String>) -> Self {
        self.type_name = Some(type_name.into());
        self
    }

    /// Set the confidence level.
    pub fn with_confidence(mut self, confidence: Confidence) -> Self {
        self.confidence = confidence;
        self
    }

    /// Set the documentation.
    pub fn with_documentation(mut self, doc: impl Into<String>) -> Self {
        self.documentation = Some(doc.into());
        self
    }

    /// Add an attribute to this node.
    pub fn add_attribute(&mut self, key: impl Into<String>, value: impl Into<String>) {
        self.attributes.insert(key.into(), value.into());
    }
}

/// Metadata associated with a graph edge.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EdgeData {
    /// Kind of relationship
    pub kind: EdgeKind,
    /// How confident we are in this relationship
    pub confidence: Confidence,
    /// Source of this relationship
    pub provenance: Provenance,
    /// Edge label or reason
    pub label: Option<String>,
    /// Additional attributes
    pub attributes: HashMap<String, String>,
}

impl EdgeData {
    /// Create a new edge with basic information.
    pub fn new(kind: EdgeKind, provenance: Provenance) -> Self {
        Self {
            kind,
            confidence: Confidence::MEDIUM,
            provenance,
            label: None,
            attributes: HashMap::new(),
        }
    }

    /// Set the confidence level.
    pub fn with_confidence(mut self, confidence: Confidence) -> Self {
        self.confidence = confidence;
        self
    }

    /// Set the edge label.
    pub fn with_label(mut self, label: impl Into<String>) -> Self {
        self.label = Some(label.into());
        self
    }

    /// Add an attribute to this edge.
    pub fn add_attribute(&mut self, key: impl Into<String>, value: impl Into<String>) {
        self.attributes.insert(key.into(), value.into());
    }
}

/// A directed graph representing program structure and relationships.
///
/// Nodes represent program entities (functions, variables, types, modules).
/// Edges represent relationships (calls, uses, defines, inherits, etc.).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProgramGraph {
    graph: DiGraph<NodeData, EdgeData>,
    /// Map from StableId to NodeIndex for fast lookup.
    ///
    /// Skipped during (de)serialization because `NodeIndex` is not serde-aware;
    /// rebuilt from `graph` via [`ProgramGraph::rebuild_index`] after deserialization.
    #[serde(skip, default)]
    id_to_index: HashMap<StableId, NodeIndex>,
}

impl ProgramGraph {
    /// Create a new empty program graph.
    pub fn new() -> Self {
        Self {
            graph: DiGraph::new(),
            id_to_index: HashMap::new(),
        }
    }

    /// Rebuild the `id_to_index` lookup map from the underlying graph.
    ///
    /// Must be called after deserializing a `ProgramGraph`, since the lookup
    /// index is not persisted (see the `#[serde(skip)]` on `id_to_index`).
    pub fn rebuild_index(&mut self) {
        self.id_to_index.clear();
        for idx in self.graph.node_indices() {
            if let Some(node) = self.graph.node_weight(idx) {
                self.id_to_index.insert(node.id.clone(), idx);
            }
        }
    }

    /// Add a node to the graph.
    pub fn add_node(&mut self, node: NodeData) -> NodeIndex {
        let id = node.id.clone();
        let idx = self.graph.add_node(node);
        self.id_to_index.insert(id, idx);
        idx
    }

    /// Get a node by its StableId.
    pub fn get_node(&self, id: &StableId) -> Option<&NodeData> {
        self.id_to_index
            .get(id)
            .and_then(|idx| self.graph.node_weight(*idx))
    }

    /// Get a mutable reference to a node by its StableId.
    pub fn get_node_mut(&mut self, id: &StableId) -> Option<&mut NodeData> {
        if let Some(&idx) = self.id_to_index.get(id) {
            self.graph.node_weight_mut(idx)
        } else {
            None
        }
    }

    /// Get a node by its NodeIndex.
    pub fn get_node_by_index(&self, idx: NodeIndex) -> Option<&NodeData> {
        self.graph.node_weight(idx)
    }

    /// Add an edge between two nodes.
    pub fn add_edge(&mut self, from: &StableId, to: &StableId, edge: EdgeData) -> Option<()> {
        let from_idx = self.id_to_index.get(from)?;
        let to_idx = self.id_to_index.get(to)?;
        self.graph.add_edge(*from_idx, *to_idx, edge);
        Some(())
    }

    /// Query nodes by name (substring match).
    pub fn query_nodes_by_name(&self, name: &str) -> Vec<&NodeData> {
        self.graph
            .node_weights()
            .filter(|n| n.name.contains(name))
            .collect()
    }

    /// Query nodes by kind.
    pub fn query_nodes_by_kind(&self, kind: NodeKind) -> Vec<&NodeData> {
        self.graph
            .node_weights()
            .filter(|n| n.kind == kind)
            .collect()
    }

    /// Query nodes by semantic role.
    pub fn query_nodes_by_role(&self, role: SemanticRole) -> Vec<&NodeData> {
        self.graph
            .node_weights()
            .filter(|n| n.role == role)
            .collect()
    }

    /// Get all nodes that a given node calls (outgoing Calls edges).
    pub fn get_callees(&self, from: &StableId) -> Vec<&NodeData> {
        self.id_to_index
            .get(from)
            .map(|&idx| {
                self.graph
                    .edges(idx)
                    .filter(|e| e.weight().kind == EdgeKind::Calls)
                    .filter_map(|e| self.graph.node_weight(e.target()))
                    .collect()
            })
            .unwrap_or_default()
    }

    /// Get all nodes that call a given node (incoming Calls edges).
    pub fn get_callers(&self, to: &StableId) -> Vec<&NodeData> {
        self.id_to_index
            .get(to)
            .map(|&idx| {
                self.graph
                    .edges_directed(idx, petgraph::Direction::Incoming)
                    .filter(|e| e.weight().kind == EdgeKind::Calls)
                    .filter_map(|e| self.graph.node_weight(e.source()))
                    .collect()
            })
            .unwrap_or_default()
    }

    /// Get all outgoing edges of a given kind from a node.
    pub fn get_outgoing_edges(&self, from: &StableId, kind: EdgeKind) -> Vec<&NodeData> {
        self.id_to_index
            .get(from)
            .map(|&idx| {
                self.graph
                    .edges(idx)
                    .filter(|e| e.weight().kind == kind)
                    .filter_map(|e| self.graph.node_weight(e.target()))
                    .collect()
            })
            .unwrap_or_default()
    }

    /// Get all incoming edges of a given kind to a node.
    pub fn get_incoming_edges(&self, to: &StableId, kind: EdgeKind) -> Vec<&NodeData> {
        self.id_to_index
            .get(to)
            .map(|&idx| {
                self.graph
                    .edges_directed(idx, petgraph::Direction::Incoming)
                    .filter(|e| e.weight().kind == kind)
                    .filter_map(|e| self.graph.node_weight(e.source()))
                    .collect()
            })
            .unwrap_or_default()
    }

    /// Get total number of nodes.
    pub fn node_count(&self) -> usize {
        self.graph.node_count()
    }

    /// Get total number of edges.
    pub fn edge_count(&self) -> usize {
        self.graph.edge_count()
    }

    /// Iterate over all nodes.
    pub fn nodes(&self) -> impl Iterator<Item = &NodeData> {
        self.graph.node_weights()
    }

    /// Iterate over all edges with their source and target.
    pub fn edges(&self) -> Vec<(&NodeData, &NodeData, &EdgeData)> {
        self.graph
            .edge_references()
            .filter_map(|e| {
                let source = self.graph.node_weight(e.source())?;
                let target = self.graph.node_weight(e.target())?;
                let weight = e.weight();
                Some((source, target, weight))
            })
            .collect()
    }

    /// Check if a specific edge exists.
    pub fn has_edge(&self, from: &StableId, to: &StableId, kind: EdgeKind) -> bool {
        self.id_to_index
            .get(from)
            .and_then(|&from_idx| {
                self.id_to_index.get(to).and_then(|&to_idx| {
                    self.graph
                        .find_edge(from_idx, to_idx)
                        .and_then(|e_idx| self.graph.edge_weight(e_idx))
                        .map(|e| e.kind == kind)
                })
            })
            .unwrap_or(false)
    }

    /// Get the transitive closure of callees (all functions reachable via calls).
    pub fn transitive_callees(&self, from: &StableId) -> Vec<StableId> {
        let mut visited = std::collections::HashSet::new();
        let mut queue = vec![from.clone()];

        while let Some(current) = queue.pop() {
            if visited.insert(current.clone()) {
                for callee in self.get_callees(&current) {
                    queue.push(callee.id.clone());
                }
            }
        }

        visited.remove(from);
        visited.into_iter().collect()
    }
}

impl Default for ProgramGraph {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn create_test_node(name: &str) -> NodeData {
        NodeData::new(
            StableId::new(format!("node_{}", name)),
            name,
            NodeKind::Function,
            SemanticRole::FunctionDef,
            Provenance::Unknown,
        )
    }

    #[test]
    fn test_graph_add_nodes() {
        let mut graph = ProgramGraph::new();
        let node1 = create_test_node("foo");
        let idx = graph.add_node(node1);
        assert_eq!(graph.node_count(), 1);

        let node = graph.get_node_by_index(idx);
        assert!(node.is_some());
        assert_eq!(node.unwrap().name, "foo");
    }

    #[test]
    fn test_graph_add_edges() {
        let mut graph = ProgramGraph::new();
        let id1 = StableId::new("node_foo");
        let id2 = StableId::new("node_bar");

        let node1 = NodeData::new(
            id1.clone(),
            "foo",
            NodeKind::Function,
            SemanticRole::FunctionDef,
            Provenance::Unknown,
        );
        let node2 = NodeData::new(
            id2.clone(),
            "bar",
            NodeKind::Function,
            SemanticRole::FunctionDef,
            Provenance::Unknown,
        );

        graph.add_node(node1);
        graph.add_node(node2);

        let edge = EdgeData::new(EdgeKind::Calls, Provenance::Unknown);
        assert!(graph.add_edge(&id1, &id2, edge).is_some());
        assert_eq!(graph.edge_count(), 1);
    }

    #[test]
    fn test_query_by_name() {
        let mut graph = ProgramGraph::new();
        graph.add_node(create_test_node("foo"));
        graph.add_node(create_test_node("foobar"));
        graph.add_node(create_test_node("bar"));

        let results = graph.query_nodes_by_name("foo");
        assert_eq!(results.len(), 2);
    }

    #[test]
    fn test_get_callees() {
        let mut graph = ProgramGraph::new();
        let id1 = StableId::new("node_foo");
        let id2 = StableId::new("node_bar");

        let node1 = NodeData::new(
            id1.clone(),
            "foo",
            NodeKind::Function,
            SemanticRole::FunctionDef,
            Provenance::Unknown,
        );
        let node2 = NodeData::new(
            id2.clone(),
            "bar",
            NodeKind::Function,
            SemanticRole::FunctionDef,
            Provenance::Unknown,
        );

        graph.add_node(node1);
        graph.add_node(node2);

        let edge = EdgeData::new(EdgeKind::Calls, Provenance::Unknown);
        graph.add_edge(&id1, &id2, edge);

        let callees = graph.get_callees(&id1);
        assert_eq!(callees.len(), 1);
        assert_eq!(callees[0].name, "bar");
    }
}
