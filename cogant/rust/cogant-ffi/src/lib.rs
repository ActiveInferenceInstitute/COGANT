#![allow(clippy::too_many_arguments, clippy::useless_conversion)]

//! Python FFI for COGANT using PyO3.
//!
//! This module provides a Python interface to COGANT's Rust components,
//! allowing the Python pipeline to leverage high-performance graph operations.

use cogant_core::{Confidence, EdgeKind, NodeKind, Provenance, SemanticRole, StableId};
use cogant_gnn::{format_json, format_markdown};
use cogant_graph::{EdgeData, NodeData, ProgramGraph};
use petgraph::algo::connected_components as petgraph_connected_components;
use petgraph::graph::UnGraph;
use pyo3::prelude::*;
use serde_json::json;
use std::collections::HashMap;

/// Python wrapper for StableId.
#[pyclass]
#[derive(Clone)]
pub struct PyStableId {
    pub inner: StableId,
}

#[pymethods]
impl PyStableId {
    #[new]
    pub fn new(short_id: String) -> Self {
        PyStableId {
            inner: StableId::new(short_id),
        }
    }

    pub fn __str__(&self) -> String {
        self.inner.to_string()
    }

    pub fn __repr__(&self) -> String {
        format!("StableId({})", self.inner)
    }
}

/// Python wrapper for Confidence.
#[pyclass]
pub struct PyConfidence {
    pub inner: Confidence,
}

#[pymethods]
impl PyConfidence {
    #[new]
    pub fn new(value: f32) -> PyResult<Self> {
        match Confidence::new(value) {
            Ok(conf) => Ok(PyConfidence { inner: conf }),
            Err(e) => Err(pyo3::exceptions::PyValueError::new_err(e)),
        }
    }

    pub fn value(&self) -> f32 {
        self.inner.value()
    }

    pub fn meets_threshold(&self, threshold: f32) -> bool {
        self.inner.meets_threshold(threshold)
    }

    pub fn __str__(&self) -> String {
        self.inner.to_string()
    }

    pub fn __float__(&self) -> f32 {
        self.inner.value()
    }
}

/// Python wrapper for NodeData.
#[pyclass]
pub struct PyNodeData {
    pub inner: NodeData,
}

#[pymethods]
impl PyNodeData {
    #[new]
    pub fn new(id: PyStableId, name: String, kind: String, role: String) -> PyResult<Self> {
        let kind = parse_node_kind(&kind)?;
        let role = parse_semantic_role(&role)?;

        Ok(PyNodeData {
            inner: NodeData::new(id.inner, name, kind, role, Provenance::Unknown),
        })
    }

    pub fn get_name(&self) -> String {
        self.inner.name.clone()
    }

    pub fn get_type(&self) -> Option<String> {
        self.inner.type_name.clone()
    }

    pub fn set_type(&mut self, type_name: String) {
        self.inner.type_name = Some(type_name);
    }

    pub fn get_confidence(&self) -> f32 {
        self.inner.confidence.value()
    }

    pub fn __str__(&self) -> String {
        format!("{}[{}]", self.inner.name, self.inner.kind)
    }
}

/// Python wrapper for ProgramGraph.
#[pyclass]
pub struct PyProgramGraph {
    pub inner: ProgramGraph,
    id_lookup: HashMap<String, StableId>,
}

impl Default for PyProgramGraph {
    fn default() -> Self {
        Self::new()
    }
}

#[pymethods]
impl PyProgramGraph {
    #[new]
    pub fn new() -> Self {
        PyProgramGraph {
            inner: ProgramGraph::new(),
            id_lookup: HashMap::new(),
        }
    }

    /// Add a node from an existing `PyNodeData` wrapper.
    ///
    /// Returns the internal graph index for the inserted node.
    pub fn add_node_data(&mut self, node: &PyNodeData) -> usize {
        let idx = self.inner.add_node(node.inner.clone());
        self.id_lookup
            .insert(node.inner.id.short_id.clone(), node.inner.id.clone());
        self.id_lookup
            .insert(node.inner.id.to_string(), node.inner.id.clone());
        idx.index()
    }

