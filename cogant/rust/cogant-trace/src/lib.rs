//! Execution trace collection and management.
//!
//! Provides types for recording program execution traces, including
//! function calls, state changes, and timing information.

use cogant_core::StableId;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::SystemTime;

/// A single event in an execution trace.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TraceEvent {
    /// Function entry event
    FunctionEntry {
        /// Function identifier
        function_id: StableId,
        /// Function name
        function_name: String,
        /// Timestamp of entry
        timestamp: u64,
        /// Call arguments (parameter names -> values)
        arguments: HashMap<String, String>,
        /// Call stack depth
        depth: u32,
    },
    /// Function exit event
    FunctionExit {
        /// Function identifier
        function_id: StableId,
        /// Timestamp of exit
        timestamp: u64,
        /// Return value (if any)
        return_value: Option<String>,
        /// Elapsed time in microseconds
        elapsed_us: u64,
    },
    /// State variable change
    StateChange {
        /// Variable identifier
        variable_id: StableId,
        /// Variable name
        variable_name: String,
        /// Previous value
        previous_value: Option<String>,
        /// New value
        new_value: String,
        /// Timestamp of change
        timestamp: u64,
    },
    /// Branching decision (if/match)
    Branch {
        /// Condition that was evaluated
        condition: String,
        /// Which branch was taken
        taken_branch: String,
        /// Timestamp
        timestamp: u64,
    },
    /// Exception or error event
    Exception {
        /// Exception type
        exception_type: String,
        /// Exception message
        message: String,
        /// Stack trace
        stack_trace: Vec<String>,
        /// Timestamp
        timestamp: u64,
    },
    /// Logging event
    Log {
        /// Log level (DEBUG, INFO, WARN, ERROR)
        level: String,
        /// Log message
        message: String,
        /// Timestamp
        timestamp: u64,
    },
    /// Synchronization event (lock, wait, etc.)
    Synchronization {
        /// Type of synchronization
        sync_type: String,
        /// Identifier of the synchronization object
        object_id: String,
        /// What happened (acquire, release, wait, etc.)
        action: String,
        /// Timestamp
        timestamp: u64,
    },
    /// Generic event
    Custom {
        /// Event type identifier
        event_type: String,
        /// Event data
        data: HashMap<String, String>,
        /// Timestamp
        timestamp: u64,
    },
}

impl TraceEvent {
    /// Get the timestamp of this event.
    pub fn timestamp(&self) -> u64 {
        match self {
            TraceEvent::FunctionEntry { timestamp, .. } => *timestamp,
            TraceEvent::FunctionExit { timestamp, .. } => *timestamp,
            TraceEvent::StateChange { timestamp, .. } => *timestamp,
            TraceEvent::Branch { timestamp, .. } => *timestamp,
            TraceEvent::Exception { timestamp, .. } => *timestamp,
            TraceEvent::Log { timestamp, .. } => *timestamp,
            TraceEvent::Synchronization { timestamp, .. } => *timestamp,
            TraceEvent::Custom { timestamp, .. } => *timestamp,
        }
    }

    /// Get a human-readable description of the event.
    pub fn description(&self) -> String {
        match self {
            TraceEvent::FunctionEntry {
                function_name, ..
            } => format!("Enter: {}", function_name),
            TraceEvent::FunctionExit { function_id, .. } => {
                format!("Exit: {}", function_id.short_id)
            }
            TraceEvent::StateChange {
                variable_name,
                new_value,
                ..
            } => format!("{} = {}", variable_name, new_value),
            TraceEvent::Branch { taken_branch, .. } => {
                format!("Branch: {}", taken_branch)
            }
            TraceEvent::Exception {
                exception_type, ..
            } => format!("Exception: {}", exception_type),
            TraceEvent::Log { message, .. } => format!("Log: {}", message),
            TraceEvent::Synchronization { action, .. } => format!("Sync: {}", action),
            TraceEvent::Custom { event_type, .. } => format!("Event: {}", event_type),
        }
    }
}

/// A complete execution trace session.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TraceSession {
    /// Session identifier
    pub id: String,
    /// Human-readable name
    pub name: String,
    /// Description of what was traced
    pub description: Option<String>,
    /// Start timestamp (Unix time in microseconds)
    pub start_time: u64,
    /// End timestamp (Unix time in microseconds), if session ended
    pub end_time: Option<u64>,
    /// All events in the session (in chronological order)
    pub events: Vec<TraceEvent>,
    /// Metadata (key-value pairs)
    pub metadata: HashMap<String, String>,
}

impl TraceSession {
    /// Create a new trace session.
    pub fn new(id: impl Into<String>, name: impl Into<String>) -> Self {
        let now = SystemTime::now()
            .duration_since(SystemTime::UNIX_EPOCH)
            .unwrap_or_default()
            .as_micros() as u64;

        Self {
            id: id.into(),
            name: name.into(),
            description: None,
            start_time: now,
            end_time: None,
            events: Vec::new(),
            metadata: HashMap::new(),
        }
    }

    /// Set the description.
    pub fn with_description(mut self, description: impl Into<String>) -> Self {
        self.description = Some(description.into());
        self
    }

    /// Add an event to the trace.
    pub fn add_event(&mut self, event: TraceEvent) {
        self.events.push(event);
    }

    /// Add metadata.
    pub fn add_metadata(&mut self, key: impl Into<String>, value: impl Into<String>) {
        self.metadata.insert(key.into(), value.into());
    }

