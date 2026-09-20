from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any


@dataclass(frozen=True)
class DataAccessAuditEvent:
    actor: str
    operation: str
    resource: str
    classification: str
    decision: str
    purpose: str
    timestamp: str
    previous_hash: str
    event_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "actor": self.actor,
            "operation": self.operation,
            "resource": self.resource,
            "classification": self.classification,
            "decision": self.decision,
            "purpose": self.purpose,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "event_hash": self.event_hash,
        }


class DataAccessAuditChain:
    def __init__(self) -> None:
        self._events: list[DataAccessAuditEvent] = []

    @property
    def events(self) -> tuple[DataAccessAuditEvent, ...]:
        return tuple(self._events)

    def append(
        self,
        *,
        actor: str,
        operation: str,
        resource: str,
        classification: str,
        decision: str,
        purpose: str,
    ) -> DataAccessAuditEvent:
        previous = self._events[-1].event_hash if self._events else "GENESIS"
        timestamp = datetime.now(timezone.utc).isoformat()

        payload = {
            "actor": actor,
            "operation": operation,
            "resource": resource,
            "classification": classification,
            "decision": decision,
            "purpose": purpose,
            "timestamp": timestamp,
            "previous_hash": previous,
        }

        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()

        event = DataAccessAuditEvent(
            **payload,
            event_hash=digest,
        )

        self._events.append(event)
        return event

    def verify(self) -> bool:
        previous = "GENESIS"

        for event in self._events:
            payload = {
                "actor": event.actor,
                "operation": event.operation,
                "resource": event.resource,
                "classification": event.classification,
                "decision": event.decision,
                "purpose": event.purpose,
                "timestamp": event.timestamp,
                "previous_hash": previous,
            }

            expected = hashlib.sha256(
                json.dumps(payload, sort_keys=True).encode("utf-8")
            ).hexdigest()

            if event.previous_hash != previous or event.event_hash != expected:
                return False

            previous = event.event_hash

        return True
