//! Core types for the COGANT translation engine.
//!
//! This crate provides foundational types used across all COGANT components:
//! - Stable identifiers for program entities
//! - Node and edge kind enumerations
//! - Semantic role classifications
//! - Confidence and provenance metadata

use serde::{Deserialize, Serialize};
use std::fmt;
use uuid::Uuid;

/// A stable identifier for a program entity that persists across transformations.
///
/// StableId combines a hash-based short ID with a UUID for collision resistance.
/// Used to track entities across the entire pipeline: source code → IR → Graph → GNN.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct StableId {
    /// Short hash-based identifier (e.g., "fn_8f2a1b")
    pub short_id: String,
    /// UUID for uniqueness across the entire system
    pub uuid: Uuid,
}

impl StableId {
    /// Create a new StableId with a given short identifier.
    pub fn new(short_id: impl Into<String>) -> Self {
        Self {
            short_id: short_id.into(),
            uuid: Uuid::new_v4(),
        }
    }

    /// Create a StableId from a short ID and UUID.
    pub fn with_uuid(short_id: impl Into<String>, uuid: Uuid) -> Self {
        Self {
            short_id: short_id.into(),
            uuid,
        }
    }
}

impl fmt::Display for StableId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}#{}", self.short_id, self.uuid)
    }
}

/// Semantic role of a node or edge in the program graph.
///
/// Defines the function or purpose of an entity within the code structure.
/// Used to classify entities for GNN training and semantic analysis.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum SemanticRole {
    /// Function or method definition
    FunctionDef,
    /// Function or method call
    FunctionCall,
    /// Variable definition or assignment
    VariableDef,
    /// Variable reference or use
    VariableUse,
    /// Control flow: if/while/for
    ControlFlow,
    /// Type definition or class definition
    TypeDef,
    /// Type reference or type annotation
    TypeRef,
    /// Data structure access (field, property, element)
    DataAccess,
    /// Error handling: try/catch/throw
    ErrorHandling,
    /// Module or namespace definition
    ModuleDef,
    /// Module or namespace import
    ModuleImport,
    /// Class method definition
    MethodDef,
    /// Class method invocation
    MethodCall,
    /// Abstract base or interface
    Interface,
    /// Implementation of interface
    Implementation,
    /// Inheritance relationship
    Inheritance,
    /// Polymorphic dispatch
    Polymorphism,
    /// Dependency injection point
    DependencyInject,
    /// Configuration parameter
    ConfigParam,
    /// Logging statement
    LoggingStmt,
    /// Performance-critical region
    PerfCritical,
    /// Security-critical region
    SecurityCritical,
    /// Test or verification code
    TestCode,
    /// Documentation or comment
    Documentation,
    /// Constant or literal value
    Constant,
    /// Annotation or decorator
    Annotation,
    /// Generic/template parameter
    GenericParam,
    /// Type constraint or bound
    TypeConstraint,
    /// Unknown or unclassified
    Unknown,
}

impl fmt::Display for SemanticRole {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            SemanticRole::FunctionDef => write!(f, "FunctionDef"),
            SemanticRole::FunctionCall => write!(f, "FunctionCall"),
            SemanticRole::VariableDef => write!(f, "VariableDef"),
            SemanticRole::VariableUse => write!(f, "VariableUse"),
            SemanticRole::ControlFlow => write!(f, "ControlFlow"),
            SemanticRole::TypeDef => write!(f, "TypeDef"),
            SemanticRole::TypeRef => write!(f, "TypeRef"),
            SemanticRole::DataAccess => write!(f, "DataAccess"),
            SemanticRole::ErrorHandling => write!(f, "ErrorHandling"),
            SemanticRole::ModuleDef => write!(f, "ModuleDef"),
            SemanticRole::ModuleImport => write!(f, "ModuleImport"),
            SemanticRole::MethodDef => write!(f, "MethodDef"),
            SemanticRole::MethodCall => write!(f, "MethodCall"),
            SemanticRole::Interface => write!(f, "Interface"),
            SemanticRole::Implementation => write!(f, "Implementation"),
            SemanticRole::Inheritance => write!(f, "Inheritance"),
            SemanticRole::Polymorphism => write!(f, "Polymorphism"),
            SemanticRole::DependencyInject => write!(f, "DependencyInject"),
            SemanticRole::ConfigParam => write!(f, "ConfigParam"),
            SemanticRole::LoggingStmt => write!(f, "LoggingStmt"),
            SemanticRole::PerfCritical => write!(f, "PerfCritical"),
            SemanticRole::SecurityCritical => write!(f, "SecurityCritical"),
            SemanticRole::TestCode => write!(f, "TestCode"),
            SemanticRole::Documentation => write!(f, "Documentation"),
            SemanticRole::Constant => write!(f, "Constant"),
            SemanticRole::Annotation => write!(f, "Annotation"),
            SemanticRole::GenericParam => write!(f, "GenericParam"),
            SemanticRole::TypeConstraint => write!(f, "TypeConstraint"),
            SemanticRole::Unknown => write!(f, "Unknown"),
        }
    }
}

