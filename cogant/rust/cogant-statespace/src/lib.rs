//! State space and behavioral modeling.
//!
//! This crate provides types for representing program state, observations,
//! actions, and transitions for behavioral analysis and GNN training.

use cogant_core::{Provenance, StableId};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// A variable representing program state.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct StateVariable {
    /// Unique identifier
    pub id: StableId,
    /// Variable name
    pub name: String,
    /// Data type (as string, e.g., "i32", "String")
    pub type_name: String,
    /// Possible values (domain) if known
    pub domain: Option<Vec<String>>,
    /// Whether this variable is observable
    pub observable: bool,
}

impl StateVariable {
    /// Create a new state variable.
    pub fn new(id: StableId, name: impl Into<String>, type_name: impl Into<String>) -> Self {
        Self {
            id,
            name: name.into(),
            type_name: type_name.into(),
            domain: None,
            observable: true,
        }
    }

    /// Set the domain (possible values).
    pub fn with_domain(mut self, domain: Vec<String>) -> Self {
        self.domain = Some(domain);
        self
    }

    /// Mark as observable or not.
    pub fn with_observable(mut self, observable: bool) -> Self {
        self.observable = observable;
        self
    }
}

/// An observation of program state.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Observation {
    /// Which variable is being observed
    pub variable_id: StableId,
    /// Observed value (as string)
    pub value: String,
    /// Observation modality (how it was captured)
    pub modality: ObservationModality,
    /// When this observation occurred (step/timestamp)
    pub timestamp: u64,
    /// Confidence in this observation
    pub confidence: f32,
}

impl Observation {
    /// Create a new observation.
    pub fn new(
        variable_id: StableId,
        value: impl Into<String>,
        modality: ObservationModality,
        timestamp: u64,
    ) -> Self {
        Self {
            variable_id,
            value: value.into(),
            modality,
            timestamp,
            confidence: 1.0,
        }
    }

    /// Set confidence.
    pub fn with_confidence(mut self, confidence: f32) -> Self {
        self.confidence = confidence.clamp(0.0, 1.0);
        self
    }
}

/// How an observation was captured.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ObservationModality {
    /// Directly from source code analysis
    StaticAnalysis,
    /// From runtime execution trace
    DynamicTrace,
    /// From instrumentation/logging
    Instrumentation,
    /// From type system inference
    TypeInference,
    /// From static heuristics
    Heuristic,
    /// From external tool
    ExternalTool,
}

impl std::fmt::Display for ObservationModality {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ObservationModality::StaticAnalysis => write!(f, "StaticAnalysis"),
            ObservationModality::DynamicTrace => write!(f, "DynamicTrace"),
            ObservationModality::Instrumentation => write!(f, "Instrumentation"),
            ObservationModality::TypeInference => write!(f, "TypeInference"),
            ObservationModality::Heuristic => write!(f, "Heuristic"),
            ObservationModality::ExternalTool => write!(f, "ExternalTool"),
        }
    }
}

/// An action that can occur in the program.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Action {
    /// Unique identifier
    pub id: StableId,
    /// Action name (e.g., "function_call", "state_mutation")
    pub name: String,
    /// Parameters (key-value pairs)
    pub parameters: HashMap<String, String>,
    /// Possible outcomes (for non-deterministic actions)
    pub outcomes: Vec<String>,
}

impl Action {
    /// Create a new action.
    pub fn new(id: StableId, name: impl Into<String>) -> Self {
        Self {
            id,
            name: name.into(),
            parameters: HashMap::new(),
            outcomes: Vec::new(),
        }
    }

    /// Add a parameter.
    pub fn add_parameter(&mut self, key: impl Into<String>, value: impl Into<String>) {
        self.parameters.insert(key.into(), value.into());
    }

    /// Add a possible outcome.
    pub fn add_outcome(&mut self, outcome: impl Into<String>) {
        self.outcomes.push(outcome.into());
    }
}

/// A transition between states.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Transition {
    /// From state (represented as variable assignments)
    pub from_state: HashMap<StableId, String>,
    /// Action taken
    pub action: Action,
    /// To state (resulting variable assignments)
    pub to_state: HashMap<StableId, String>,
    /// Probability (0.0 to 1.0) if probabilistic
    pub probability: f32,
    /// Provenance of this transition
    pub provenance: Provenance,
}