    /// Add a node from primitive fields (ergonomic entry point for Python).
    ///
    /// This mirrors the signature exposed to the Python pipeline and constructs
    /// a `NodeData` with source-code provenance. Returns the node's index.
    #[pyo3(signature = (kind, name, stable_id, file, language, line_start, line_end))]
    pub fn add_node(
        &mut self,
        kind: &str,
        name: &str,
        stable_id: &str,
        file: &str,
        language: &str,
        line_start: u32,
        line_end: u32,
    ) -> PyResult<usize> {
        let node_kind = parse_node_kind(kind)?;
        let role = default_role_for_kind(node_kind);
        let provenance = Provenance::source_code(file.to_string(), line_start, 1);
        let mut node = NodeData::new(
            StableId::new(stable_id),
            name.to_string(),
            node_kind,
            role,
            provenance,
        );
        node.add_attribute("language", language);
        node.add_attribute("line_start", line_start.to_string());
        node.add_attribute("line_end", line_end.to_string());
        let rust_id = node.id.clone();
        let idx = self.inner.add_node(node);
        self.id_lookup
            .insert(stable_id.to_string(), rust_id.clone());
        self.id_lookup.insert(rust_id.short_id.clone(), rust_id);
        Ok(idx.index())
    }

    /// Add an edge from primitive fields.
    ///
    /// The source and target IDs must be the stable IDs previously passed to
    /// `add_node`. Returns true when the edge was inserted.
    #[pyo3(signature = (source_id, target_id, kind, confidence = 0.75))]
    pub fn add_edge(
        &mut self,
        source_id: &str,
        target_id: &str,
        kind: &str,
        confidence: f32,
    ) -> PyResult<bool> {
        let edge_kind = parse_edge_kind(kind)?;
        let from = self
            .id_lookup
            .get(source_id)
            .cloned()
            .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err(source_id.to_string()))?;
        let to = self
            .id_lookup
            .get(target_id)
            .cloned()
            .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err(target_id.to_string()))?;
        let conf = Confidence::new(confidence).map_err(pyo3::exceptions::PyValueError::new_err)?;
        let edge = EdgeData::new(edge_kind, Provenance::Unknown).with_confidence(conf);
        Ok(self.inner.add_edge(&from, &to, edge).is_some())
    }

    pub fn node_count(&self) -> usize {
        self.inner.node_count()
    }

    pub fn edge_count(&self) -> usize {
        self.inner.edge_count()
    }

    pub fn query_by_name(&self, name: &str) -> Vec<String> {
        self.inner
            .query_nodes_by_name(name)
            .iter()
            .map(|n| n.name.clone())
            .collect()
    }

    pub fn query_by_kind(&self, kind: &str) -> PyResult<Vec<String>> {
        let node_kind = parse_node_kind(kind)?;
        Ok(self
            .inner
            .query_nodes_by_kind(node_kind)
            .iter()
            .map(|n| n.name.clone())
            .collect())
    }

    pub fn get_callees(&self, from_id: String) -> Vec<String> {
        let id = StableId::new(from_id);
        self.inner
            .get_callees(&id)
            .iter()
            .map(|n| n.name.clone())
            .collect()
    }

    pub fn get_callers(&self, to_id: String) -> Vec<String> {
        let id = StableId::new(to_id);
        self.inner
            .get_callers(&id)
            .iter()
            .map(|n| n.name.clone())
            .collect()
    }

    pub fn to_json(&self) -> PyResult<String> {
        let json = format_json(&self.inner, "graph");
        Ok(json.to_string())
    }

    pub fn to_markdown(&self, title: &str) -> String {
        format_markdown(&self.inner, title)
    }

    pub fn summary_json(&self) -> String {
        graph_summary_json_inner(&self.inner).to_string()
    }

    pub fn node_kind_counts_json(&self) -> String {
        let mut counts: HashMap<String, usize> = HashMap::new();
        for node in self.inner.nodes() {
            *counts.entry(node.kind.to_string()).or_insert(0) += 1;
        }
        json!(counts).to_string()
    }

    pub fn edge_kind_counts_json(&self) -> String {
        let mut counts: HashMap<String, usize> = HashMap::new();
        for (_, _, edge) in self.inner.edges() {
            *counts.entry(edge.kind.to_string()).or_insert(0) += 1;
        }
        json!(counts).to_string()
    }

    pub fn __str__(&self) -> String {
        format!(
            "ProgramGraph(nodes={}, edges={})",
            self.inner.node_count(),
            self.inner.edge_count()
        )
    }

    pub fn __len__(&self) -> usize {
        self.inner.node_count()
    }
}

