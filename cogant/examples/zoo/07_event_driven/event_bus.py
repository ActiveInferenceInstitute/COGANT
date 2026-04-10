"""Event bus with handler registration and dispatch.

Triggers:
    - PolicyRule: `EventDispatcher` class (keyword "dispatcher")
    - PolicyRule: `dispatch()` method (keyword "dispatch")
    - ActionRule: `handle_temperature()` and `handle_pressure()` (keyword "handle")
    - ObservationRule: `get_history()` (keyword "get", read-only)
"""

from __future__ import annotations

from typing import Callable


class EventDispatcher:
    """Central event bus: routes events to registered handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[dict], None]]] = {}
        self._history: list[dict] = []

    def subscribe(self, event_type: str, handler: Callable[[dict], None]) -> None:
        """Register a handler for a given event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def dispatch(self, event_type: str, payload: dict) -> None:
        """Route an event to all registered handlers."""
        record = {"type": event_type, "payload": payload}
        self._history.append(record)
        for handler in self._handlers.get(event_type, []):
            handler(payload)

    def get_history(self) -> list[dict]:
        """Read-only access to dispatched event history."""
        return list(self._history)


class SensorHandler:
    """Handles incoming sensor events by updating internal accumulators."""

    def __init__(self) -> None:
        self.temperature_readings: list[float] = []
        self.pressure_readings: list[float] = []

    def handle_temperature(self, payload: dict) -> None:
        """Process a temperature event."""
        value = payload.get("value", 0.0)
        self.temperature_readings.append(value)

    def handle_pressure(self, payload: dict) -> None:
        """Process a pressure event."""
        value = payload.get("value", 0.0)
        self.pressure_readings.append(value)


if __name__ == "__main__":
    bus = EventDispatcher()
    handler = SensorHandler()
    bus.subscribe("temperature", handler.handle_temperature)
    bus.subscribe("pressure", handler.handle_pressure)
    bus.dispatch("temperature", {"value": 22.5})
    bus.dispatch("pressure", {"value": 101.3})
    bus.dispatch("temperature", {"value": 23.1})
    print("history:", bus.get_history())
    print("temps:", handler.temperature_readings)