impl Transition {
    /// Create a new transition.
    pub fn new(
        from_state: HashMap<StableId, String>,
        action: Action,
        to_state: HashMap<StableId, String>,
        provenance: Provenance,
    ) -> Self {
        Self {
            from_state,
            action,
            to_state,
            probability: 1.0,
            provenance,
        }
    }

    /// Set the probability.
    pub fn with_probability(mut self, probability: f32) -> Self {
        self.probability = probability.clamp(0.0, 1.0);
        self
    }
}

/// Complete state space model of a program.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StateSpaceModel {
    /// Name/identifier
    pub name: String,
    /// Description
    pub description: Option<String>,
    /// All state variables
    pub variables: HashMap<StableId, StateVariable>,
    /// All possible actions
    pub actions: HashMap<StableId, Action>,
    /// All transitions
    pub transitions: Vec<Transition>,
    /// Initial state
    pub initial_state: HashMap<StableId, String>,
    /// Goal/accepting states
    pub accepting_states: Vec<HashMap<StableId, String>>,
    /// All observations collected
    pub observations: Vec<Observation>,
}

impl StateSpaceModel {
    /// Create a new state space model.
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            description: None,
            variables: HashMap::new(),
            actions: HashMap::new(),
            transitions: Vec::new(),
            initial_state: HashMap::new(),
            accepting_states: Vec::new(),
            observations: Vec::new(),
        }
    }

    /// Set the description.
    pub fn with_description(mut self, description: impl Into<String>) -> Self {
        self.description = Some(description.into());
        self
    }

    /// Add a state variable.
    pub fn add_variable(&mut self, variable: StateVariable) {
        self.variables.insert(variable.id.clone(), variable);
    }

    /// Add an action.
    pub fn add_action(&mut self, action: Action) {
        self.actions.insert(action.id.clone(), action);
    }

    /// Add a transition.
    pub fn add_transition(&mut self, transition: Transition) {
        self.transitions.push(transition);
    }

    /// Add an observation.
    pub fn add_observation(&mut self, observation: Observation) {
        self.observations.push(observation);
    }

    /// Set the initial state.
    pub fn set_initial_state(&mut self, state: HashMap<StableId, String>) {
        self.initial_state = state;
    }

    /// Add an accepting state.
    pub fn add_accepting_state(&mut self, state: HashMap<StableId, String>) {
        self.accepting_states.push(state);
    }

    /// Get the number of states (cardinality of state space).
    pub fn state_cardinality(&self) -> usize {
        // Simplified: product of domain sizes
        self.variables
            .values()
            .map(|v| v.domain.as_ref().map(|d| d.len()).unwrap_or(2))
            .product()
    }

    /// Check if a state is accepting.
    pub fn is_accepting(&self, state: &HashMap<StableId, String>) -> bool {
        self.accepting_states.iter().any(|s| s == state)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_state_variable() {
        let var = StateVariable::new(StableId::new("var_x"), "x", "i32");
        assert_eq!(var.name, "x");
        assert_eq!(var.type_name, "i32");
        assert!(var.observable);
    }

    #[test]
    fn test_observation() {
        let obs = Observation::new(
            StableId::new("var_x"),
            "42",
            ObservationModality::StaticAnalysis,
            0,
        );
        assert_eq!(obs.value, "42");
        assert_eq!(obs.confidence, 1.0);
    }

    #[test]
    fn test_action() {
        let action = Action::new(StableId::new("action_call"), "function_call");
        assert_eq!(action.name, "function_call");
    }

    #[test]
    fn test_transition() {
        let action = Action::new(StableId::new("action_call"), "call");
        let from = HashMap::new();
        let to = HashMap::new();
        let trans = Transition::new(from, action, to, Provenance::Unknown);
        assert_eq!(trans.probability, 1.0);
    }

    #[test]
    fn test_state_space_model() {
        let mut model = StateSpaceModel::new("test_program");
        let var = StateVariable::new(StableId::new("var_x"), "x", "bool");
        model.add_variable(var);
        assert_eq!(model.variables.len(), 1);
    }
}