/// Pick a sensible default `SemanticRole` for a given `NodeKind`.
///
/// Used by the primitive-argument `add_node` entry point so callers do not
/// have to specify a role explicitly.
fn default_role_for_kind(kind: NodeKind) -> SemanticRole {
    match kind {
        NodeKind::Function | NodeKind::Method => SemanticRole::FunctionDef,
        NodeKind::Class => SemanticRole::TypeDef,
        NodeKind::Variable | NodeKind::Parameter | NodeKind::ReturnValue => {
            SemanticRole::VariableDef
        }
        NodeKind::Module => SemanticRole::ModuleDef,
        NodeKind::File => SemanticRole::ModuleDef,
        NodeKind::Constant => SemanticRole::Constant,
        NodeKind::Test | NodeKind::Assertion => SemanticRole::TestCode,
        NodeKind::Documentation => SemanticRole::Documentation,
        NodeKind::Configuration | NodeKind::FeatureFlag => SemanticRole::ConfigParam,
        NodeKind::ErrorHandler => SemanticRole::ErrorHandling,
        NodeKind::ControlFlowNode => SemanticRole::ControlFlow,
        _ => SemanticRole::Unknown,
    }
}

/// Parse a node kind string to NodeKind enum.
fn parse_node_kind(kind: &str) -> PyResult<NodeKind> {
    match kind.to_lowercase().as_str() {
        "repo" => Ok(NodeKind::Repo),
        "module" => Ok(NodeKind::Module),
        "file" => Ok(NodeKind::File),
        "class" | "type" => Ok(NodeKind::Class),
        "function" => Ok(NodeKind::Function),
        "method" => Ok(NodeKind::Method),
        "variable" => Ok(NodeKind::Variable),
        "endpoint" => Ok(NodeKind::Endpoint),
        "event" => Ok(NodeKind::Event),
        "parameter" => Ok(NodeKind::Parameter),
        "return_value" => Ok(NodeKind::ReturnValue),
        "data_structure" | "datastructure" => Ok(NodeKind::DataStructure),
        "configuration" => Ok(NodeKind::Configuration),
        "feature_flag" => Ok(NodeKind::FeatureFlag),
        "test" => Ok(NodeKind::Test),
        "assertion" => Ok(NodeKind::Assertion),
        "policy" => Ok(NodeKind::Policy),
        "action" => Ok(NodeKind::Action),
        "control_flow" | "controlflow" => Ok(NodeKind::ControlFlowNode),
        "error_handler" | "errorhandler" => Ok(NodeKind::ErrorHandler),
        "constant" => Ok(NodeKind::Constant),
        "external" => Ok(NodeKind::External),
        "documentation" => Ok(NodeKind::Documentation),
        "unknown" => Ok(NodeKind::Unknown),
        _ => Err(pyo3::exceptions::PyValueError::new_err(format!(
            "Unknown node kind: {}",
            kind
        ))),
    }
}

/// Parse an edge kind string to EdgeKind enum.
fn parse_edge_kind(kind: &str) -> PyResult<EdgeKind> {
    match kind.to_lowercase().as_str() {
        "contains" => Ok(EdgeKind::Contains),
        "imports" => Ok(EdgeKind::Imports),
        "inherits" => Ok(EdgeKind::Inherits),
        "implements" => Ok(EdgeKind::Implements),
        "depends_on" | "dependson" => Ok(EdgeKind::DependsOn),
        "reads" => Ok(EdgeKind::Reads),
        "writes" => Ok(EdgeKind::Writes),
        "returns" => Ok(EdgeKind::Returns),
        "calls" => Ok(EdgeKind::Calls),
        "throws" => Ok(EdgeKind::Throws),
        "catches" => Ok(EdgeKind::Catches),
        "yields" => Ok(EdgeKind::Yields),
        "observes" => Ok(EdgeKind::Observes),
        "mutates" => Ok(EdgeKind::Mutates),
        "guards" => Ok(EdgeKind::Guards),
        "triggers" => Ok(EdgeKind::Triggers),
        "evidence_from_static" | "evidencefromstatic" => Ok(EdgeKind::EvidenceFromStatic),
        "evidence_from_dynamic" | "evidencefromdynamic" => Ok(EdgeKind::EvidenceFromDynamic),
        "uses" => Ok(EdgeKind::Uses),
        "defines" => Ok(EdgeKind::Defines),
        "has_type" | "hastype" => Ok(EdgeKind::HasType),
        "data_flow" | "dataflow" => Ok(EdgeKind::DataFlow),
        "control_dependency" | "controldependency" => Ok(EdgeKind::ControlDependency),
        "member_of" | "memberof" => Ok(EdgeKind::MemberOf),
        "parameter" => Ok(EdgeKind::Parameter),
        "unknown" => Ok(EdgeKind::Unknown),
        _ => Err(pyo3::exceptions::PyValueError::new_err(format!(
            "Unknown edge kind: {}",
            kind
        ))),
    }
}