    /// Mark the session as ended.
    pub fn end(&mut self) {
        let now = SystemTime::now()
            .duration_since(SystemTime::UNIX_EPOCH)
            .unwrap_or_default()
            .as_micros() as u64;
        self.end_time = Some(now);
    }

    /// Get the duration of this session (in microseconds).
    pub fn duration_us(&self) -> u64 {
        let end = self.end_time.unwrap_or_else(|| {
            SystemTime::now()
                .duration_since(SystemTime::UNIX_EPOCH)
                .unwrap_or_default()
                .as_micros() as u64
        });
        end.saturating_sub(self.start_time)
    }

    /// Get all function entry events.
    pub fn function_entries(&self) -> Vec<&TraceEvent> {
        self.events
            .iter()
            .filter(|e| matches!(e, TraceEvent::FunctionEntry { .. }))
            .collect()
    }

    /// Get all function exit events.
    pub fn function_exits(&self) -> Vec<&TraceEvent> {
        self.events
            .iter()
            .filter(|e| matches!(e, TraceEvent::FunctionExit { .. }))
            .collect()
    }

    /// Get all state change events.
    pub fn state_changes(&self) -> Vec<&TraceEvent> {
        self.events
            .iter()
            .filter(|e| matches!(e, TraceEvent::StateChange { .. }))
            .collect()
    }

    /// Get all exception events.
    pub fn exceptions(&self) -> Vec<&TraceEvent> {
        self.events
            .iter()
            .filter(|e| matches!(e, TraceEvent::Exception { .. }))
            .collect()
    }

    /// Filter events by type.
    pub fn filter_events<F>(&self, predicate: F) -> Vec<&TraceEvent>
    where
        F: Fn(&TraceEvent) -> bool,
    {
        self.events.iter().filter(|e| predicate(e)).collect()
    }

    /// Get call graph from trace (functions and their callers).
    pub fn call_graph(&self) -> HashMap<String, Vec<String>> {
        let mut graph: HashMap<String, Vec<String>> = HashMap::new();
        let mut call_stack: Vec<String> = Vec::new();

        for event in &self.events {
            match event {
                TraceEvent::FunctionEntry {
                    function_name, ..
                } => {
                    if !call_stack.is_empty() {
                        let caller = call_stack.last().unwrap().clone();
                        graph
                            .entry(caller)
                            .or_insert_with(Vec::new)
                            .push(function_name.clone());
                    }
                    call_stack.push(function_name.clone());
                }
                TraceEvent::FunctionExit { .. } => {
                    call_stack.pop();
                }
                _ => {}
            }
        }

        graph
    }

    /// Get the maximum call depth reached.
    pub fn max_call_depth(&self) -> u32 {
        let mut max_depth: u32 = 0;
        let mut current_depth: u32 = 0;

        for event in &self.events {
            match event {
                TraceEvent::FunctionEntry { .. } => {
                    current_depth += 1;
                    max_depth = max_depth.max(current_depth);
                }
                TraceEvent::FunctionExit { .. } => {
                    current_depth = current_depth.saturating_sub(1);
                }
                _ => {}
            }
        }

        max_depth
    }

    /// Get number of events of each type.
    pub fn event_counts(&self) -> HashMap<String, usize> {
        let mut counts = HashMap::new();
        for event in &self.events {
            let key = match event {
                TraceEvent::FunctionEntry { .. } => "FunctionEntry",
                TraceEvent::FunctionExit { .. } => "FunctionExit",
                TraceEvent::StateChange { .. } => "StateChange",
                TraceEvent::Branch { .. } => "Branch",
                TraceEvent::Exception { .. } => "Exception",
                TraceEvent::Log { .. } => "Log",
                TraceEvent::Synchronization { .. } => "Synchronization",
                TraceEvent::Custom { .. } => "Custom",
            };
            *counts.entry(key.to_string()).or_insert(0) += 1;
        }
        counts
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_trace_session_create() {
        let session = TraceSession::new("session1", "test_trace");
        assert_eq!(session.id, "session1");
        assert_eq!(session.name, "test_trace");
    }

    #[test]
    fn test_add_event() {
        let mut session = TraceSession::new("session1", "test_trace");
        let event = TraceEvent::FunctionEntry {
            function_id: StableId::new("fn_test"),
            function_name: "test_func".to_string(),
            timestamp: 1000,
            arguments: HashMap::new(),
            depth: 1,
        };
        session.add_event(event);
        assert_eq!(session.events.len(), 1);
    }

    #[test]
    fn test_duration() {
        let mut session = TraceSession::new("session1", "test_trace");
        session.end();
        assert!(session.duration_us() >= 0);
    }

    #[test]
    fn test_call_graph() {
        let mut session = TraceSession::new("session1", "test_trace");
        session.add_event(TraceEvent::FunctionEntry {
            function_id: StableId::new("fn_main"),
            function_name: "main".to_string(),
            timestamp: 1000,
            arguments: HashMap::new(),
            depth: 1,
        });
        session.add_event(TraceEvent::FunctionEntry {
            function_id: StableId::new("fn_test"),
            function_name: "test_func".to_string(),
            timestamp: 1100,
            arguments: HashMap::new(),
            depth: 2,
        });
        session.add_event(TraceEvent::FunctionExit {
            function_id: StableId::new("fn_test"),
            timestamp: 1200,
            return_value: None,
            elapsed_us: 100,
        });

        let graph = session.call_graph();
        assert!(graph.contains_key("main"));
    }
}
