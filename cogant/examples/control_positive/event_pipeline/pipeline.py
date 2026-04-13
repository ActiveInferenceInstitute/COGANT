"""
Pub/Sub event pipeline with retry logic and logging.

Exercises: event rules, retry/policy rules, observation channels.
"""

from typing import Callable, List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Event:
    """An event in the system."""
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class EventHandler:
    """Base handler for events."""

    def can_handle(self, event: Event) -> bool:
        """Check if this handler can process the event."""
        return True

    def handle(self, event: Event) -> bool:
        """Handle the event. Returns True if successful."""
        raise NotImplementedError


class LoggingEventHandler(EventHandler):
    """Logs all events (observation channel)."""

    def __init__(self):
        self.logs: List[Dict[str, Any]] = []

    def handle(self, event: Event) -> bool:
        self.logs.append({
            "event_type": event.event_type,
            "timestamp": str(event.timestamp),
            "payload": event.payload,
        })
        return True

    def get_logs(self) -> List[Dict[str, Any]]:
        """Observation: access logs."""
        return self.logs.copy()


class RetryableEventHandler(EventHandler):
    """Handler with retry logic (policy/state)."""

    def __init__(self, handler: EventHandler, max_retries: int = 3):
        self.handler = handler
        self.max_retries = max_retries
        self.retry_count = 0
        self.failed_events: List[Event] = []

    def handle(self, event: Event) -> bool:
        """Handle with retries."""
        for attempt in range(self.max_retries):
            try:
                if self.handler.handle(event):
                    self.retry_count = 0
                    return True
            except Exception:
                self.retry_count = attempt + 1
                continue

        # Failed after retries
        self.failed_events.append(event)
        return False

    def get_failed_events(self) -> List[Event]:
        """Observation: failed events."""
        return self.failed_events.copy()


class FilteringEventHandler(EventHandler):
    """Filters events by type."""

    def __init__(self, event_type: str, handler: EventHandler):
        self.event_type = event_type
        self.handler = handler

    def can_handle(self, event: Event) -> bool:
        return event.event_type == self.event_type

    def handle(self, event: Event) -> bool:
        if self.can_handle(event):
            return self.handler.handle(event)
        return False


class EventBus:
    """Central event bus with multiple handlers."""

    def __init__(self):
        self.handlers: List[EventHandler] = []
        self.event_history: List[Event] = []

    def subscribe(self, handler: EventHandler) -> None:
        """Register a handler."""
        self.handlers.append(handler)

    def publish(self, event: Event) -> bool:
        """Publish an event to all handlers."""
        self.event_history.append(event)

        for handler in self.handlers:
            if handler.can_handle(event):
                if not handler.handle(event):
                    return False

        return True

    def get_event_history(self) -> List[Event]:
        """Observation: event history."""
        return self.event_history.copy()


# Example usage
if __name__ == "__main__":
    bus = EventBus()

    # Subscribe handlers
    logger = LoggingEventHandler()
    bus.subscribe(logger)

    retryable_handler = RetryableEventHandler(LoggingEventHandler(), max_retries=3)
    bus.subscribe(FilteringEventHandler("user_login", retryable_handler))

    # Publish events
    login_event = Event("user_login", {"user_id": "123", "ip": "192.168.1.1"})
    data_event = Event("data_processed", {"count": 42})

    bus.publish(login_event)
    bus.publish(data_event)

    # Observations
    print(f"Logged events: {len(logger.get_logs())}")
    print(f"Event history: {len(bus.get_event_history())}")