/// Parse a semantic role string to SemanticRole enum.
fn parse_semantic_role(role: &str) -> PyResult<SemanticRole> {
    match role.to_lowercase().as_str() {
        "functiondef" => Ok(SemanticRole::FunctionDef),
        "functioncall" => Ok(SemanticRole::FunctionCall),
        "variabledef" => Ok(SemanticRole::VariableDef),
        "variableuse" => Ok(SemanticRole::VariableUse),
        "controlflow" => Ok(SemanticRole::ControlFlow),
        "typedef" => Ok(SemanticRole::TypeDef),
        "typeref" => Ok(SemanticRole::TypeRef),
        "dataaccess" => Ok(SemanticRole::DataAccess),
        "errorhandling" => Ok(SemanticRole::ErrorHandling),
        "moduledef" => Ok(SemanticRole::ModuleDef),
        "moduleimport" => Ok(SemanticRole::ModuleImport),
        "methoddef" => Ok(SemanticRole::MethodDef),
        "methodcall" => Ok(SemanticRole::MethodCall),
        "interface" => Ok(SemanticRole::Interface),
        "implementation" => Ok(SemanticRole::Implementation),
        "inheritance" => Ok(SemanticRole::Inheritance),
        "polymorphism" => Ok(SemanticRole::Polymorphism),
        "dependencyinject" => Ok(SemanticRole::DependencyInject),
        "configparam" => Ok(SemanticRole::ConfigParam),
        "loggingstmt" => Ok(SemanticRole::LoggingStmt),
        "perfcritical" => Ok(SemanticRole::PerfCritical),
        "securitycritical" => Ok(SemanticRole::SecurityCritical),
        "testcode" => Ok(SemanticRole::TestCode),
        "documentation" => Ok(SemanticRole::Documentation),
        "constant" => Ok(SemanticRole::Constant),
        "annotation" => Ok(SemanticRole::Annotation),
        "genericparam" => Ok(SemanticRole::GenericParam),
        "typeconstraint" => Ok(SemanticRole::TypeConstraint),
        "unknown" => Ok(SemanticRole::Unknown),
        _ => Err(pyo3::exceptions::PyValueError::new_err(format!(
            "Unknown semantic role: {}",
            role
        ))),
    }
}

