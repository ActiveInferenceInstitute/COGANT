"""Event system for the example service."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional


@dataclass
class Event:
    """Base event class."""

    event_type: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None


@dataclass
class UserCreatedEvent(Event):
    """Event triggered when a user is created."""

    event_type: str = "user_created"


@dataclass
class UserUpdatedEvent(Event):
    """Event triggered when a user is updated."""

    event_type: str = "user_updated"


@dataclass
class ItemCreatedEvent(Event):
    """Event triggered when an item is created."""

    event_type: str = "item_created"


class EventListener(ABC):
    """Abstract base class for event listeners."""

    @abstractmethod
    async def handle(self, event: Event) -> None:
        """Handle an event."""
        pass


class EventEmitter:
    """Simple event emitter for pub/sub pattern."""

    def __init__(self):
        self._listeners: dict[str, list[Callable]] = {}

    def subscribe(self, event_type: str, listener: Callable) -> None:
        """Subscribe to an event type."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(listener)

    def unsubscribe(self, event_type: str, listener: Callable) -> None:
        """Unsubscribe from an event type."""
        if event_type in self._listeners:
            self._listeners[event_type].remove(listener)

    async def emit(self, event: Event) -> None:
        """Emit an event to all listeners."""
        if event.event_type in self._listeners:
            for listener in self._listeners[event.event_type]:
                await listener(event)

    def get_listeners(self, event_type: str) -> list[Callable]:
        """Get all listeners for an event type."""
        return self._listeners.get(event_type, [])


# Global event emitter instance
event_emitter = EventEmitter()
