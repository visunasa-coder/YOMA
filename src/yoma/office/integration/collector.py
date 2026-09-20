from __future__ import annotations

from typing import Any

from yoma.office.adapters.base import YomaAdapter
from yoma.office.integration.bridge import IntegrationEventBridge
from yoma.office.operations import OperationalEvent


class AdapterEventCollector:
    """
    Collects events from registered YOMA adapters and sends them
    through the universal operational event bridge.

    Adapters remain responsible for communicating with their
    external systems. This layer only normalizes and publishes
    what they actually return.
    """

    def __init__(self, bridge: IntegrationEventBridge) -> None:
        self.bridge = bridge

    def collect(
        self,
        adapter: YomaAdapter,
        *,
        event_type: str,
        records: list[dict[str, Any]],
        user_id_field: str | None = None,
        system_id_field: str | None = None,
    ) -> list[OperationalEvent]:
        normalized: list[OperationalEvent] = []

        for record in records:
            user_id = None
            system_id = None

            if user_id_field:
                value = record.get(user_id_field)
                if value is not None:
                    user_id = str(value)

            if system_id_field:
                value = record.get(system_id_field)
                if value is not None:
                    system_id = str(value)

            normalized.append(
                self.bridge.normalize(
                    source=adapter.name,
                    event_type=event_type,
                    record=record,
                    user_id=user_id,
                    system_id=system_id,
                )
            )

        self.bridge.bus.publish_many(normalized)

        return normalized

    def collect_adapter_events(
        self,
        adapter: YomaAdapter,
    ) -> list[OperationalEvent]:
        """
        Collect events from an adapter implementing the universal
        collect_events() contract.
        """
        events = list(adapter.collect_events())

        self.bridge.bus.publish_many(events)

        return events