/// Compute connected components of an undirected graph.
///
/// Given a list of node IDs and a list of (source, target) edge pairs, returns
/// a list of components where each component is a list of node IDs that are
/// reachable from each other.
///
/// This is the Rust hot path replacing the Python BFS in
/// ``ProgramGraphBuilder.get_connected_components()``. Enable it by setting
/// the environment variable ``COGANT_USE_RUST=1``.
///
/// Complexity: O(V + E) using petgraph's union-find.
#[pyfunction]
pub fn connected_components(nodes: Vec<String>, edges: Vec<(String, String)>) -> Vec<Vec<String>> {
    if nodes.is_empty() {
        return Vec::new();
    }

    // Map node IDs to petgraph NodeIndex.
    let mut node_index: std::collections::HashMap<&str, petgraph::graph::NodeIndex> =
        std::collections::HashMap::with_capacity(nodes.len());
    let mut graph: UnGraph<usize, ()> = UnGraph::with_capacity(nodes.len(), edges.len());

    for (i, node_id) in nodes.iter().enumerate() {
        let idx = graph.add_node(i);
        node_index.insert(node_id.as_str(), idx);
    }

    for (src, dst) in &edges {
        if let (Some(&a), Some(&b)) = (node_index.get(src.as_str()), node_index.get(dst.as_str())) {
            // petgraph's UnGraph deduplicates automatically via the adjacency
            // representation; adding parallel edges is harmless for BFS/union-find.
            graph.add_edge(a, b, ());
        }
    }

    // Use petgraph's union-find to assign each node to a component label.
    let num_components = petgraph_connected_components(&graph);
    if num_components == 0 {
        return Vec::new();
    }

    // Walk nodes in petgraph order to collect component membership.
    // petgraph doesn't expose the component map directly from
    // `connected_components`, so we run a manual BFS to group them — this
    // keeps the result order deterministic (same as the Python BFS).
    let n = nodes.len();
    let mut visited = vec![false; n];
    let mut components: Vec<Vec<String>> = Vec::with_capacity(num_components);

    // Build an adjacency list indexed by our 0..n positions.
    let mut adj: Vec<Vec<usize>> = vec![Vec::new(); n];
    for (src, dst) in &edges {
        if let (Some(&a), Some(&b)) = (node_index.get(src.as_str()), node_index.get(dst.as_str())) {
            let ai = a.index();
            let bi = b.index();
            adj[ai].push(bi);
            adj[bi].push(ai);
        }
    }

    for (i, node_id) in nodes.iter().enumerate() {
        if visited[i] {
            continue;
        }
        // BFS from node i.
        let mut component: Vec<String> = Vec::new();
        let mut queue: std::collections::VecDeque<usize> = std::collections::VecDeque::new();
        queue.push_back(i);
        visited[i] = true;
        while let Some(cur) = queue.pop_front() {
            component.push(nodes[cur].clone());
            for &nb in &adj[cur] {
                if !visited[nb] {
                    visited[nb] = true;
                    queue.push_back(nb);
                }
            }
        }
        // Suppress unused warning: node_id is the canonical label for i.
        let _ = node_id;
        components.push(component);
    }

    components
}

fn graph_summary_json_inner(graph: &ProgramGraph) -> serde_json::Value {
    let node_count = graph.node_count();
    let edge_count = graph.edge_count();
    let possible_edges = node_count.saturating_mul(node_count.saturating_sub(1));
    let density = if possible_edges == 0 {
        0.0
    } else {
        edge_count as f64 / possible_edges as f64
    };
    json!({
        "node_count": node_count,
        "edge_count": edge_count,
        "density": density,
        "backend": "rust",
    })
}

#[pyfunction]
pub fn graph_summary_json(graph: &PyProgramGraph) -> String {
    graph_summary_json_inner(&graph.inner).to_string()
}

#[pyfunction]
pub fn translation_rule_predicates_json() -> String {
    json!({
        "rule_count": 22,
        "rules": [
            "observation", "action", "mutating_subsystem", "orchestrator",
            "preference", "constraint", "policy", "context", "parameter",
            "state_machine", "endpoint", "configuration", "feature_flag",
            "event", "test", "assertion", "data_structure", "external_service",
            "cache", "rate_limiter", "security_guard", "error_handler"
        ],
        "authoritative_backend": "python",
        "rust_parity_scope": "predicate-name metadata and deterministic summaries"
    })
    .to_string()
}

#[pyfunction]
pub fn compile_matrix_shapes_json(n_states: usize, n_obs: usize, n_actions: usize) -> String {
    json!({
        "A": [n_obs, n_states],
        "B": [n_states, n_states, n_actions],
        "C": [n_obs],
        "D": [n_states],
        "backend": "rust",
    })
    .to_string()
}

#[pyfunction]
pub fn format_gnn_json(graph: &PyProgramGraph, title: &str) -> String {
    format_json(&graph.inner, title).to_string()
}

#[pyfunction]
pub fn format_gnn_markdown(graph: &PyProgramGraph, title: &str) -> String {
    format_markdown(&graph.inner, title)
}

