"""State machine implementation for workflow engine."""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, TypeVar, Generic

T = TypeVar("T")


class WorkflowState(str, Enum):
    """Possible workflow states."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Transition:
    """State transition definition."""

    from_state: WorkflowState
    to_state: WorkflowState
    condition: Optional[Callable] = None
    on_transition: Optional[Callable] = None


class StateMachine(Generic[T]):
    """Generic state machine for workflow management."""

    def __init__(self, initial_state: WorkflowState):
        self.current_state = initial_state
        self.transitions: dict[tuple[WorkflowState, WorkflowState], Transition] = {}
        self.state_handlers: dict[WorkflowState, Callable] = {}
        self.history: list[tuple[WorkflowState, WorkflowState]] = []

    def add_transition(
        self,
        from_state: WorkflowState,
        to_state: WorkflowState,
        condition: Optional[Callable] = None,
        on_transition: Optional[Callable] = None,
    ) -> None:
        """Register a state transition."""
        key = (from_state, to_state)
        self.transitions[key] = Transition(
            from_state=from_state,
            to_state=to_state,
            condition=condition,
            on_transition=on_transition,
        )

    def add_state_handler(self, state: WorkflowState, handler: Callable) -> None:
        """Register a handler for a state."""
        self.state_handlers[state] = handler

    def can_transition(
        self, from_state: WorkflowState, to_state: WorkflowState, context: Optional[T] = None
    ) -> bool:
        """Check if a transition is allowed."""
        key = (from_state, to_state)
        if key not in self.transitions:
            return False

        transition = self.transitions[key]
        if transition.condition is None:
            return True

        return transition.condition(context)

    def transition(
        self, to_state: WorkflowState, context: Optional[T] = None
    ) -> bool:
        """Perform a state transition."""
        if not self.can_transition(self.current_state, to_state, context):
            return False

        old_state = self.current_state
        self.current_state = to_state
        self.history.append((old_state, to_state))

        # Call transition handler if defined
        key = (old_state, to_state)
        if key in self.transitions:
            transition = self.transitions[key]
            if transition.on_transition:
                transition.on_transition(context)

        return True

    def handle_state(self, context: Optional[T] = None) -> None:
        """Execute the handler for the current state."""
        if self.current_state in self.state_handlers:
            handler = self.state_handlers[self.current_state]
            handler(context)

    def get_history(self) -> list[tuple[WorkflowState, WorkflowState]]:
        """Get transition history."""
        return self.history.copy()

    def reset(self, initial_state: Optional[WorkflowState] = None) -> None:
        """Reset state machine."""
        if initial_state:
            self.current_state = initial_state
        else:
            # Could store initial state in constructor
            self.current_state = WorkflowState.PENDING
        self.history.clear()