/// Kind of node in the program graph.
///
/// Superset of Python `schemas/core.py` NodeKind plus Rust-specific variants.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum NodeKind {
    // -- Matches Python schemas/core.py --
    /// Repository root
    Repo,
    /// Module or namespace
    Module,
    /// Source file
    File,
    /// Class definition
    Class,
    /// Function definition
    Function,
    /// Method definition
    Method,
    /// Variable or binding
    Variable,
    /// API endpoint
    Endpoint,
    /// Event definition
    Event,
    /// Function/method parameter
    Parameter,
    /// Return value
    ReturnValue,
    /// Data structure
    DataStructure,
    /// Configuration node
    Configuration,
    /// Feature flag
    FeatureFlag,
    /// Test case or test suite
    Test,
    /// Assertion
    Assertion,
    /// Policy definition
    Policy,
    /// Action definition
    Action,
    // -- Rust-specific (kept for extensibility) --
    /// Control flow node (if/while/for)
    ControlFlowNode,
    /// Error handling node
    ErrorHandler,
    /// Constant value
    Constant,
    /// External library or dependency
    External,
    /// Documentation node
    Documentation,
    /// Unknown node type
    Unknown,
}

impl fmt::Display for NodeKind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            NodeKind::Repo => write!(f, "Repo"),
            NodeKind::Module => write!(f, "Module"),
            NodeKind::File => write!(f, "File"),
            NodeKind::Class => write!(f, "Class"),
            NodeKind::Function => write!(f, "Function"),
            NodeKind::Method => write!(f, "Method"),
            NodeKind::Variable => write!(f, "Variable"),
            NodeKind::Endpoint => write!(f, "Endpoint"),
            NodeKind::Event => write!(f, "Event"),
            NodeKind::Parameter => write!(f, "Parameter"),
            NodeKind::ReturnValue => write!(f, "ReturnValue"),
            NodeKind::DataStructure => write!(f, "DataStructure"),
            NodeKind::Configuration => write!(f, "Configuration"),
            NodeKind::FeatureFlag => write!(f, "FeatureFlag"),
            NodeKind::Test => write!(f, "Test"),
            NodeKind::Assertion => write!(f, "Assertion"),
            NodeKind::Policy => write!(f, "Policy"),
            NodeKind::Action => write!(f, "Action"),
            NodeKind::ControlFlowNode => write!(f, "ControlFlowNode"),
            NodeKind::ErrorHandler => write!(f, "ErrorHandler"),
            NodeKind::Constant => write!(f, "Constant"),
            NodeKind::External => write!(f, "External"),
            NodeKind::Documentation => write!(f, "Documentation"),
            NodeKind::Unknown => write!(f, "Unknown"),
        }
    }
}

/// Kind of edge connecting nodes in the program graph.
///
/// Superset of Python `schemas/core.py` EdgeKind plus Rust-specific variants.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EdgeKind {
    // -- Matches Python schemas/core.py --
    /// Containment relationship
    Contains,
    /// Import relationship
    Imports,
    /// Inheritance relationship
    Inherits,
    /// Interface implementation
    Implements,
    /// Depends on
    DependsOn,
    /// Reads from
    Reads,
    /// Writes to
    Writes,
    /// Return type relationship
    Returns,
    /// Direct function call
    Calls,
    /// Throws exception
    Throws,
    /// Catches exception
    Catches,
    /// Yields value
    Yields,
    /// Observes state
    Observes,
    /// Mutates state
    Mutates,
    /// Guards execution
    Guards,
    /// Triggers action
    Triggers,
    /// Evidence from static analysis
    EvidenceFromStatic,
    /// Evidence from dynamic analysis
    EvidenceFromDynamic,
    // -- Rust-specific (kept for extensibility) --
    /// Uses or references
    Uses,
    /// Defines or declares
    Defines,
    /// Type annotation or type reference
    HasType,
    /// Data flow dependency
    DataFlow,
    /// Control flow dependency
    ControlDependency,
    /// Module/namespace membership
    MemberOf,
    /// Generic/template instantiation
    Instantiates,
    /// Parameterization
    Parameterizes,
    /// Overrides
    Overrides,
    /// External reference
    ExternalRef,
    /// Configuration reference
    ConfigRef,
    /// Error flow
    ErrorFlow,
    /// Parameter passing
    Parameter,
    /// Unknown edge type
    Unknown,
}

