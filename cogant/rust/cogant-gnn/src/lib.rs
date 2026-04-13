//! GNN export and formatting.
//!
//! "GNN" in COGANT refers to the Active Inference Institute's Generalized
//! Notation Notation (https://github.com/ActiveInferenceInstitute/GeneralizedNotationNotation),
//! a structured notation for Active Inference state-space and process models —
//! NOT graph neural networks. This crate provides functionality for exporting
//! program graphs into that notation.

use cogant_core::{EdgeKind, NodeKind, SemanticRole};
use cogant_graph::{EdgeData, NodeData, ProgramGraph};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::HashMap;

/// Sections of a GNN-formatted document.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum GnnSection {
    /// Graph structure (nodes and edges)
    Graph,
    /// Node features
    NodeFeatures,
    /// Edge features
    EdgeFeatures,
    /// Graph statistics
    Statistics,
    /// Semantic roles mapping
    SemanticRoles,
    /// Confidence scores
    Confidence,
    /// Provenance information
    Provenance,
    /// Type information
    Types,
    /// Metadata
    Metadata,
}

impl std::fmt::Display for GnnSection {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            GnnSection::Graph => write!(f, "Graph"),
            GnnSection::NodeFeatures => write!(f, "NodeFeatures"),
            GnnSection::EdgeFeatures => write!(f, "EdgeFeatures"),
            GnnSection::Statistics => write!(f, "Statistics"),
            GnnSection::SemanticRoles => write!(f, "SemanticRoles"),
            GnnSection::Confidence => write!(f, "Confidence"),
            GnnSection::Provenance => write!(f, "Provenance"),
            GnnSection::Types => write!(f, "Types"),
            GnnSection::Metadata => write!(f, "Metadata"),
        }
    }
}

/// A bundle of GNN-formatted data.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GnnBundle {
    /// Bundle identifier
    pub id: String,
    /// Name
    pub name: String,
    /// Description
    pub description: Option<String>,
    /// Sections included
    pub sections: Vec<GnnSection>,
    /// Raw GNN data (format-specific)
    pub data: Value,
    /// Metadata
    pub metadata: HashMap<String, String>,
}

impl GnnBundle {
    /// Create a new GNN bundle.
    pub fn new(id: impl Into<String>, name: impl Into<String>) -> Self {
        Self {
            id: id.into(),
            name: name.into(),
            description: None,
            sections: Vec::new(),
            data: json!({}),
            metadata: HashMap::new(),
        }
    }

    /// Set the description.
    pub fn with_description(mut self, description: impl Into<String>) -> Self {
        self.description = Some(description.into());
        self
    }

    /// Add a section.
    pub fn with_section(mut self, section: GnnSection) -> Self {
        if !self.sections.contains(&section) {
            self.sections.push(section);
        }
        self
    }

    /// Set multiple sections.
    pub fn with_sections(mut self, sections: Vec<GnnSection>) -> Self {
        self.sections = sections;
        self
    }

    /// Add metadata.
    pub fn add_metadata(&mut self, key: impl Into<String>, value: impl Into<String>) {
        self.metadata.insert(key.into(), value.into());
    }
}

