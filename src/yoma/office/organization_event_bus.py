from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from yoma.office.organization_events import OrganizationChangeEvent


EventHandler = Callable[[OrganizationChangeEvent], None]


@dataclass(frozen=True)
class EventSubscription:
    """Subscription definition for an organization event handler."""

    handler: EventHandler
    event_types: frozenset[str] | None = None
    entity_types: frozenset[str] | None = None

    def matches(
        self,
        event: OrganizationChangeEvent,
    ) -> bool:
        if (
            self.event_types is not None
            and event.event_type not in self.event_types
        ):
            return False

        if (
            self.entity_types is not None
            and event.entity_type not in self.entity_types
        ):
            return False

        return True


class OrganizationEventBus:
    """In-process event bus for YOMA organization change events."""

    def __init__(self) -> None:
        self._subscriptions: list[EventSubscription] = []

    def _normalize_filter(
        self,
        values: Iterable[str] | None,
        *,
        name: str,
    ) -> frozenset[str] | None:
        if values is None:
            return None

        if isinstance(values, (str, bytes)):
            raise TypeError(
                f"{name} must be an iterable of strings"
            )

        try:
            normalized = frozenset(
                str(value).strip()
                for value in values
            )
        except TypeError as exc:
            raise TypeError(
                f"{name} must be an iterable of strings"
            ) from exc

        if not normalized or any(
            not value
            for value in normalized
        ):
            raise ValueError(
                f"{name} cannot be empty"
            )

        return normalized

    def subscribe(
        self,
        handler: EventHandler,
        *,
        event_types: Iterable[str] | None = None,
        entity_types: Iterable[str] | None = None,
    ) -> None:
        if not callable(handler):
            raise TypeError("handler must be callable")

        normalized_event_types = self._normalize_filter(
            event_types,
            name="event_types",
        )

        normalized_entity_types = self._normalize_filter(
            entity_types,
            name="entity_types",
        )

        # A handler is uniquely identified by the callable itself.
        # Re-subscribing it with different filters does not create
        # a second subscription.
        for subscription in self._subscriptions:
            if subscription.handler == handler:
                return

        self._subscriptions.append(
            EventSubscription(
                handler=handler,
                event_types=normalized_event_types,
                entity_types=normalized_entity_types,
            )
        )

    def unsubscribe(
        self,
        handler: EventHandler,
    ) -> bool:
        for index, subscription in enumerate(
            self._subscriptions
        ):
            if subscription.handler == handler:
                del self._subscriptions[index]
                return True

        return False

    def subscriber_count(self) -> int:
        return len(self._subscriptions)

    def publish(
        self,
        event: OrganizationChangeEvent,
    ) -> int:
        if not isinstance(
            event,
            OrganizationChangeEvent,
        ):
            raise TypeError(
                "event must be an OrganizationChangeEvent"
            )

        deliveries = 0
        first_error: Exception | None = None

        for subscription in list(self._subscriptions):
            if not subscription.matches(event):
                continue

            try:
                subscription.handler(event)
                deliveries += 1
            except Exception as exc:
                if first_error is None:
                    first_error = exc

        if first_error is not None:
            raise first_error

        return deliveries

    def publish_many(
        self,
        events: Iterable[OrganizationChangeEvent],
    ) -> int:
        if isinstance(events, (str, bytes)):
            raise TypeError(
                "events must contain OrganizationChangeEvent objects"
            )

        try:
            event_list = list(events)
        except TypeError as exc:
            raise TypeError(
                "events must be iterable"
            ) from exc

        for event in event_list:
            if not isinstance(
                event,
                OrganizationChangeEvent,
            ):
                raise TypeError(
                    "events must contain only "
                    "OrganizationChangeEvent objects"
                )

        deliveries = 0

        for event in event_list:
            deliveries += self.publish(event)

        return deliveries