impl fmt::Display for EdgeKind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            EdgeKind::Contains => write!(f, "Contains"),
            EdgeKind::Imports => write!(f, "Imports"),
            EdgeKind::Inherits => write!(f, "Inherits"),
            EdgeKind::Implements => write!(f, "Implements"),
            EdgeKind::DependsOn => write!(f, "DependsOn"),
            EdgeKind::Reads => write!(f, "Reads"),
            EdgeKind::Writes => write!(f, "Writes"),
            EdgeKind::Returns => write!(f, "Returns"),
            EdgeKind::Calls => write!(f, "Calls"),
            EdgeKind::Throws => write!(f, "Throws"),
            EdgeKind::Catches => write!(f, "Catches"),
            EdgeKind::Yields => write!(f, "Yields"),
            EdgeKind::Observes => write!(f, "Observes"),
            EdgeKind::Mutates => write!(f, "Mutates"),
            EdgeKind::Guards => write!(f, "Guards"),
            EdgeKind::Triggers => write!(f, "Triggers"),
            EdgeKind::EvidenceFromStatic => write!(f, "EvidenceFromStatic"),
            EdgeKind::EvidenceFromDynamic => write!(f, "EvidenceFromDynamic"),
            EdgeKind::Uses => write!(f, "Uses"),
            EdgeKind::Defines => write!(f, "Defines"),
            EdgeKind::HasType => write!(f, "HasType"),
            EdgeKind::DataFlow => write!(f, "DataFlow"),
            EdgeKind::ControlDependency => write!(f, "ControlDependency"),
            EdgeKind::MemberOf => write!(f, "MemberOf"),
            EdgeKind::Instantiates => write!(f, "Instantiates"),
            EdgeKind::Parameterizes => write!(f, "Parameterizes"),
            EdgeKind::Overrides => write!(f, "Overrides"),
            EdgeKind::ExternalRef => write!(f, "ExternalRef"),
            EdgeKind::ConfigRef => write!(f, "ConfigRef"),
            EdgeKind::ErrorFlow => write!(f, "ErrorFlow"),
            EdgeKind::Parameter => write!(f, "Parameter"),
            EdgeKind::Unknown => write!(f, "Unknown"),
        }
    }
}

/// Confidence level for a semantic assertion.
///
/// Used to track certainty of type inference, role assignment, and relationship discovery.
/// Values from 0.0 to 1.0, where:
/// - 1.0 = certain (explicit source code evidence)
/// - 0.7-0.99 = high (heuristic-based with strong signals)
/// - 0.4-0.7 = medium (multiple heuristics, some ambiguity)
/// - 0.0-0.4 = low (speculative or single weak signal)
#[derive(Debug, Clone, Copy, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(transparent)]
pub struct Confidence(f32);

impl Confidence {
    /// Certain: explicit source code evidence (confidence = 1.0)
    pub const CERTAIN: Self = Self(1.0);

    /// High confidence: heuristic-based with strong signals (confidence >= 0.8)
    pub const HIGH: Self = Self(0.85);

    /// Medium confidence: multiple heuristics with some ambiguity (confidence = 0.6)
    pub const MEDIUM: Self = Self(0.6);

    /// Low confidence: speculative or single weak signal (confidence = 0.3)
    pub const LOW: Self = Self(0.3);

    /// Create a confidence value from a floating-point number (0.0 to 1.0).
    pub fn new(value: f32) -> Result<Self, String> {
        if (0.0..=1.0).contains(&value) {
            Ok(Confidence(value))
        } else {
            Err(format!(
                "Confidence must be between 0.0 and 1.0, got {}",
                value
            ))
        }
    }

    /// Get the confidence as a float (0.0 to 1.0).
    pub fn value(&self) -> f32 {
        self.0
    }

    /// Check if this confidence meets or exceeds a threshold.
    pub fn meets_threshold(&self, threshold: f32) -> bool {
        self.0 >= threshold
    }
}