/// Format a program graph as GNN in Markdown format.
pub fn format_markdown(graph: &ProgramGraph, title: &str) -> String {
    let mut output = String::new();

    // Header
    output.push_str(&format!("# {}\n\n", title));
    output.push_str("Generalized Notation Notation (Active Inference) representation\n\n");

    // Statistics
    output.push_str("## Statistics\n\n");
    output.push_str(&format!("- **Nodes**: {}\n", graph.node_count()));
    output.push_str(&format!("- **Edges**: {}\n", graph.edge_count()));
    output.push_str("\n");

    // Nodes
    output.push_str("## Nodes\n\n");
    output.push_str("| ID | Name | Kind | Role | Type | Confidence |\n");
    output.push_str("|----|----|----|----|----|----|----|\n");

    for node in graph.nodes() {
        let type_str = node.type_name.as_deref().unwrap_or("-");
        output.push_str(&format!(
            "| {} | {} | {} | {} | {} | {:.2} |\n",
            node.id.short_id,
            node.name,
            node.kind,
            node.role,
            type_str,
            node.confidence.value()
        ));
    }
    output.push('\n');

    // Edges
    output.push_str("## Edges\n\n");
    output.push_str("| From | To | Kind | Confidence | Label |\n");
    output.push_str("|-----|----|----|----|----|----|\n");

    for (source, target, edge) in graph.edges() {
        let label = edge.label.as_deref().unwrap_or("-");
        output.push_str(&format!(
            "| {} | {} | {} | {:.2} | {} |\n",
            source.id.short_id, target.id.short_id, edge.kind, edge.confidence.value(), label
        ));
    }
    output.push('\n');

    // Node Features
    output.push_str("## Node Features\n\n");
    output.push_str("```json\n");
    let node_features: Vec<_> = graph
        .nodes()
        .map(|n| {
            json!({
                "id": n.id.short_id,
                "name": n.name,
                "kind": n.kind.to_string(),
                "role": n.role.to_string(),
                "type": n.type_name,
                "confidence": n.confidence.value(),
                "attributes": n.attributes,
            })
        })
        .collect();
    output.push_str(&serde_json::to_string_pretty(&node_features).unwrap_or_default());
    output.push_str("\n```\n\n");

    // Edge Features
    output.push_str("## Edge Features\n\n");
    output.push_str("```json\n");
    let edge_features: Vec<_> = graph
        .edges()
        .iter()
        .map(|(src, tgt, e)| {
            json!({
                "source": src.id.short_id,
                "target": tgt.id.short_id,
                "kind": e.kind.to_string(),
                "confidence": e.confidence.value(),
                "label": e.label,
                "attributes": e.attributes,
            })
        })
        .collect();
    output.push_str(&serde_json::to_string_pretty(&edge_features).unwrap_or_default());
    output.push_str("\n```\n\n");

    output
}

/// Format a program graph as GNN in JSON format.
pub fn format_json(graph: &ProgramGraph, title: &str) -> Value {
    let nodes: Vec<Value> = graph
        .nodes()
        .map(|n| {
            json!({
                "id": n.id.uuid.to_string(),
                "short_id": n.id.short_id,
                "name": n.name,
                "kind": n.kind.to_string(),
                "role": n.role.to_string(),
                "type_name": n.type_name,
                "confidence": n.confidence.value(),
                "attributes": n.attributes,
                "documentation": n.documentation,
            })
        })
        .collect();

    let edges: Vec<Value> = graph
        .edges()
        .iter()
        .map(|(src, tgt, e)| {
            json!({
                "source": src.id.uuid.to_string(),
                "target": tgt.id.uuid.to_string(),
                "kind": e.kind.to_string(),
                "confidence": e.confidence.value(),
                "label": e.label,
                "attributes": e.attributes,
            })
        })
        .collect();

    let mut node_kinds = HashMap::new();
    for node in graph.nodes() {
        *node_kinds.entry(node.kind.to_string()).or_insert(0) += 1;
    }

    let mut edge_kinds = HashMap::new();
    for (_, _, edge) in graph.edges() {
        *edge_kinds.entry(edge.kind.to_string()).or_insert(0) += 1;
    }

    json!({
        "title": title,
        "statistics": {
            "nodes": graph.node_count(),
            "edges": graph.edge_count(),
            "node_kinds": node_kinds,
            "edge_kinds": edge_kinds,
        },
        "nodes": nodes,
        "edges": edges,
    })
}

/// Convert a NodeKind to a GNN node type string.
pub fn node_kind_to_gnn_type(kind: NodeKind) -> &'static str {
    match kind {
        NodeKind::Repo => "repo",
        NodeKind::Module => "module",
        NodeKind::File => "file",
        NodeKind::Class => "class",
        NodeKind::Function => "function",
        NodeKind::Method => "method",
        NodeKind::Variable => "variable",
        NodeKind::Endpoint => "endpoint",
        NodeKind::Event => "event",
        NodeKind::Parameter => "parameter",
        NodeKind::ReturnValue => "return_value",
        NodeKind::DataStructure => "data_structure",
        NodeKind::Configuration => "configuration",
        NodeKind::FeatureFlag => "feature_flag",
        NodeKind::Test => "test",
        NodeKind::Assertion => "assertion",
        NodeKind::Policy => "policy",
        NodeKind::Action => "action",
        NodeKind::ControlFlowNode => "control_flow",
        NodeKind::ErrorHandler => "error_handler",
        NodeKind::Constant => "constant",
        NodeKind::External => "external",
        NodeKind::Documentation => "documentation",
        NodeKind::Unknown => "unknown",
    }
}

