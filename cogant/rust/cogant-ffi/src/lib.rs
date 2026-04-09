//! Python FFI for COGANT using PyO3.
//!
//! This module provides a Python interface to COGANT's Rust components,
//! allowing the Python pipeline to leverage high-performance graph operations.

use cogant_core::{Confidence, EdgeKind, NodeKind, Provenance, SemanticRole, StableId};
use cogant_graph::{EdgeData, NodeData, ProgramGraph};
use cogant_gnn::{format_json, format_markdown};
use pyo3::prelude::*;

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
    pub fn new(
        id: PyStableId,
        name: String,
        kind: String,
        role: String,
    ) -> PyResult<Self> {
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
}

#[pymethods]
impl PyProgramGraph {
    #[new]
    pub fn new() -> Self {
        PyProgramGraph {
            inner: ProgramGraph::new(),
        }
    }

    /// Add a node from an existing `PyNodeData` wrapper.
    ///
    /// Returns the internal graph index for the inserted node.
    pub fn add_node_data(&mut self, node: &PyNodeData) -> usize {
        let idx = self.inner.add_node(node.inner.clone());
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
        let idx = self.inner.add_node(node);
        Ok(idx.index())
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

    PyProgramGraph { inner: graph }
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