impl fmt::Display for Confidence {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{:.2}", self.0)
    }
}

impl Default for Confidence {
    fn default() -> Self {
        Confidence::MEDIUM
    }
}

/// Source of information for a semantic assertion.
///
/// Tracks provenance of inferred facts to enable transparency and debugging.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Provenance {
    /// Extracted directly from source code
    SourceCode {
        /// File path relative to repository root
        file: String,
        /// Line number (1-based)
        line: u32,
        /// Column number (1-based)
        col: u32,
    },
    /// Inferred by type system analysis
    TypeSystem { reason: String },
    /// Inferred by control flow analysis
    ControlFlow { reason: String },
    /// Inferred by data flow analysis
    DataFlow { reason: String },
    /// Inferred by heuristic rule
    Heuristic { rule_id: String },
    /// Generated by external tool (e.g., linter, formatter)
    External { tool: String, version: String },
    /// Aggregated from multiple sources
    Aggregated { sources: Vec<Box<Provenance>> },
    /// Unknown or not tracked
    Unknown,
}

impl fmt::Display for Provenance {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Provenance::SourceCode { file, line, col } => {
                write!(f, "{}:{}:{}", file, line, col)
            }
            Provenance::TypeSystem { reason } => write!(f, "TypeSystem({})", reason),
            Provenance::ControlFlow { reason } => write!(f, "ControlFlow({})", reason),
            Provenance::DataFlow { reason } => write!(f, "DataFlow({})", reason),
            Provenance::Heuristic { rule_id } => write!(f, "Heuristic({})", rule_id),
            Provenance::External { tool, version } => write!(f, "{}@{}", tool, version),
            Provenance::Aggregated { sources } => {
                write!(f, "Aggregated[{}]", sources.len())
            }
            Provenance::Unknown => write!(f, "Unknown"),
        }
    }
}

impl Provenance {
    /// Create a source code provenance.
    pub fn source_code(file: impl Into<String>, line: u32, col: u32) -> Self {
        Provenance::SourceCode {
            file: file.into(),
            line,
            col,
        }
    }

    /// Create a type system provenance.
    pub fn type_system(reason: impl Into<String>) -> Self {
        Provenance::TypeSystem {
            reason: reason.into(),
        }
    }

    /// Create a control flow provenance.
    pub fn control_flow(reason: impl Into<String>) -> Self {
        Provenance::ControlFlow {
            reason: reason.into(),
        }
    }

    /// Create a data flow provenance.
    pub fn data_flow(reason: impl Into<String>) -> Self {
        Provenance::DataFlow {
            reason: reason.into(),
        }
    }

    /// Create a heuristic provenance.
    pub fn heuristic(rule_id: impl Into<String>) -> Self {
        Provenance::Heuristic {
            rule_id: rule_id.into(),
        }
    }

    /// Create an external tool provenance.
    pub fn external(tool: impl Into<String>, version: impl Into<String>) -> Self {
        Provenance::External {
            tool: tool.into(),
            version: version.into(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_stable_id() {
        let id = StableId::new("fn_test");
        assert_eq!(id.short_id, "fn_test");
        assert!(!id.uuid.to_string().is_empty());
    }

    #[test]
    fn test_confidence() {
        assert_eq!(Confidence::CERTAIN.value(), 1.0);
        assert!(Confidence::HIGH.meets_threshold(0.8));
        assert!(!Confidence::LOW.meets_threshold(0.5));
    }

    #[test]
    fn test_confidence_bounds() {
        assert!(Confidence::new(0.5).is_ok());
        assert!(Confidence::new(-0.1).is_err());
        assert!(Confidence::new(1.5).is_err());
    }

    #[test]
    fn test_semantic_role_serialization() {
        let role = SemanticRole::FunctionDef;
        let json = serde_json::to_string(&role).unwrap();
        assert_eq!(json, "\"FUNCTION_DEF\"");
    }

    #[test]
    fn test_node_kind_serialization() {
        let kind = NodeKind::Function;
        let json = serde_json::to_string(&kind).unwrap();
        assert_eq!(json, "\"function\"");
    }

    #[test]
    fn test_edge_kind_serialization() {
        let kind = EdgeKind::Calls;
        let json = serde_json::to_string(&kind).unwrap();
        assert_eq!(json, "\"calls\"");
    }

    #[test]
    fn test_provenance_source_code() {
        let prov = Provenance::source_code("main.rs", 42, 10);
        assert_eq!(prov.to_string(), "main.rs:42:10");
    }
}