/// Convert an EdgeKind to a GNN edge type string.
pub fn edge_kind_to_gnn_type(kind: EdgeKind) -> &'static str {
    match kind {
        // Python-aligned edge kinds
        EdgeKind::Contains => "contains",
        EdgeKind::Imports => "imports",
        EdgeKind::Inherits => "inherits",
        EdgeKind::Implements => "implements",
        EdgeKind::DependsOn => "depends_on",
        EdgeKind::Reads => "reads",
        EdgeKind::Writes => "writes",
        EdgeKind::Returns => "returns",
        EdgeKind::Calls => "calls",
        EdgeKind::Throws => "throws",
        EdgeKind::Catches => "catches",
        EdgeKind::Yields => "yields",
        EdgeKind::Observes => "observes",
        EdgeKind::Mutates => "mutates",
        EdgeKind::Guards => "guards",
        EdgeKind::Triggers => "triggers",
        EdgeKind::EvidenceFromStatic => "evidence_from_static",
        EdgeKind::EvidenceFromDynamic => "evidence_from_dynamic",
        // Rust-specific edge kinds
        EdgeKind::Uses => "uses",
        EdgeKind::Defines => "defines",
        EdgeKind::HasType => "has_type",
        EdgeKind::DataFlow => "data_flow",
        EdgeKind::ControlDependency => "control_dependency",
        EdgeKind::MemberOf => "member_of",
        EdgeKind::Instantiates => "instantiates",
        EdgeKind::Parameterizes => "parameterizes",
        EdgeKind::Overrides => "overrides",
        EdgeKind::ExternalRef => "external_ref",
        EdgeKind::ConfigRef => "config_ref",
        EdgeKind::ErrorFlow => "error_flow",
        EdgeKind::Parameter => "parameter",
        EdgeKind::Unknown => "unknown",
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use cogant_core::{Confidence, NodeKind, Provenance, SemanticRole, StableId};
    use cogant_graph::{EdgeData, NodeData};

    fn create_test_graph() -> ProgramGraph {
        let mut graph = ProgramGraph::new();

        let node1 = NodeData::new(
            StableId::new("fn_test1"),
            "test_func1",
            NodeKind::Function,
            SemanticRole::FunctionDef,
            Provenance::Unknown,
        );
        let node2 = NodeData::new(
            StableId::new("fn_test2"),
            "test_func2",
            NodeKind::Function,
            SemanticRole::FunctionDef,
            Provenance::Unknown,
        );

        graph.add_node(node1.clone());
        graph.add_node(node2.clone());

        let edge = EdgeData::new(EdgeKind::Calls, Provenance::Unknown);
        graph.add_edge(&node1.id, &node2.id, edge);

        graph
    }

    #[test]
    fn test_format_json() {
        let graph = create_test_graph();
        let json = format_json(&graph, "test");
        assert_eq!(json["title"], "test");
        assert_eq!(json["statistics"]["nodes"], 2);
        assert_eq!(json["statistics"]["edges"], 1);
    }

    #[test]
    fn test_format_markdown() {
        let graph = create_test_graph();
        let md = format_markdown(&graph, "Test Graph");
        assert!(md.contains("Test Graph"));
        assert!(md.contains("Nodes"));
        assert!(md.contains("Edges"));
    }

    #[test]
    fn test_gnn_bundle() {
        let bundle = GnnBundle::new("bundle1", "test_bundle");
        assert_eq!(bundle.id, "bundle1");
        assert_eq!(bundle.name, "test_bundle");
    }

    #[test]
    fn test_node_kind_to_gnn_type() {
        assert_eq!(node_kind_to_gnn_type(NodeKind::Function), "function");
        assert_eq!(node_kind_to_gnn_type(NodeKind::Variable), "variable");
        assert_eq!(node_kind_to_gnn_type(NodeKind::Unknown), "unknown");
    }

    #[test]
    fn test_edge_kind_to_gnn_type() {
        assert_eq!(edge_kind_to_gnn_type(EdgeKind::Calls), "calls");
        assert_eq!(edge_kind_to_gnn_type(EdgeKind::Uses), "uses");
        assert_eq!(edge_kind_to_gnn_type(EdgeKind::Unknown), "unknown");
    }
}
