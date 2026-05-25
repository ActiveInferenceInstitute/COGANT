//! Translation rules and semantic mapping engine.
//!
//! This crate provides the abstraction for translating program structures
//! from one form to another, with pluggable rules and semantic mappings.

use cogant_core::{Confidence, NodeKind, SemanticRole};
use cogant_graph::{NodeData, ProgramGraph};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

/// Error type for translation operations.
#[derive(Error, Debug)]
pub enum TranslationError {
    #[error("Rule not found: {0}")]
    RuleNotFound(String),

    #[error("Mapping error: {0}")]
    MappingError(String),

    #[error("Confidence too low: required {required}, got {actual}")]
    ConfidenceTooLow { required: f32, actual: f32 },

    #[error("Type mismatch: expected {expected}, got {actual}")]
    TypeMismatch { expected: String, actual: String },

    #[error("Graph error: {0}")]
    GraphError(String),

    #[error("Invalid configuration: {0}")]
    InvalidConfig(String),
}

/// Configuration for translation behavior.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TranslationConfig {
    /// Minimum confidence threshold for including results
    pub min_confidence: f32,
    /// Whether to include uncertain results
    pub include_low_confidence: bool,
    /// Maximum recursion depth for transitive queries
    pub max_recursion_depth: usize,
    /// Language/framework version being translated
    pub language_version: String,
}

impl Default for TranslationConfig {
    fn default() -> Self {
        Self {
            min_confidence: 0.6,
            include_low_confidence: true,
            max_recursion_depth: 10,
            language_version: "unknown".to_string(),
        }
    }
}

/// A semantic mapping from one concept to another.
///
/// Maps source program entities to GNN semantic roles and node types.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SemanticMapping {
    /// Identifier for this mapping
    pub id: String,
    /// Source: (NodeKind, SemanticRole) pair
    pub source_kind: NodeKind,
    pub source_role: SemanticRole,
    /// Target: GNN semantic role
    pub target_role: SemanticRole,
    /// Confidence in this mapping
    pub confidence: Confidence,
    /// Rule conditions (optional)
    pub conditions: Vec<String>,
    /// Transformations to apply
    pub transformations: HashMap<String, String>,
}

impl SemanticMapping {
    /// Create a new semantic mapping.
    pub fn new(
        id: impl Into<String>,
        source_kind: NodeKind,
        source_role: SemanticRole,
        target_role: SemanticRole,
    ) -> Self {
        Self {
            id: id.into(),
            source_kind,
            source_role,
            target_role,
            confidence: Confidence::HIGH,
            conditions: Vec::new(),
            transformations: HashMap::new(),
        }
    }

    /// Add a condition for this mapping.
    pub fn with_condition(mut self, condition: impl Into<String>) -> Self {
        self.conditions.push(condition.into());
        self
    }

    /// Add a transformation.
    pub fn with_transformation(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.transformations.insert(key.into(), value.into());
        self
    }

    /// Check if this mapping applies to a node.
    pub fn applies_to(&self, node: &NodeData) -> bool {
        node.kind == self.source_kind && node.role == self.source_role
    }
}

/// Trait for translation rules.
///
/// A translation rule defines how to map source code structures to semantic entities
/// in the target representation.
pub trait TranslationRule: Send + Sync {
    /// Get the unique identifier for this rule.
    fn id(&self) -> &str;

    /// Get human-readable description.
    fn description(&self) -> &str;

    /// Check if this rule applies to the given input.
    fn matches(&self, node: &NodeData) -> bool;

    /// Apply the rule to produce output.
    fn apply(&self, node: &NodeData) -> Result<SemanticMapping, TranslationError>;

    /// Get the confidence level of this rule.
    fn confidence(&self) -> Confidence;
}

/// A collection of translation rules.
#[derive(Default)]
pub struct RuleSet {
    rules: HashMap<String, Box<dyn TranslationRule>>,
}

impl RuleSet {
    /// Create a new empty rule set.
    pub fn new() -> Self {
        Self::default()
    }

    /// Register a rule.
    pub fn register(&mut self, rule: Box<dyn TranslationRule>) {
        self.rules.insert(rule.id().to_string(), rule);
    }

    /// Get a rule by ID.
    pub fn get(&self, id: &str) -> Option<&dyn TranslationRule> {
        self.rules.get(id).map(|b| b.as_ref())
    }

    /// Get all rules that match a node.
    pub fn matching_rules(&self, node: &NodeData) -> Vec<&dyn TranslationRule> {
        self.rules
            .values()
            .filter(|rule| rule.matches(node))
            .map(|b| b.as_ref())
            .collect()
    }

