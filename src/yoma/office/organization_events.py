from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class OrganizationChangeEvent:
    """Structured event describing a change in organization state."""

    event_type: str
    entity_type: str
    entity_id: str
    previous_state: dict[str, Any] | None = None
    current_state: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self) -> None:
        if not str(self.event_type).strip():
            raise ValueError("event_type is required")

        if not str(self.entity_type).strip():
            raise ValueError("entity_type is required")

        if not str(self.entity_id).strip():
            raise ValueError("entity_id is required")

        if self.previous_state is not None:
            if not isinstance(self.previous_state, dict):
                raise TypeError("previous_state must be a dictionary")

        if self.current_state is not None:
            if not isinstance(self.current_state, dict):
                raise TypeError("current_state must be a dictionary")

        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary")

        if not str(self.timestamp).strip():
            raise ValueError("timestamp is required")


class OrganizationChangeEventStore:
    """In-memory ordered store for organization change events."""

    def __init__(self) -> None:
        self._events: list[OrganizationChangeEvent] = []

    def add(self, event: OrganizationChangeEvent) -> None:
        if not isinstance(event, OrganizationChangeEvent):
            raise TypeError("event must be an OrganizationChangeEvent")

        self._events.append(event)

    def events(self) -> list[OrganizationChangeEvent]:
        return list(self._events)

    def count(self) -> int:
        return len(self._events)

    def by_type(
        self,
        event_type: str,
    ) -> list[OrganizationChangeEvent]:
        event_type = str(event_type).strip()

        if not event_type:
            raise ValueError("event_type is required")

        return [
            event
            for event in self._events
            if event.event_type == event_type
        ]

    def by_entity(
        self,
        entity_type: str,
        entity_id: str,
    ) -> list[OrganizationChangeEvent]:
        entity_type = str(entity_type).strip()
        entity_id = str(entity_id).strip()

        if not entity_type:
            raise ValueError("entity_type is required")

        if not entity_id:
            raise ValueError("entity_id is required")

        return [
            event
            for event in self._events
            if (
                event.entity_type == entity_type
                and event.entity_id == entity_id
            )
        ]