#[pyfunction]
pub fn write_artifact_atomic(path: String, contents: Vec<u8>) -> PyResult<()> {
    use std::fs;
    use std::io::Write;
    let final_path = std::path::PathBuf::from(path);
    let parent = final_path
        .parent()
        .map(std::path::Path::to_path_buf)
        .unwrap_or_else(|| std::path::PathBuf::from("."));
    fs::create_dir_all(&parent)?;
    let tmp_path = final_path.with_extension("tmp");
    {
        let mut file = fs::File::create(&tmp_path)?;
        file.write_all(&contents)?;
        file.sync_all()?;
    }
    fs::rename(tmp_path, final_path)?;
    Ok(())
}

#[pyfunction]
pub fn summarize_trace_events_json(events_json: &str) -> PyResult<String> {
    let value: serde_json::Value = serde_json::from_str(events_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    let events = value
        .as_array()
        .ok_or_else(|| pyo3::exceptions::PyValueError::new_err("expected JSON list"))?;
    let mut counts: HashMap<String, usize> = HashMap::new();
    for event in events {
        let kind = event
            .get("event_type")
            .or_else(|| event.get("type"))
            .and_then(serde_json::Value::as_str)
            .unwrap_or("unknown");
        *counts.entry(kind.to_string()).or_insert(0) += 1;
    }
    Ok(json!({
        "event_count": events.len(),
        "event_type_counts": counts,
        "backend": "rust",
    })
    .to_string())
}

/// Get COGANT version.
#[pyfunction]
pub fn get_version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

/// Create a test program graph for demonstration.
#[pyfunction]
pub fn create_example_graph() -> PyProgramGraph {
    let mut graph = ProgramGraph::new();

    // Create some example nodes
    let node1 = NodeData::new(
        StableId::new("fn_main"),
        "main",
        NodeKind::Function,
        SemanticRole::FunctionDef,
        Provenance::Unknown,
    );
    let node2 = NodeData::new(
        StableId::new("fn_helper"),
        "helper",
        NodeKind::Function,
        SemanticRole::FunctionDef,
        Provenance::Unknown,
    );
    let node3 = NodeData::new(
        StableId::new("var_x"),
        "x",
        NodeKind::Variable,
        SemanticRole::VariableDef,
        Provenance::Unknown,
    );

    graph.add_node(node1.clone());
    graph.add_node(node2.clone());
    graph.add_node(node3.clone());

    // Add some edges
    let edge1 = EdgeData::new(EdgeKind::Calls, Provenance::Unknown);
    graph.add_edge(&node1.id, &node2.id, edge1);

    let edge2 = EdgeData::new(EdgeKind::Uses, Provenance::Unknown);
    graph.add_edge(&node1.id, &node3.id, edge2);

    let mut id_lookup = HashMap::new();
    for node in [&node1, &node2, &node3] {
        id_lookup.insert(node.id.short_id.clone(), node.id.clone());
        id_lookup.insert(node.id.to_string(), node.id.clone());
    }

    PyProgramGraph {
        inner: graph,
        id_lookup,
    }
}

/// PyO3 module definition.
///
/// The module is named `_rust` so it can be imported from Python as
/// `cogant._rust`, matching the maturin `module-name` setting.
#[pymodule]
#[pyo3(name = "_rust")]
pub fn cogant_rust_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(get_version, m)?)?;
    m.add_function(wrap_pyfunction!(create_example_graph, m)?)?;
    m.add_function(wrap_pyfunction!(connected_components, m)?)?;
    m.add_function(wrap_pyfunction!(graph_summary_json, m)?)?;
    m.add_function(wrap_pyfunction!(translation_rule_predicates_json, m)?)?;
    m.add_function(wrap_pyfunction!(compile_matrix_shapes_json, m)?)?;
    m.add_function(wrap_pyfunction!(format_gnn_json, m)?)?;
    m.add_function(wrap_pyfunction!(format_gnn_markdown, m)?)?;
    m.add_function(wrap_pyfunction!(write_artifact_atomic, m)?)?;
    m.add_function(wrap_pyfunction!(summarize_trace_events_json, m)?)?;

    m.add_class::<PyStableId>()?;
    m.add_class::<PyConfidence>()?;
    m.add_class::<PyNodeData>()?;
    m.add_class::<PyProgramGraph>()?;

    // Module docstring
    m.add(
        "__doc__",
        "COGANT: Codebase-to-GNN Translation Engine\n\n\
         High-performance Rust backend for program graph analysis and GNN export.",
    )?;

    Ok(())
}