    /// Get the count of registered rules.
    pub fn len(&self) -> usize {
        self.rules.len()
    }

    /// Check if empty.
    pub fn is_empty(&self) -> bool {
        self.rules.is_empty()
    }
}

/// Translation engine for applying rules to graphs.
pub struct TranslationEngine {
    rules: RuleSet,
    mappings: HashMap<String, SemanticMapping>,
    config: TranslationConfig,
}

impl TranslationEngine {
    /// Create a new translation engine with configuration.
    pub fn new(config: TranslationConfig) -> Self {
        Self {
            rules: RuleSet::new(),
            mappings: HashMap::new(),
            config,
        }
    }

    /// Create with default configuration.
    pub fn default_engine() -> Self {
        Self::new(TranslationConfig::default())
    }

    /// Register a translation rule.
    pub fn register_rule(&mut self, rule: Box<dyn TranslationRule>) {
        self.rules.register(rule);
    }

    /// Register a semantic mapping.
    pub fn register_mapping(&mut self, mapping: SemanticMapping) {
        self.mappings.insert(mapping.id.clone(), mapping);
    }

    /// Translate a single node.
    pub fn translate_node(&self, node: &NodeData) -> Result<SemanticRole, TranslationError> {
        // Try to find matching mappings
        for mapping in self.mappings.values() {
            if mapping.applies_to(node)
                && mapping
                    .confidence
                    .meets_threshold(self.config.min_confidence)
            {
                return Ok(mapping.target_role);
            }
        }

        // Try matching rules
        let matching = self.rules.matching_rules(node);
        if let Some(rule) = matching.first() {
            if rule
                .confidence()
                .meets_threshold(self.config.min_confidence)
            {
                let mapping = rule.apply(node)?;
                return Ok(mapping.target_role);
            }
        }

        // If no confident matches, use the node's existing role
        if self.config.include_low_confidence {
            Ok(node.role)
        } else {
            Err(TranslationError::MappingError(
                "No mapping found and low-confidence results excluded".to_string(),
            ))
        }
    }

    /// Translate an entire program graph.
    pub fn translate_graph(&self, graph: &ProgramGraph) -> Result<ProgramGraph, TranslationError> {
        let mut translated = ProgramGraph::new();

        // Translate all nodes
        for node in graph.nodes() {
            let target_role = self.translate_node(node)?;
            let mut new_node = node.clone();
            new_node.role = target_role;
            translated.add_node(new_node);
        }

        // Copy all edges (they remain the same)
        for (source, target, edge) in graph.edges() {
            translated.add_edge(&source.id, &target.id, edge.clone());
        }

        Ok(translated)
    }

    /// Get the underlying rule set.
    pub fn rules(&self) -> &RuleSet {
        &self.rules
    }

    /// Get the configuration.
    pub fn config(&self) -> &TranslationConfig {
        &self.config
    }

    /// Get the count of registered mappings.
    pub fn mapping_count(&self) -> usize {
        self.mappings.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct TestRule;

    impl TranslationRule for TestRule {
        fn id(&self) -> &str {
            "test_rule"
        }

        fn description(&self) -> &str {
            "A test rule"
        }

        fn matches(&self, _node: &NodeData) -> bool {
            true
        }

        fn apply(&self, node: &NodeData) -> Result<SemanticMapping, TranslationError> {
            Ok(SemanticMapping::new(
                "test_mapping",
                node.kind,
                node.role,
                SemanticRole::FunctionDef,
            ))
        }

        fn confidence(&self) -> Confidence {
            Confidence::HIGH
        }
    }

    #[test]
    fn test_rule_set() {
        let mut rules = RuleSet::new();
        rules.register(Box::new(TestRule));
        assert_eq!(rules.len(), 1);
        assert!(rules.get("test_rule").is_some());
    }

    #[test]
    fn test_semantic_mapping() {
        let mapping = SemanticMapping::new(
            "test",
            NodeKind::Function,
            SemanticRole::FunctionDef,
            SemanticRole::FunctionCall,
        );
        assert_eq!(mapping.id, "test");
        assert_eq!(mapping.source_kind, NodeKind::Function);
    }

    #[test]
    fn test_translation_config_default() {
        let config = TranslationConfig::default();
        assert_eq!(config.min_confidence, 0.6);
        assert!(config.include_low_confidence);
    }

    #[test]
    fn test_translation_engine() {
        let mut engine = TranslationEngine::default_engine();
        engine.register_rule(Box::new(TestRule));
        assert_eq!(engine.rules().len(), 1);
    }
}
