from __future__ import annotations

from collections.abc import Callable, Iterable

from .model import OperationalEvent


EventHandler = Callable[[OperationalEvent], None]


class OperationalEventBus:
    """
    Lightweight in-process event bus.

    External systems must be normalized by adapters before events
    enter the bus.
    """

    def __init__(self) -> None:
        self._handlers: list[EventHandler] = []

    def subscribe(self, handler: EventHandler) -> None:
        if handler not in self._handlers:
            self._handlers.append(handler)

    def unsubscribe(self, handler: EventHandler) -> None:
        if handler in self._handlers:
            self._handlers.remove(handler)

    def publish(self, event: OperationalEvent) -> None:
        for handler in tuple(self._handlers):
            handler(event)

    def publish_many(self, events: Iterable[OperationalEvent]) -> None:
        for event in events:
            self.publish(event)

    @property
    def subscriber_count(self) -> int:
        return len(self._handlers)
